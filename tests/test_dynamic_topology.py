"""Dynamic network modification: service-level and API-level behaviour."""
import asyncio

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.runtime import controller_monitor
from backend.services.topology_service import topology_service as topo
from tests.conftest import FakeCluster, FakeController

client = TestClient(app)


@pytest.fixture
def api(fresh_backend):
    return client


def decisions(api):
    return api.get("/api/routing/decisions").json()


def route(api, src="10.0.0.1", dst="10.0.0.8", qos="DEFAULT", k=3):
    return api.post("/api/routing/recalculate",
                    json={"source_ip": src, "dest_ip": dst, "qos_class": qos, "max_candidates": k}).json()


# ------------------------------------------------------------------ service
def test_service_validation_and_duplicates(fresh_backend):
    with pytest.raises(ValueError):
        topo.add_switch("s1")                       # duplicate
    with pytest.raises(ValueError):
        topo.add_switch("1bad")                     # invalid name
    with pytest.raises(ValueError):
        topo.add_host("hx", "999.1.1.1", "s1")      # bad IP
    with pytest.raises(ValueError):
        topo.add_host("hx", "10.0.0.1", "s1")       # duplicate IP
    with pytest.raises(ValueError):
        topo.add_host("h1", "10.0.0.50", "s1")      # duplicate name
    with pytest.raises(ValueError):
        topo.add_host("hx", "224.0.0.1", "s1")      # multicast
    with pytest.raises(ValueError):
        topo.add_host("hx", "10.0.0.50", "s1", mac="zz")
    with pytest.raises(ValueError):
        topo.add_host("hx", "10.0.0.50", "s1", mac="00:00:00:00:00:01")  # duplicate MAC
    with pytest.raises(KeyError):
        topo.add_host("hx", "10.0.0.50", "s99")
    with pytest.raises(ValueError):
        topo.add_connection("s1", "s2", 100, 5)     # duplicate link
    with pytest.raises(ValueError):
        topo.add_connection("s1", "s1", 100, 5)     # self loop
    with pytest.raises(KeyError):
        topo.add_connection("s1", "s99", 100, 5)
    with pytest.raises(KeyError):
        topo.remove_connection("s1", "s7")
    with pytest.raises(ValueError):
        topo.update_connection("s1", "s2")           # nothing to change


def test_hosts_persist_across_topology_reads(fresh_backend):
    topo.add_host("h9", "10.0.0.9", "s3")
    assert "h9" in {h.name for h in topo.get_topology().hosts}
    topo.remove_host("h1")
    assert "h1" not in {h.name for h in topo.get_topology().hosts}


def test_snapshot_reflects_every_edit_and_bumps_version(fresh_backend):
    v0 = topo.version
    topo.add_switch("s8")
    topo.add_connection("s7", "s8", 50, 9, 0.5)
    topo.add_host("h9", "10.0.0.9", "s8")
    topo.update_connection("s7", "s8", latency_ms=12)
    topo.set_link_state("s1", "s2", False)
    snap = topo.snapshot()
    assert topo.version == v0 + 5 and snap["version"] == topo.version
    assert "s8" in snap["switches"]
    link = next(l for l in snap["links"] if (l["src"], l["dst"]) == ("s7", "s8"))
    assert (link["capacity_mbps"], link["latency_ms"], link["loss_pct"]) == (50, 12, 0.5)
    assert next(l for l in snap["links"] if (l["src"], l["dst"]) == ("s1", "s2"))["is_active"] is False
    assert any(h["ip"] == "10.0.0.9" and h["switch"] == "s8" for h in snap["hosts"])


def test_auto_assigned_macs_stay_unique_after_deletions(fresh_backend):
    topo.add_host("a", "10.0.1.1", "s2")
    topo.remove_host("h1")
    topo.add_host("b", "10.0.1.2", "s2")
    macs = [h.mac for h in topo.hosts.values()]
    assert len(macs) == len(set(macs))


# ---------------------------------------------------------------------- API
def test_api_error_codes(api):
    assert api.post("/api/switches", json={"name": "s1"}).status_code == 409
    assert api.post("/api/switches", json={"name": "!!"}).status_code == 422
    assert api.delete("/api/switches/s99").status_code == 404
    assert api.post("/api/hosts", json={"name": "hz", "ip": "bad", "connected_switch": "s1"}).status_code == 422
    assert api.post("/api/hosts", json={"name": "hz", "ip": "999.9.9.9", "connected_switch": "s1"}).status_code == 409
    assert api.post("/api/links", json={"src": "s1", "dst": "s2"}).status_code == 409
    assert api.post("/api/links", json={"src": "s1", "dst": "s99"}).status_code == 404
    assert api.post("/api/links", json={"src": "s1", "dst": "s7", "capacity_mbps": -1}).status_code == 422
    assert api.post("/api/links", json={"src": "s1", "dst": "s7", "latency_ms": "nan"}).status_code == 422
    assert api.patch("/api/links/s1/s2", json={}).status_code == 422
    assert api.patch("/api/links/s1/s7", json={"latency_ms": 1}).status_code == 404
    assert api.patch("/api/links/s1/s2", json={"loss_pct": 101}).status_code == 422
    assert api.post("/api/network/failure/simulate", json={"src_switch": "s1", "dst_switch": "s7"}).status_code == 404
    assert api.post("/api/network/failure/simulate", json={"src_switch": "s1", "dst_switch": "s2", "action": "SIDEWAYS"}).status_code == 422
    assert api.post("/api/routing/recalculate", json={"source_ip": "1.1.1.1", "dest_ip": "10.0.0.8"}).status_code == 404


def test_removing_link_on_selected_route_reroutes_and_records_decision(api):
    before = route(api)
    path = before["selected_path"]
    assert path[0] == "s1" and path[-1] == "s7"
    a, b = path[0], path[1]
    resp = api.delete(f"/api/links/{a}/{b}")
    assert resp.status_code == 200
    changes = resp.json()["route_changes"]
    moved = next(c for c in changes if (c["source_ip"], c["dest_ip"]) == ("10.0.0.1", "10.0.0.8"))
    assert moved["old_path"] == path and moved["new_path"] != path
    assert f"link {a}-{b} was removed" in moved["reason"]
    after = route(api)
    assert after["selected_path"] == moved["new_path"]
    assert all(f"{x}-{y}" != f"{a}-{b}" for x, y in zip(after["selected_path"], after["selected_path"][1:]))
    stored = decisions(api)
    assert any(d["decision_id"] == moved["decision_id"] for d in stored)


def test_removing_active_switch_reroutes_and_drops_its_hosts(api):
    path = route(api)["selected_path"]
    middle = path[1]
    resp = api.delete(f"/api/switches/{middle}")
    assert resp.status_code == 200
    new_path = route(api)["selected_path"]
    assert middle not in new_path and new_path[0] == "s1"
    api.post("/api/hosts", json={"name": "h9", "ip": "10.0.0.9", "connected_switch": "s4"})
    assert api.delete("/api/switches/s4").json()["removed_hosts"] == ["h9"]
    assert "h9" not in {h["name"] for h in api.get("/api/hosts").json()}


def test_disconnect_then_restore_connectivity(api):
    for pair in ("s7/s4", "s7/s5", "s7/s6"):
        assert api.post("/api/network/failure/simulate",
                        json={"src_switch": pair.split("/")[0], "dst_switch": pair.split("/")[1], "action": "DOWN"}).status_code == 200
    result = route(api)
    assert result["status"] == "NO_ROUTE" and result["selected_path"] is None
    assert "can only reach" in result["explanation"]
    assert len(result["excluded_links"]) >= 6
    assert any(d["new_path"] == [] and "No route remains" in d["reason"] for d in decisions(api))

    resp = api.post("/api/network/failure/simulate", json={"src_switch": "s7", "dst_switch": "s5", "action": "UP"})
    assert resp.status_code == 200
    restored = route(api)
    assert restored["status"] == "SUCCESS" and restored["selected_path"][-2:] == ["s5", "s7"]
    assert any("Connectivity restored" in d["reason"] for d in decisions(api))


def test_link_property_change_flows_into_routing_and_explanation(api):
    base = route(api, "10.0.0.1", "10.0.0.7")
    sel = base["selected_path"]
    hop = (sel[0], sel[1])
    resp = api.patch(f"/api/links/{hop[0]}/{hop[1]}", json={"latency_ms": 90})
    assert resp.status_code == 200 and resp.json()["applied"] == {"latency_ms": 90.0}
    after = route(api, "10.0.0.1", "10.0.0.7", k=10)
    assert after["selected_path"] != sel
    rejected = next(c for c in after["candidate_paths"] if c["path"] == sel)
    assert "latency" in rejected["decision"]
    edge = next(e for e in rejected["edge_metrics"] if (e["src"], e["dst"]) == hop)
    assert edge["latency_ms"] == 90.0
    link = next(l for l in api.get("/api/links").json() if l["link_id"] == f"{hop[0]}-{hop[1]}")
    assert link["latency_ms"] == 90.0


def test_model_only_links_are_excluded_from_routing(api):
    """Without a live network a new link is unconfirmed and must not carry traffic."""
    api.post("/api/switches", json={"name": "s8"})
    api.post("/api/links", json={"src": "s1", "dst": "s8", "latency_ms": 0.5, "capacity_mbps": 1000})
    api.post("/api/links", json={"src": "s8", "dst": "s7", "latency_ms": 0.5, "capacity_mbps": 1000})
    result = route(api)
    assert "s8" not in result["selected_path"]
    assert any("not confirmed in the data plane" in x["reason"] for x in result["excluded_links"])
    assert api.get("/api/links").json()[-1]["data_plane_confirmed"] is False


def test_new_switch_and_link_become_a_usable_route(api, fake_agent):
    api.post("/api/switches", json={"name": "s8"})
    api.post("/api/links", json={"src": "s1", "dst": "s8", "latency_ms": 0.5, "capacity_mbps": 1000})
    api.post("/api/links", json={"src": "s8", "dst": "s7", "latency_ms": 0.5, "capacity_mbps": 1000})
    assert route(api)["selected_path"] == ["s1", "s8", "s7"]
    link = next(l for l in api.get("/api/links").json() if l["link_id"] == "s1-s8")
    assert link["data_plane_confirmed"] is True   # the running network really has it


def test_rapid_consecutive_modifications_keep_model_consistent(api):
    versions = []
    for i in range(10):
        r = api.post("/api/switches", json={"name": f"x{i}"})
        assert r.status_code == 201
        versions.append(r.json()["topology_version"])
    assert versions == sorted(set(versions))
    for i in range(10):
        assert api.delete(f"/api/switches/x{i}").status_code == 200
    assert len(api.get("/api/switches").json()) == 7


def test_host_attached_to_new_switch_routes_after_linking(api, fake_agent):
    api.post("/api/switches", json={"name": "s8"})
    api.post("/api/hosts", json={"name": "h9", "ip": "10.0.0.9", "connected_switch": "s8"})
    assert route(api, "10.0.0.1", "10.0.0.9")["status"] == "NO_ROUTE"
    api.post("/api/links", json={"src": "s8", "dst": "s7"})
    assert route(api, "10.0.0.1", "10.0.0.9")["selected_path"][-2:] == ["s7", "s8"]


# ------------------------------------------------- sync with controller (fake)
def test_changes_are_synced_to_controller_and_queued_while_down(api, token):
    fake = FakeController()
    cluster = FakeCluster(primary=fake)
    controller_monitor.endpoints = [cluster.ports["primary"]]
    controller_monitor.endpoint_health = {u: {"healthy": None, "last_probe": None, "error": None} for u in controller_monitor.endpoints}
    controller_monitor.transport = cluster.transport

    asyncio.run(controller_monitor.check_once())
    assert controller_monitor.status == "UP" and fake.syncs  # initial connect pushes the model

    r = api.post("/api/switches", json={"name": "s8"})
    assert r.json()["sync_status"] == "SYNCED"
    assert "s8" in fake.syncs[-1]["switches"]

    fake.up = False
    controller_monitor.status = "DOWN"
    r = api.post("/api/links", json={"src": "s7", "dst": "s8"})
    assert r.status_code == 201 and r.json()["sync_status"] == "PENDING_CONTROLLER_UNAVAILABLE"
    assert controller_monitor.pending_sync is True
    assert "s8" not in [l["dst"] for l in fake.syncs[-1]["links"] if l["src"] == "s7"]

    fake.up = True
    for _ in range(controller_monitor.recovery_threshold):
        asyncio.run(controller_monitor.check_once())
    assert controller_monitor.status == "UP" and controller_monitor.pending_sync is False
    assert any((l["src"], l["dst"]) == ("s7", "s8") for l in fake.syncs[-1]["links"])
