"""Real Mininet + Open vSwitch tests (skipped unless SDN_REAL_BENCH=1).

They drive the live bench started by docker/run_bench.sh: OVS switches in Mininet
connected to a primary and a standby controller, the network agent, and the
backend API. Nothing here is mocked: pings are real packets through OVS, roles are
read from OVS's own Controller table, and flows come from `ovs-ofctl dump-flows`.

Order matters (module state: the topology evolves, the primary is killed/restored).
"""
import os
import subprocess
import time

import httpx
import pytest

pytestmark = pytest.mark.skipif(os.environ.get("SDN_REAL_BENCH") != "1",
                                reason="needs the Mininet/OVS bench (docker/run_real_tests.sh)")
TOKEN = os.environ.get("CONTROLLER_API_TOKEN", "bench-token")
H = {"Authorization": f"Bearer {TOKEN}"}
BACKEND, AGENT = "http://127.0.0.1:8000", "http://127.0.0.1:9100"
SWITCHES = [f"s{i}" for i in range(1, 8)]


def backend(method, path, **kw):
    return httpx.request(method, BACKEND + path, timeout=60, **kw)


def agent(method, path, body=None):
    r = httpx.request(method, AGENT + path, json=body, headers=H, timeout=60)
    r.raise_for_status()
    return r.json()


def ping(src, dst_ip, count=3):
    return agent("POST", "/ping", {"src": src, "dst_ip": dst_ip, "count": count})


def wait_until(fn, timeout=30, interval=0.5, what="condition"):
    deadline, last = time.time() + timeout, None
    while time.time() < deadline:
        try:
            last = fn()
            if last:
                return last
        except Exception as exc:       # transient while things converge
            last = exc
        time.sleep(interval)
    pytest.fail(f"timed out waiting for {what}; last={last!r}")


def roles():
    """{switch: {controller port: OVS role}} straight from OVS."""
    return {sw: {c["target"].rsplit(":", 1)[1]: c["role"] for c in cs if c["connected"]}
            for sw, cs in agent("GET", "/switch-roles").items()}


def master_port(sw_roles):
    return {sw: next((p for p, r in rs.items() if r == "master"), None) for sw, rs in sw_roles.items()}


def controller_ctl(who, action):
    subprocess.run(["/work/docker/controller_ctl.sh", who, action], check=True)


def all_pings_ok():
    pairs = [("h1", "10.0.0.7"), ("h2", "10.0.0.8"), ("h7", "10.0.0.1"), ("h8", "10.0.0.2")]
    return all(ping(s, d)["ok"] for s, d in pairs)


def wait_installed(src_ip, dst_ip, path=None, timeout=40):
    """Wait until OVS flows for src->dst are VERIFIED (and equal ``path`` if given);
    on timeout fail with the verifier's own discrepancy report."""
    box = {}

    def check():
        box["v"] = backend("GET", "/api/routing/verify", params={"source_ip": src_ip, "dest_ip": dst_ip}).json()
        return box["v"]["status"] == "VERIFIED" and (path is None or box["v"]["installed_path"] == path)

    deadline = time.time() + timeout
    while time.time() < deadline:
        if check():
            return box["v"]
        time.sleep(0.5)
    pytest.fail(f"OVS flows {src_ip}->{dst_ip} did not reach {path}: {box.get('v')}")


def verify_all():
    return backend("GET", "/api/routing/verify/all").json()


# --------------------------------------------------------------- baseline
def test_01_all_switches_connected_with_one_master_each():
    state = wait_until(lambda: (lambda r: r if len(r) == 7 and all(len(v) == 2 for v in r.values()) else None)(roles()),
                       what="7 switches connected to both controllers")
    assert set(state) == set(SWITCHES)
    for sw, by_port in state.items():
        assert sorted(by_port.values()) == ["master", "slave"], f"{sw}: {by_port}"
    assert set(master_port(state).values()) == {"6653"}            # primary leads every switch


def test_02_real_connectivity_and_flows_match_calculated_routes():
    wait_until(all_pings_ok, timeout=60, what="host connectivity through OVS")
    result = wait_until(lambda: (lambda v: v if v["all_verified"] else None)(verify_all()), timeout=40,
                        what="every calculated route verified against OVS dumps")
    assert result["counts"] == {"VERIFIED": 8}
    one = next(r for r in result["results"] if r["source_ip"] == "10.0.0.1" and r["dest_ip"] == "10.0.0.8")
    assert one["expected_path"] == one["installed_path"] and one["delivered"]
    assert all(h["packets"] is not None for h in one["hops"])      # counters come from OVS


def test_03_backend_sees_real_topology_and_both_controllers():
    status = backend("GET", "/api/network/status").json()
    assert status["agent_enabled"] and status["reachable"] and status["in_sync"], status["drift"]
    ctl = backend("GET", "/api/controller/status").json()
    assert ctl["status"] == "UP" and ctl["active_role"] == "primary"
    topo = backend("GET", "/api/topology").json()
    assert len(topo["links"]) == 18 and all(l["data_plane_confirmed"] for l in topo["links"])


def test_04_verification_detects_tampering_in_ovs():
    """Delete a rule behind the controller's back. The verifier must report it; the
    controller's periodic ADD-based reinstall then heals it without any resync.
    The healing window is a few seconds, so retry the delete-then-verify pair."""
    pair = {"source_ip": "10.0.0.1", "dest_ip": "10.0.0.8"}
    detected = None
    for _ in range(6):
        v = backend("GET", "/api/routing/verify", params=pair).json()
        victim = v["installed_path"][1]
        subprocess.run(["ovs-ofctl", "-O", "OpenFlow13", "del-flows", victim, "ip,nw_dst=10.0.0.8"], check=True)
        broken = backend("GET", "/api/routing/verify", params=pair).json()
        if broken["status"] == "MISSING_RULES":
            detected = (victim, broken)
            break
        wait_installed("10.0.0.1", "10.0.0.8")       # healed before we looked; try again
    assert detected, "verifier never observed the deleted rule"
    victim, broken = detected
    assert any(victim in d for d in broken["discrepancies"])
    wait_installed("10.0.0.1", "10.0.0.8", timeout=40)   # self-healed by the controller


# -------------------------------------------------- real link failure
def test_05_link_failure_is_real_and_traffic_reroutes():
    before = backend("POST", "/api/routing/recalculate",
                     json={"source_ip": "10.0.0.1", "dest_ip": "10.0.0.8"}).json()["selected_path"]
    a, b = before[0], before[1]
    pid = agent("POST", "/ping-start", {"src": "h1", "dst_ip": "10.0.0.8", "interval": 0.2})["id"]
    time.sleep(1)
    r = backend("POST", "/api/network/failure/simulate", json={"src_switch": a, "dst_switch": b, "action": "DOWN"})
    assert r.status_code == 200 and r.json()["sync_status"] == "SYNCED"
    link = next(l for l in agent("GET", "/topology")["links"] if {l["src"], l["dst"]} == {a, b})
    assert link["up"] is False                                      # the interface really is down
    after = wait_until(lambda: (lambda p: p if p and (a, b) not in zip(p, p[1:]) else None)(
        backend("POST", "/api/routing/recalculate", json={"source_ip": "10.0.0.1", "dest_ip": "10.0.0.8"}).json()["selected_path"]),
        what="route avoiding failed link")
    wait_installed("10.0.0.1", "10.0.0.8", after)
    time.sleep(2)
    stats = agent("POST", "/ping-stop", {"id": pid})
    assert stats["received"] > 0 and stats["max_consecutive_gap"] <= 15, stats
    backend("POST", "/api/network/failure/simulate", json={"src_switch": a, "dst_switch": b, "action": "UP"})
    wait_until(lambda: (lambda l: l["up"])(next(l for l in agent("GET", "/topology")["links"] if {l["src"], l["dst"]} == {a, b})))
    wait_until(all_pings_ok, timeout=40, what="connectivity after link restore")


# ------------------------------------- dynamic edits while traffic runs
def test_06_add_switch_and_links_while_traffic_is_running():
    pid = agent("POST", "/ping-start", {"src": "h1", "dst_ip": "10.0.0.8", "interval": 0.2})["id"]
    time.sleep(1)
    assert backend("POST", "/api/switches", json={"name": "s8"}).status_code == 201
    assert backend("POST", "/api/links", json={"src": "s1", "dst": "s8", "latency_ms": 0.5, "capacity_mbps": 100}).status_code == 201
    r = backend("POST", "/api/links", json={"src": "s8", "dst": "s7", "latency_ms": 0.5, "capacity_mbps": 100})
    assert r.status_code == 201 and r.json()["sync_status"] == "SYNCED"
    real = agent("GET", "/topology")
    assert "s8" in {s["name"] for s in real["switches"]}                # exists in Mininet
    assert {"s1", "s8"} in [{l["src"], l["dst"]} for l in real["links"]]
    assert backend("GET", "/api/network/status").json()["in_sync"] is True
    selected = backend("POST", "/api/routing/recalculate", json={"source_ip": "10.0.0.1", "dest_ip": "10.0.0.8"}).json()
    assert selected["selected_path"] == ["s1", "s8", "s7"]
    wait_until(lambda: (lambda v: v["status"] == "VERIFIED" and v["installed_path"] == ["s1", "s8", "s7"])(
        backend("GET", "/api/routing/verify", params={"source_ip": "10.0.0.1", "dest_ip": "10.0.0.8"}).json()),
        timeout=40, what="OVS carries traffic over the new links")
    time.sleep(2)
    stats = agent("POST", "/ping-stop", {"id": pid})
    assert stats["received"] > 0 and stats["max_consecutive_gap"] <= 15, stats
    assert ping("h1", "10.0.0.8", 3)["ok"]


def test_07_remove_link_on_active_route_while_traffic_is_running():
    pid = agent("POST", "/ping-start", {"src": "h1", "dst_ip": "10.0.0.8", "interval": 0.2})["id"]
    time.sleep(1)
    r = backend("DELETE", "/api/links/s1/s8")
    assert r.status_code == 200
    assert {"s1", "s8"} not in [{l["src"], l["dst"]} for l in agent("GET", "/topology")["links"]]
    path = wait_until(lambda: (lambda p: p if p and "s8" not in p else None)(
        backend("POST", "/api/routing/recalculate", json={"source_ip": "10.0.0.1", "dest_ip": "10.0.0.8"}).json()["selected_path"]),
        what="route without s8")
    wait_until(lambda: backend("GET", "/api/routing/verify", params={"source_ip": "10.0.0.1", "dest_ip": "10.0.0.8"}).json()["installed_path"] == path,
               timeout=40, what="flows follow the surviving route")
    time.sleep(2)
    stats = agent("POST", "/ping-stop", {"id": pid})
    assert stats["received"] > 0, stats
    assert all_pings_ok()


def test_08_host_add_and_remove_on_the_running_network():
    r = backend("POST", "/api/hosts", json={"name": "h9", "ip": "10.0.0.9", "connected_switch": "s4"})
    assert r.status_code == 201, r.text
    wait_until(lambda: ping("h9", "10.0.0.1", 3)["ok"], timeout=40, what="new host reaches h1 through OVS")
    assert ping("h1", "10.0.0.9", 3)["ok"]
    assert backend("DELETE", "/api/hosts/h9").status_code == 200
    assert "h9" not in {h["name"] for h in agent("GET", "/topology")["hosts"]}


def test_09_failed_network_operation_leaves_model_and_network_unchanged():
    before = backend("GET", "/api/topology").json()
    r = backend("POST", "/api/switches", json={"name": "this-name-is-too-long-for-linux"})
    assert r.status_code in (409, 422, 502), r.text
    after = backend("GET", "/api/topology").json()
    assert [s["dpid"] for s in after["switches"]] == [s["dpid"] for s in before["switches"]]
    assert backend("GET", "/api/network/status").json()["in_sync"] is True
    dup = backend("POST", "/api/links", json={"src": "s1", "dst": "s2"})
    assert dup.status_code == 409


# ------------------------------------------- switch-level controller failover
def test_10_primary_controller_failure_fails_over_at_the_switches():
    wait_until(lambda: set(master_port(roles()).values()) == {"6653"}, what="primary master everywhere")
    pid = agent("POST", "/ping-start", {"src": "h2", "dst_ip": "10.0.0.7", "interval": 0.2})["id"]
    controller_ctl("primary", "stop")                              # kill -9 the primary controller
    wait_until(lambda: set(master_port(roles()).values()) == {"6654"}, timeout=30,
               what="standby promoted to MASTER on every switch (as seen by OVS)")
    ctl = wait_until(lambda: (lambda c: c if c["active_role"] == "standby-1" and c["status"] == "UP" else None)(
        backend("GET", "/api/controller/status").json()), timeout=30, what="backend failed over")
    assert ctl["failover_count"] >= 1
    assert "CONTROLLER_DOWN" in [e["type"] for e in ctl["history"]]
    # Forwarding continued and the NEW master can still program the network:
    assert ping("h2", "10.0.0.7")["ok"]
    r = backend("POST", "/api/links", json={"src": "s2", "dst": "s6", "latency_ms": 0.5})
    assert r.status_code == 201 and r.json()["sync_status"] == "SYNCED"
    wait_until(lambda: verify_all()["all_verified"], timeout=40, what="standby programmed consistent flows")
    backend("DELETE", "/api/links/s2/s6")
    stats = agent("POST", "/ping-stop", {"id": pid})
    assert stats["received"] > 0 and stats["max_consecutive_gap"] <= 20, stats


def test_11_slave_controller_never_programs_while_another_is_master():
    # Primary is down; standby is the only master. Confirm via OVS that no switch has two masters.
    for sw, by_port in roles().items():
        assert list(by_port.values()).count("master") <= 1, (sw, by_port)


def test_12_primary_recovery_fails_back_with_current_state():
    # An edit made while the primary was down must be present after it returns.
    assert backend("PATCH", "/api/links/s3/s4", json={"latency_ms": 33}).status_code == 200
    controller_ctl("primary", "start")
    wait_until(lambda: set(master_port(roles()).values()) == {"6653"}, timeout=60,
               what="primary re-elected MASTER on every switch")
    ctl = wait_until(lambda: (lambda c: c if c["active_role"] == "primary" and c["status"] == "UP" else None)(
        backend("GET", "/api/controller/status").json()), timeout=40, what="backend failed back")
    types = [e["type"] for e in ctl["history"]]
    assert "CONTROLLER_FAILOVER" in types and "CONTROLLER_FAILBACK" in types
    for sw_roles in roles().values():
        assert sorted(sw_roles.values()) == ["master", "slave"]
    state = httpx.get("http://127.0.0.1:8080/state", headers=H, timeout=10).json()
    link = next(l for l in state["links"] if l["link_id"] == "s3-s4")
    assert link["latency_ms"] == 33                                # stale primary was resynced
    wait_until(all_pings_ok, timeout=60, what="connectivity after failback")
    wait_until(lambda: verify_all()["all_verified"], timeout=60, what="flows verified after failback")


def test_13_repeated_primary_failures():
    for cycle in range(2):
        controller_ctl("primary", "stop")
        wait_until(lambda: set(master_port(roles()).values()) == {"6654"}, timeout=30, what=f"failover #{cycle + 1}")
        assert ping("h1", "10.0.0.7")["ok"]
        controller_ctl("primary", "start")
        wait_until(lambda: set(master_port(roles()).values()) == {"6653"}, timeout=60, what=f"failback #{cycle + 1}")
        wait_until(all_pings_ok, timeout=60, what="connectivity")
    ctl = backend("GET", "/api/controller/status").json()
    assert ctl["outage_count"] >= 3 and ctl["failover_count"] >= 3


# ------------------------------------ QA additions: traffic, counters, tc
def test_14_real_traffic_shows_up_in_ovs_flow_counters():
    before = {(f["dpid"], f["priority"]): f["packet_count"] for f in backend("GET", "/api/flows").json()
              if f["match"].get("ipv4_dst") == "10.0.0.8"}
    r = backend("POST", "/api/network/traffic/start",
                json={"src_host": "h1", "dst_host": "h8", "rate_mbps": 5, "duration_sec": 4, "protocol": "UDP"})
    assert r.status_code == 200, r.text
    time.sleep(6)
    flows = backend("GET", "/api/flows").json()
    assert flows and all(f["source"] == "ovs" for f in flows)
    grew = [f for f in flows if f["match"].get("ipv4_dst") == "10.0.0.8"
            and f["packet_count"] > before.get((f["dpid"], f["priority"]), 0)]
    assert len(grew) >= 3, "iperf traffic must increment counters on every switch of the path"
    assert backend("POST", "/api/network/traffic/stop").status_code == 200


def test_15_link_property_changes_are_applied_to_the_real_link():
    assert backend("PATCH", "/api/links/s3/s4", json={"latency_ms": 33}).status_code == 200
    link = next(l for l in agent("GET", "/topology")["links"] if {l["src"], l["dst"]} == {"s3", "s4"})
    assert "33" in str(link["delay"])                                # reflected, not the stale 6ms
    tc = subprocess.run(["tc", "qdisc", "show", "dev", "s3-eth2"], capture_output=True, text=True).stdout
    assert "delay 33ms" in tc or "delay 33.0ms" in tc, tc
    assert backend("GET", "/api/network/status").json()["in_sync"] is True
