"""Issues found during the final QA pass (browser + real-OVS runs), as regression tests."""
import asyncio
import struct

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.controller_monitor import ControllerMonitor
from backend.services.runtime import controller_monitor, orchestrator
from backend.services.topology_service import TopologyService, topology_service as topo
from controller import ha as ha_module
from controller.ha import HAManager, NO_GENERATION
from controller.openflow.protocol import (
    OFPCR_ROLE_MASTER, OFPCR_ROLE_NOCHANGE, OFP_VERSION, OFPT_ROLE_REPLY, RoleReply, parse_header,
)
from controller.routing.dijkstra import DijkstraRouter
from controller.topology.graph import NetworkGraph
from tests.conftest import FakeCluster, FakeController
from tests.test_dataplane_integration import RecordingDP

client = TestClient(app)


# ---------------------------------------------------- noise vs equal-cost ties
def test_control_plane_noise_does_not_flip_equal_cost_paths():
    """LLDP/echo chatter measured as ~0.0002% utilization used to break ties and
    produced spurious 'route change' decisions."""
    g = NetworkGraph()
    for sw in ("a", "b", "c", "d"):
        g.add_switch(sw)
    for u, v in (("a", "b"), ("b", "d"), ("a", "c"), ("c", "d")):
        g.add_link(u, v, 1, 1)
        g.add_link(v, u, 1, 1)
    router = DijkstraRouter(g)
    baseline = router.calculate_shortest_path("a", "d")[0]
    for u, v in (("a", "b"), ("b", "d")):
        g.graph[u][v]["utilization_pct"] = 0.00018731      # the value seen on the real bench
    assert router.calculate_shortest_path("a", "d")[0] == baseline
    g.graph["a"]["b"]["utilization_pct"] = 5.0             # real load still matters
    assert router.calculate_shortest_path("a", "d")[0] == ["a", "c", "d"]


# ---------------------------------------------------------- generation ids
def test_skewed_clock_cannot_stay_stale_forever(monkeypatch):
    """A controller whose clock is far behind learns the switch's generation id and
    retries above it instead of failing every promotion."""
    async def run():
        monkeypatch.setattr(ha_module, "next_generation_id", lambda: 1_000)      # clock far in the past
        sm = type("SM", (), {"datapaths": {}})()
        ha = HAManager(sm, "late", preferred=True, peer_url="http://p", token="t")
        dp = RecordingDP("s1")
        sm.datapaths[1] = dp
        await ha.request_role(dp)
        first_gen = struct.unpack("!Q", dp.sent[0][16:24])[0]
        assert first_gen < 5_000
        ha.on_error(dp, 11, 0)                                                   # STALE
        await asyncio.sleep(0.05)
        query = dp.sent[1]
        assert struct.unpack("!I", query[8:12])[0] == OFPCR_ROLE_NOCHANGE        # asks the switch
        await ha.on_role_reply(dp, RoleReply(role=1, generation_id=9_000_000_000_000))
        retry = dp.sent[2]
        assert struct.unpack("!I", retry[8:12])[0] == OFPCR_ROLE_MASTER
        assert struct.unpack("!Q", retry[16:24])[0] == 9_000_000_000_001          # strictly above the switch
        assert ha.switch_generations["s1"] == 9_000_000_000_000
    asyncio.run(run())


def test_unset_switch_generation_is_not_treated_as_a_huge_value():
    async def run():
        sm = type("SM", (), {"datapaths": {}})()
        ha = HAManager(sm, "c", preferred=True, peer_url="http://p", token="t")
        dp = RecordingDP("s1")
        await ha.on_role_reply(dp, RoleReply(role=1, generation_id=NO_GENERATION))
        assert ha.generation_id < NO_GENERATION and "s1" not in ha.switch_generations
    asyncio.run(run())


def test_backend_recovers_from_a_controller_holding_a_newer_version():
    primary = FakeController()
    primary.applied_version = 10 ** 15               # e.g. backend restarted on a clock that is behind
    cluster = FakeCluster(primary=primary)
    service = TopologyService()
    service.version = 5
    monitor = ControllerMonitor([cluster.ports["primary"]], lambda: "test-token", service.snapshot,
                                transport=cluster.transport,
                                on_version_conflict=service.ensure_version_above)
    asyncio.run(monitor.check_once())
    assert monitor.status == "UP" and monitor.pending_sync is False
    assert service.version > 10 ** 15 and primary.syncs[-1]["version"] == service.version


# --------------------------------------------------------------- alerts
def test_controller_alerts_are_resolved_after_recovery(fresh_backend):
    async def run():
        await orchestrator.on_controller_event({"type": "CONTROLLER_DOWN", "severity": "CRITICAL", "message": "down",
                                                "timestamp": "t", "data": {"active_url": "u"}})
        assert [a["status"] for a in await _alerts()] == ["ACTIVE"]
        await orchestrator.on_controller_event({"type": "CONTROLLER_RECOVERED", "severity": "INFO", "message": "up",
                                                "timestamp": "t", "data": {"active_url": "u", "sync_status": "SYNCED"}})
        by_type = {a["type"]: a["status"] for a in await _alerts()}
        assert by_type == {"CONTROLLER_DOWN": "RESOLVED", "CONTROLLER_RECOVERED": "RESOLVED"}
        # An unsynced recovery must not close the outage alert.
        await orchestrator.on_controller_event({"type": "CONTROLLER_DOWN", "severity": "CRITICAL", "message": "d2",
                                                "timestamp": "t", "data": {"active_url": "u"}})
        await orchestrator.on_controller_event({"type": "CONTROLLER_RECOVERED", "severity": "WARNING", "message": "u2",
                                                "timestamp": "t", "data": {"active_url": "u", "sync_status": "PENDING_CONTROLLER_UNAVAILABLE"}})
        assert any(a["type"] == "CONTROLLER_DOWN" and a["status"] == "ACTIVE" for a in await _alerts())
    asyncio.run(run())


async def _alerts():
    from backend.database.connection import db_manager
    return await db_manager.find("alerts", limit=50)


# ----------------------------------------------- no fake success responses
def test_traffic_endpoints_refuse_instead_of_pretending_without_an_agent(fresh_backend):
    assert client.post("/api/network/traffic/start",
                       json={"src_host": "h1", "dst_host": "h7"}).status_code == 503
    assert client.post("/api/network/traffic/stop").status_code == 503


def test_traffic_goes_to_the_real_network_when_an_agent_is_attached(fresh_backend, fake_agent):
    ok = client.post("/api/network/traffic/start",
                     json={"src_host": "h1", "dst_host": "h7", "rate_mbps": 20, "duration_sec": 5, "protocol": "UDP"})
    assert ok.status_code == 200
    assert fake_agent.calls[-1][1] == "/traffic-start"
    assert fake_agent.calls[-1][2] == {"src": "h1", "dst": "h7", "rate_mbps": 20.0, "duration_sec": 5, "protocol": "UDP"}
    assert client.post("/api/network/traffic/start",
                       json={"src_host": "nope", "dst_host": "h7"}).status_code == 404
    assert client.post("/api/network/traffic/stop").status_code == 200


def test_experiments_report_what_exists_not_canned_results(fresh_backend):
    assert client.get("/api/experiments").json() == []
    assert client.post("/api/experiments/start", json={"name": "x", "type": "y"}).status_code == 501
    assert client.post("/api/experiments/stop").status_code == 409


# ------------------------------------------------------------- flows API
def test_flows_api_serves_real_ovs_tables_with_counters(fresh_backend, fake_agent):
    fake_agent.flows = {"s1": [
        {"switch": "s1", "priority": 100, "match": {"nw_dst": "10.0.0.7"}, "protocols": ["ip"], "out_ports": [1],
         "to_controller": False, "drop": False, "n_packets": 42, "n_bytes": 4096, "duration": 7.5, "table": 0},
        {"switch": "s1", "priority": 0, "match": {}, "protocols": [], "out_ports": [], "to_controller": True,
         "drop": False, "n_packets": 3, "n_bytes": 100, "duration": 9.0, "table": 0}]}
    flows = client.get("/api/flows").json()
    rule = next(f for f in flows if f["priority"] == 100)
    assert rule["match"] == {"ipv4_dst": "10.0.0.7"} and rule["packet_count"] == 42 and rule["source"] == "ovs"
    assert rule["instructions"][0]["actions"] == ["OUTPUT:1"]
    assert next(f for f in flows if f["priority"] == 0)["instructions"][0]["actions"] == ["CONTROLLER"]


# ------------------------------------------------------------ auth hygiene
def test_management_api_token_comparison_is_constant_time():
    import inspect
    from controller import management_api
    assert "compare_digest" in inspect.getsource(management_api)


# ------------------------------------- configured loss must survive telemetry
def test_configured_loss_is_not_overwritten_by_measured_drops(fresh_backend):
    """Regression from the demo walk-through: loss set on a link (netem) was reset to
    0% by the next telemetry merge because netem drops are not port drop counters."""
    topo.update_connection("s1", "s2", loss_pct=2.0)
    state = {"switches": [], "links": [
        {"src": "s1", "dst": "s2", "is_active": True, "utilization_pct": 0.0, "loss_pct": 0.0,
         "measured_loss_pct": 0.0, "data_plane_confirmed": True}]}
    topo.apply_live_state(state)
    assert topo.network_graph.graph["s1"]["s2"]["loss_pct"] == 2.0
    link = next(l for l in topo.get_topology().links if l.link_id == "s1-s2")
    assert link.packet_loss_pct == 2.0
    state["links"][0]["measured_loss_pct"] = 5.0           # real drops worse than configured
    topo.apply_live_state(state)
    assert next(l for l in topo.get_topology().links if l.link_id == "s1-s2").packet_loss_pct == 5.0
    assert topo.network_graph.graph["s1"]["s2"]["loss_pct"] == 2.0


def test_lossy_link_loses_the_route_and_the_explanation_says_why(fresh_backend):
    base = client.post("/api/routing/recalculate", json={"source_ip": "10.0.0.1", "dest_ip": "10.0.0.7"}).json()
    first = base["selected_path"][:2]
    client.patch(f"/api/links/{first[0]}/{first[1]}", json={"loss_pct": 10})
    topo.apply_live_state({"switches": [], "links": [
        {"src": first[0], "dst": first[1], "is_active": True, "utilization_pct": 0.0, "measured_loss_pct": 0.0}]})
    after = client.post("/api/routing/recalculate",
                        json={"source_ip": "10.0.0.1", "dest_ip": "10.0.0.7", "max_candidates": 10}).json()
    assert after["selected_path"][:2] != first
    old = next(c for c in after["candidate_paths"] if c["path"][:2] == first)
    assert "packet loss" in old["decision"]


def test_stats_manager_updates_measured_not_configured_loss():
    g = NetworkGraph()
    g.add_switch("a"); g.add_switch("b")
    g.add_link("a", "b", 1, 1, loss_pct=3.0)
    g.update_link_packet_loss("a", "b", 0.0)
    assert g.graph["a"]["b"]["loss_pct"] == 3.0 and g.graph["a"]["b"]["measured_loss_pct"] == 0.0
    router = DijkstraRouter(g)
    assert router.cost_calculator.normalized_metrics(g.graph["a"]["b"])["packet_loss_pct"] == 3.0
