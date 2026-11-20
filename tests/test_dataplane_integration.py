"""Switch-level HA, live-network edits, route verification and capacity-aware cost.

These tests run without Mininet (fakes at the OpenFlow/HTTP boundary). The real
Mininet/OVS equivalents live in tests/real/ and run via docker/run_real_tests.sh.
"""
import asyncio
import struct

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.route_verifier import verify_route
from backend.services.runtime import orchestrator, routing_service
from backend.services.topology_service import topology_service as topo
from controller.app import SDNTrafficEngineApp
from controller.config.settings import settings as controller_settings
from controller.ha import HAManager
from controller.openflow.protocol import (
    OFPCR_ROLE_MASTER, OFPCR_ROLE_SLAVE, OFPT_FLOW_MOD, OFPT_ROLE_REQUEST, OFPT_ROLE_REPLY,
    build_role_request, parse_header, parse_role_reply, OFP_VERSION, build_flow_mod,
)
from controller.openflow.switch_manager import Datapath
from controller.routing.cost_function import CostCalculator
from controller.routing.dijkstra import DijkstraRouter
from controller.topology.graph import NetworkGraph
from tests.test_controller_sync import MockDatapath

client = TestClient(app)


# ------------------------------------------------------------------ protocol
def test_role_request_wire_format_and_reply_parse():
    msg = build_role_request(OFPCR_ROLE_MASTER, 0x1122334455667788, xid=9)
    hdr = parse_header(msg[:8])
    assert (hdr.msg_type, hdr.length, hdr.xid) == (OFPT_ROLE_REQUEST, 24, 9)
    assert struct.unpack("!I4xQ", msg[8:]) == (OFPCR_ROLE_MASTER, 0x1122334455667788)
    reply = struct.pack("!BBHI", OFP_VERSION, OFPT_ROLE_REPLY, 24, 9) + msg[8:]
    parsed = parse_role_reply(reply)
    assert (parsed.role, parsed.generation_id) == (OFPCR_ROLE_MASTER, 0x1122334455667788)
    assert parse_role_reply(b"short") is None


# ----------------------------------------------------------------------- HA
class RecordingDP:
    def __init__(self, sw):
        self.sw_id, self.sent, self.role = sw, [], 1

    async def send_msg(self, m):
        self.sent.append(m)
        return True


class FakePeer:
    """httpx transport emulating the peer controller's /state and /role."""
    def __init__(self, role="MASTER"):
        self.up, self.role, self.asked = True, role, []

    def handle(self, request):
        if not self.up:
            raise httpx.ConnectError("down", request=request)
        if request.url.path == "/state":
            return httpx.Response(200, json={"ha": {"role": self.role}})
        self.asked.append(request.url.path)
        return httpx.Response(200, json={"ok": True})


def ha_with(peer, preferred, dps=2, **kw):
    sm = type("SM", (), {"datapaths": {i: RecordingDP(f"s{i}") for i in range(1, dps + 1)}})()
    manager = HAManager(sm, "c", preferred=preferred, peer_url="http://peer", token="t",
                        failure_threshold=2, recovery_threshold=2,
                        transport=httpx.MockTransport(peer.handle), **kw)
    return manager, sm


def roles_sent(sm):
    return [struct.unpack("!I", m[8:12])[0] for dp in sm.datapaths.values() for m in dp.sent]


def test_standby_waits_then_promotes_when_primary_dies():
    async def run():
        peer = FakePeer("MASTER")
        ha, sm = ha_with(peer, preferred=False)
        assert ha.role_name == "SLAVE"
        await ha.check_peer()
        assert ha.role_name == "SLAVE" and not roles_sent(sm)            # primary healthy
        peer.up = False
        await ha.check_peer()
        assert ha.role_name == "SLAVE"                                    # one miss: not yet
        promoted = []
        ha.on_promoted = lambda: promoted.append(1)
        await ha.check_peer()
        assert ha.role_name == "MASTER" and promoted
        assert set(roles_sent(sm)) == {OFPCR_ROLE_MASTER}                 # every switch told
    asyncio.run(run())


def test_generation_ids_are_strictly_increasing():
    async def run():
        ha, sm = ha_with(FakePeer(), preferred=True)
        ha.enabled = True
        dp = sm.datapaths[1]
        for _ in range(3):
            await ha.request_role(dp)
        gens = [struct.unpack("!Q", m[16:24])[0] for m in dp.sent]
        assert gens == sorted(set(gens))
    asyncio.run(run())


def test_preferred_controller_starts_slave_if_peer_leads_then_standby_yields():
    async def run():
        peer = FakePeer("MASTER")
        primary, _ = ha_with(peer, preferred=True)
        await primary.decide_initial_role()
        assert primary.role_name == "SLAVE"                               # peer holds fresher state

        # Standby is master (took over); primary recovered and reports SLAVE.
        peer_primary = FakePeer("SLAVE")
        standby, sm = ha_with(peer_primary, preferred=False)
        standby.desired = OFPCR_ROLE_MASTER
        await standby.check_peer()
        assert standby.role_name == "MASTER"                              # needs 2 healthy beats
        await standby.check_peer()
        assert peer_primary.asked == ["/role"] and standby.role_name == "SLAVE"
        assert set(roles_sent(sm)) == {OFPCR_ROLE_SLAVE}
    asyncio.run(run())


def test_two_masters_resolve_in_favour_of_the_preferred():
    async def run():
        standby, _ = ha_with(FakePeer("MASTER"), preferred=False)
        standby.desired = OFPCR_ROLE_MASTER
        await standby.check_peer()
        assert standby.role_name == "SLAVE"
    asyncio.run(run())


def test_stale_generation_is_retried_not_treated_as_demotion():
    async def run():
        ha, sm = ha_with(FakePeer(), preferred=True)
        ha.enabled = True
        dp = sm.datapaths[1]
        ha.on_error(dp, 11, 0)                    # ROLE_REQUEST_FAILED / STALE
        await asyncio.sleep(0.05)
        assert ha.role_name == "MASTER" and len(dp.sent) == 1
        ha.on_error(dp, 1, 10)                    # BAD_REQUEST / IS_SLAVE: another master won
        assert ha.role_name == "SLAVE"
    asyncio.run(run())


def test_slave_controller_cannot_write_to_switches():
    async def run():
        class W:
            def __init__(self): self.data, self.closed = [], False
            def write(self, d): self.data.append(d)
            async def drain(self): pass
            def is_closing(self): return False
        writer, allowed = W(), {"master": False}
        dp = Datapath(1, None, writer, ("x", 1), write_guard=lambda: allowed["master"])
        assert await dp.send_msg(build_flow_mod()) is False               # SLAVE: blocked
        assert await dp.send_msg(parse_msg := struct.pack("!BBHI", OFP_VERSION, 18, 8, 1)) is True  # reads fine
        allowed["master"] = True
        assert await dp.send_msg(build_flow_mod()) is True                # MASTER: allowed
        assert len(writer.data) == 2
    asyncio.run(run())


def test_lone_controller_does_not_negotiate_roles():
    app_ = SDNTrafficEngineApp()
    dp = MockDatapath("s1")
    assert asyncio.run(app_.ha.request_role(dp)) is True and dp.messages == []


def test_promotion_rebuilds_forwarding_state():
    async def run():
        a = SDNTrafficEngineApp()
        a.initialize_mesh_topology()
        for n in range(1, 8):
            a.switch_manager.datapaths[n] = MockDatapath(f"s{n}")
        await a.ha.set_role("SLAVE")
        await a.ha.set_role("MASTER")
        assert a.flow_manager.active_flows                                 # routes reprogrammed
        roles = [m for m in a.switch_manager.datapaths[1].messages
                 if parse_header(m[:8]).msg_type == OFPT_ROLE_REQUEST]
        assert len(roles) == 2
    asyncio.run(run())


# --------------------------------------------- backend: edits hit the network
def agent_calls(fake):
    return [(m, p) for m, p, _ in fake.calls]


@pytest.fixture
def api(fake_agent):
    return client


def test_edits_are_applied_to_the_network_with_the_allocated_ports(api, fake_agent):
    assert api.post("/api/switches", json={"name": "s8"}).status_code == 201
    assert api.post("/api/links", json={"src": "s7", "dst": "s8", "capacity_mbps": 50, "latency_ms": 7}).status_code == 201
    host = api.post("/api/hosts", json={"name": "h9", "ip": "10.0.0.9", "connected_switch": "s8"})
    assert host.status_code == 201
    calls = {(m, p): b for m, p, b in fake_agent.calls}
    assert calls[("POST", "/switches")] == {"name": "s8", "dpid": 8}
    link = calls[("POST", "/links")]
    edge = topo.network_graph.graph["s7"]["s8"]
    assert (link["src_port"], link["dst_port"]) == (edge["src_port"], edge["dst_port"]) == (6, 1)
    assert link["bw"] == 50 and link["delay_ms"] == 7
    assert calls[("POST", "/hosts")]["port"] == 2 and calls[("POST", "/hosts")]["switch"] == "s8"
    api.patch("/api/links/s7/s8", json={"latency_ms": 9})
    api.post("/api/network/failure/simulate", json={"src_switch": "s7", "dst_switch": "s8", "action": "DOWN"})
    assert calls_last(fake_agent, "/link-state") == {"src": "s7", "dst": "s8", "up": False}
    api.delete("/api/links/s7/s8")
    api.delete("/api/hosts/h9")
    api.delete("/api/switches/s8")
    assert [c for c in agent_calls(fake_agent) if c[0] == "DELETE"] == [
        ("DELETE", "/links/s7/s8"), ("DELETE", "/hosts/h9"), ("DELETE", "/switches/s8")]


def calls_last(fake, path):
    return [b for _, p, b in fake.calls if p == path][-1]


@pytest.mark.parametrize("method,url,body", [
    ("post", "/api/switches", {"name": "s8"}),
    ("post", "/api/links", {"src": "s1", "dst": "s7"}),
    ("post", "/api/hosts", {"name": "h9", "ip": "10.0.0.9", "connected_switch": "s3"}),
    ("delete", "/api/links/s1/s2", None),
    ("delete", "/api/switches/s4", None),
    ("delete", "/api/hosts/h1", None),
    ("patch", "/api/links/s1/s2", {"latency_ms": 99}),
    ("post", "/api/network/failure/simulate", {"src_switch": "s1", "dst_switch": "s2", "action": "DOWN"}),
])
def test_failed_network_operation_rolls_the_model_back(api, fake_agent, method, url, body):
    before = topo.snapshot()
    version_before = topo.version
    fake_agent.fail_next = (500, "ovs-vsctl failed")
    kwargs = {"json": body} if body is not None else {}
    resp = getattr(api, method)(url, **kwargs)
    assert resp.status_code == 502 and "topology unchanged" in resp.json()["detail"]
    after = topo.snapshot()
    assert {k: v for k, v in after.items() if k != "version"} == {k: v for k, v in before.items() if k != "version"}
    assert topo.version > version_before                                   # versions never regress
    assert not api.get("/api/alerts").json() or "TOPOLOGY_CHANGE" not in [
        a["type"] for a in api.get("/api/alerts").json()]                   # no success alert recorded


def test_agent_conflict_is_reported_with_its_status(api, fake_agent):
    fake_agent.fail_next = (409, "OVS assigned OpenFlow port 9 instead of 6")
    resp = api.post("/api/links", json={"src": "s7", "dst": "s3"})
    assert resp.status_code == 409 and not topo.network_graph.graph.has_edge("s7", "s3")


def test_unreachable_agent_rejects_edits_instead_of_diverging(api, fake_agent):
    fake_agent.up = False
    resp = api.delete("/api/links/s1/s2")
    assert resp.status_code == 502 and topo.network_graph.graph.has_edge("s1", "s2")


# ------------------------------------------------------- reconcile / adopt
REAL = {
    "switches": [{"name": f"s{i}", "dpid": i} for i in (1, 2, 3)],
    "hosts": [{"name": "ha", "ip": "10.1.0.1", "mac": "00:00:00:00:01:01", "switch": "s1", "port": 3, "up": True},
              {"name": "hb", "ip": "10.1.0.2", "mac": "00:00:00:00:01:02", "switch": "s3", "port": 3, "up": True}],
    "links": [{"src": "s1", "dst": "s2", "src_port": 1, "dst_port": 1, "up": True, "bw": 40, "delay": "4ms", "loss": None},
              {"src": "s2", "dst": "s3", "src_port": 2, "dst_port": 1, "up": False, "bw": None, "delay": "9ms", "loss": 1.5}],
}


def test_model_drift_is_reported_and_adoption_replaces_the_model(api, fake_agent):
    fake_agent.topology = REAL
    status = api.get("/api/network/status").json()
    assert status["in_sync"] is False
    kinds = {(d["kind"], d["name"]) for d in status["drift"]}
    assert ("switch", "s4") in kinds and ("host", "h1") in kinds and ("host", "ha") in kinds

    result = api.post("/api/network/reconcile?mode=adopt").json()
    assert result["adopted"] is True and result["in_sync"] is True
    assert sorted(topo.network_graph.graph.nodes) == ["s1", "s2", "s3"]
    edge = topo.network_graph.graph["s1"]["s2"]
    assert (edge["capacity_mbps"], edge["latency_ms"], edge["data_plane_confirmed"]) == (40.0, 4.0, True)
    down = topo.network_graph.graph["s2"]["s3"]
    assert down["is_active"] is False and down["loss_pct"] == 1.5
    assert {h.name for h in topo.hosts.values()} == {"ha", "hb"}
    assert api.get("/api/network/status").json()["drift"] == []
    # routing now follows the adopted network: s2-s3 is down, so hb is unreachable
    assert routing_service.explain("10.1.0.1", "10.1.0.2")["status"] == "NO_ROUTE"


def test_drift_detects_port_and_state_mismatch(api, fake_agent):
    real = {**REAL, "switches": [{"name": s, "dpid": i} for i, s in enumerate(["s1", "s2", "s3"], 1)]}
    fake_agent.topology = REAL
    api.post("/api/network/reconcile?mode=adopt")
    topo.update_connection("s1", "s2", latency_ms=4)           # same props, no drift
    changed = {**REAL, "links": [{**REAL["links"][0], "src_port": 5}, {**REAL["links"][1], "up": True}]}
    fake_agent.topology = changed
    problems = " | ".join(d["problem"] for d in api.get("/api/network/status").json()["drift"])
    assert "port mismatch" in problems and "state mismatch" in problems


def test_status_without_agent_explains_model_only_mode(fresh_backend):
    status = client.get("/api/network/status").json()
    assert status["agent_enabled"] is False and "unconfirmed" in status["note"]


# ------------------------------------------------------ route verification
def flow(sw, priority=100, nw_dst=None, out=None, miss=False, ip=True, drop=False):
    match = {"nw_dst": nw_dst} if nw_dst else {}
    return {"switch": sw, "priority": priority, "match": match, "protocols": ["ip"] if ip and nw_dst else [],
            "out_ports": [out] if out else [], "to_controller": miss, "drop": drop, "n_packets": 4}


PORTS = {("s1", 1): "s2", ("s2", 3): "s5", ("s5", 2): "s7", ("s1", 2): "s3", ("s3", 3): "s6", ("s6", 2): "s7"}


def verify(flows, expected=("s1", "s2", "s5", "s7"), exp_ports=None):
    return verify_route(list(expected), "s1", "s7", 4, "10.0.0.7", flows, PORTS,
                        exp_ports or {"s1": 1, "s2": 3, "s5": 2, "s7": 4})


def good_tables():
    return {"s1": [flow("s1", nw_dst="10.0.0.7", out=1), flow("s1", 0, miss=True)],
            "s2": [flow("s2", nw_dst="10.0.0.7", out=3)],
            "s5": [flow("s5", nw_dst="10.0.0.7", out=2)],
            "s7": [flow("s7", nw_dst="10.0.0.7", out=4)]}


def test_verification_passes_when_tables_match_the_route():
    r = verify(good_tables())
    assert r["status"] == "VERIFIED" and r["installed_path"] == ["s1", "s2", "s5", "s7"]
    assert [h["status"] for h in r["hops"]] == ["FORWARDS", "FORWARDS", "FORWARDS", "DELIVERS_TO_HOST"]


def test_verification_reports_missing_rule_on_a_hop():
    t = good_tables(); t["s5"] = [flow("s5", 0, miss=True)]
    r = verify(t)
    assert r["status"] == "MISSING_RULES" and "s5: no forwarding rule" in r["discrepancies"][0]
    assert "table-miss" in r["discrepancies"][0]


def test_verification_reports_a_different_installed_path():
    t = good_tables()
    t["s1"] = [flow("s1", nw_dst="10.0.0.7", out=2)]                       # OVS goes s1->s3
    t["s3"] = [flow("s3", nw_dst="10.0.0.7", out=3)]
    t["s6"] = [flow("s6", nw_dst="10.0.0.7", out=2)]
    r = verify(t)
    assert r["status"] == "DIFFERENT_PATH" and r["delivered"] is True
    assert r["hops"][0]["status"] == "MISMATCH"
    assert "delivered via s1 -> s3 -> s6 -> s7" in " ".join(r["discrepancies"])


def test_verification_detects_blackhole_loop_and_unknown_switch():
    t = good_tables(); t["s2"] = [flow("s2", nw_dst="10.0.0.7", out=9)]
    assert verify(t)["status"] == "BROKEN" and "not a known link" in verify(t)["discrepancies"][0]
    t = good_tables(); t["s5"] = [flow("s5", nw_dst="10.0.0.7", out=1)]
    ports = {**PORTS, ("s5", 1): "s2"}
    r = verify_route(["s1", "s2", "s5", "s7"], "s1", "s7", 4, "10.0.0.7", t, ports)
    assert any("loop" in d for d in r["discrepancies"])
    t = good_tables(); del t["s2"]
    assert any("no flow table" in d for d in verify(t)["discrepancies"])


def test_higher_priority_rule_wins_like_ovs():
    t = good_tables()
    t["s1"] = [flow("s1", 100, nw_dst="10.0.0.7", out=1), flow("s1", 200, nw_dst="10.0.0.7", out=2)]
    r = verify(t)
    assert r["hops"][0]["installed_out_port"] == 2 and r["hops"][0]["priority"] == 200


def test_verify_endpoint_requires_agent_and_uses_ovs_dumps(api, fake_agent):
    expected = routing_service.explain("10.0.0.1", "10.0.0.8")["selected_path"]
    g = topo.network_graph.graph
    tables = {}
    for i, sw in enumerate(expected):
        out = g[sw][expected[i + 1]]["src_port"] if i + 1 < len(expected) else 5   # h8 is on s7:5
        tables[sw] = [flow(sw, nw_dst="10.0.0.8", out=out)]
    fake_agent.flows = tables
    ok = client.get("/api/routing/verify", params={"source_ip": "10.0.0.1", "dest_ip": "10.0.0.8"}).json()
    assert ok["status"] == "VERIFIED" and ok["installed_path"] == expected

    broken = {**tables, expected[1]: [flow(expected[1], 0, miss=True)]}
    fake_agent.flows = broken
    bad = client.get("/api/routing/verify", params={"source_ip": "10.0.0.1", "dest_ip": "10.0.0.8"}).json()
    assert bad["status"] == "MISSING_RULES" and bad["discrepancies"]

    summary = client.get("/api/routing/verify/all").json()
    assert summary["all_verified"] is False and sum(summary["counts"].values()) == 8
    assert client.get("/api/routing/verify", params={"source_ip": "1.1.1.1", "dest_ip": "10.0.0.8"}).status_code == 404


def test_verify_without_agent_is_unavailable_not_faked(fresh_backend):
    r = client.get("/api/routing/verify", params={"source_ip": "10.0.0.1", "dest_ip": "10.0.0.8"}).json()
    assert r["status"] == "UNAVAILABLE" and r["verified"] is False


# ----------------------------------------------------- capacity-aware cost
def two_paths(cap_top, cap_bottom):
    g = NetworkGraph()
    for s in ("a", "b", "c", "d"):
        g.add_switch(s)
    for u, v, cap in (("a", "b", cap_top), ("b", "d", cap_top), ("a", "c", cap_bottom), ("c", "d", cap_bottom)):
        g.add_link(u, v, 1, 1, capacity_mbps=cap)
        g.add_link(v, u, 1, 1, capacity_mbps=cap)
    return g


def test_capacity_term_is_off_by_default_and_changes_nothing():
    g = two_paths(10, 1000)
    calc = CostCalculator()
    assert calc.delta == 0.0
    costs = {n: calc.calculate_edge_cost(g.graph[a][b]) for n, (a, b) in {"thin": ("a", "b"), "fat": ("a", "c")}.items()}
    assert costs["thin"] == costs["fat"]


def test_video_profile_prefers_the_fat_pipe_when_everything_is_idle():
    g = two_paths(10, 1000)
    video = controller_settings.qos_profiles["VIDEO"]
    router = DijkstraRouter(g, CostCalculator(alpha=video["latency"], beta=video["utilization"],
                                              gamma=video["loss"], delta=video["capacity"]))
    result = router.explain_route("a", "d")
    assert result["selected_path"] == ["a", "c", "d"]
    assert result["candidates"][0]["cost_breakdown"]["capacity"] == 0.0
    top = result["candidates"][1]
    assert top["cost_breakdown"]["capacity"] == pytest.approx(2 * 0.15 * 0.9)
    assert "link capacity" in top["decision"] and "capacity" in result["weights"]
    assert "min(capacity" in result["formula"]


def test_capacity_flows_through_the_api(api):
    topo.update_connection("s1", "s2", capacity_mbps=10)
    topo.update_connection("s1", "s3", capacity_mbps=1000)
    video = client.post("/api/routing/recalculate", json={"source_ip": "10.0.0.1", "dest_ip": "10.0.0.7",
                                                          "qos_class": "VIDEO", "max_candidates": 10}).json()
    assert video["selected_path"][1] == "s3"
    assert video["weights"]["capacity"] == 0.15
    voice = client.post("/api/routing/recalculate", json={"source_ip": "10.0.0.1", "dest_ip": "10.0.0.7",
                                                          "qos_class": "VOICE"}).json()
    assert voice["weights"]["capacity"] == 0.0


def test_invalid_capacity_excludes_the_link():
    g = two_paths(100, 100)
    g.graph["a"]["b"]["capacity_mbps"] = 0
    assert DijkstraRouter(g).calculate_shortest_path("a", "d")[0] == ["a", "c", "d"]


# ------------------------------------- unconfirmed links on the controller
def test_controller_refuses_unconfirmed_links_until_lldp_confirms():
    async def run():
        a = SDNTrafficEngineApp()
        a.initialize_mesh_topology()
        for n in range(1, 8):
            a.switch_manager.datapaths[n] = MockDatapath(f"s{n}")
        from backend.services.topology_service import TopologyService
        t = TopologyService()
        t.add_switch("s8"); t.add_connection("s1", "s8", 1000, 0.1); t.add_connection("s8", "s7", 1000, 0.1)
        await a.apply_topology_snapshot(t.snapshot())
        edge = a.network_graph.graph["s1"]["s8"]
        assert edge["data_plane_confirmed"] is False
        assert a.router.calculate_shortest_path("s1", "s7")[0] != ["s1", "s8", "s7"]
        assert any(x["src"] == "s1" and "not confirmed" in x["reason"] for x in a.router.excluded_links())

        # LLDP proves the links exist in the data plane -> now usable.
        for u, v in (("s1", "s8"), ("s8", "s7")):
            for x, y in ((u, v), (v, u)):
                a.network_graph.graph[x][y]["data_plane_confirmed"] = True
        assert a.router.calculate_shortest_path("s1", "s7")[0] == ["s1", "s8", "s7"]

        # Agent-confirmed links arrive confirmed in the snapshot.
        t.mark_confirmed("s1", "s8"); t.mark_confirmed("s8", "s7")
        assert all(l["confirmed"] for l in t.snapshot()["links"] if "s8" in (l["src"], l["dst"]))
    asyncio.run(run())


def test_lldp_confirms_links_and_probes_dynamic_ports():
    from controller.topology.discovery import TopologyDiscovery
    from controller.openflow.protocol import build_lldp_packet, parse_lldp
    g = NetworkGraph()
    g.add_switch("s1"); g.add_switch("s2")
    g.add_link("s1", "s2", 9, 1); g.add_link("s2", "s1", 1, 9)
    g.graph["s1"]["s2"]["data_plane_confirmed"] = False
    g.graph["s2"]["s1"]["data_plane_confirmed"] = False
    disco = TopologyDiscovery(g, switch_manager=None)
    dst = type("D", (), {"sw_id": "s2"})()
    disco.handle_lldp_packet(dst, 1, build_lldp_packet(1, 9)[14:])  # strip the Ethernet header like PacketHandler
    assert g.graph["s1"]["s2"]["data_plane_confirmed"] is True
    assert g.graph["s2"]["s1"]["data_plane_confirmed"] is True

    sent = []
    class DP:
        sw_id, ports = "s1", {}
        async def send_msg(self, m): sent.append(m); return True
    sm = type("SM", (), {"datapaths": {1: DP()}})()
    disco.switch_manager = sm
    asyncio.run(disco.send_lldp_probes())
    assert len(sent) == 8        # default ports 1-7 plus the operator-added port 9
