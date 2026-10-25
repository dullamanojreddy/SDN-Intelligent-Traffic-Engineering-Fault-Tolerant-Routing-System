"""
Unit tests for Congestion Detection, Failure Recovery, and Backend APIs
"""
import pytest
import asyncio
from controller.topology.graph import NetworkGraph
from controller.congestion.detector import CongestionDetector
from controller.failure.detector import FailureDetector, RecoveryEngine
from controller.routing.dijkstra import DijkstraRouter
from controller.models.event import EventType
from controller.app import SDNTrafficEngineApp
from controller.openflow.protocol import OFPFC_ADD, OFPFC_MODIFY, ETH_TYPE_IP
from controller.openflow.flow_manager import FlowManager

def test_congestion_persistence():
    detector = CongestionDetector(threshold_pct=85.0, persistence_cycles=3, cooldown_sec=5.0)
    
    # 1st cycle: breach
    ev1 = detector.check_link("s1-s2", 90.0)
    assert ev1 is None
    
    # 2nd cycle: breach
    ev2 = detector.check_link("s1-s2", 92.0)
    assert ev2 is None
    
    # 3rd cycle: persistent breach triggers event
    ev3 = detector.check_link("s1-s2", 89.0)
    assert ev3 is not None
    assert ev3.type == EventType.LINK_CONGESTION

def test_link_failure_and_recovery():
    g = NetworkGraph()
    for sw in ["s1", "s2", "s3", "s4"]:
        g.add_switch(sw)
    g.add_link("s1", "s2", 1, 1, capacity_mbps=100.0, latency_ms=5.0, utilization_pct=10.0)
    g.add_link("s2", "s4", 2, 1, capacity_mbps=100.0, latency_ms=5.0, utilization_pct=10.0)
    g.add_link("s1", "s3", 2, 1, capacity_mbps=100.0, latency_ms=10.0, utilization_pct=10.0)
    g.add_link("s3", "s4", 2, 2, capacity_mbps=100.0, latency_ms=10.0, utilization_pct=10.0)
    
    detector = FailureDetector(g)
    router = DijkstraRouter(g)
    recovery = RecoveryEngine(router)
    
    # Simulate S2 port 2 down
    events = detector.handle_port_down("s2", 2)
    assert len(events) >= 1
    assert events[0].type == EventType.LINK_FAILURE
    
    # Compute recovery failover path
    new_path, cost, duration = recovery.compute_failover_path("s1", "s4", "s2-s4")
    assert new_path == ["s1", "s3", "s4"]
    assert duration >= 0

def test_flow_manager_modifies_existing_destination_rule():
    class MockDatapath:
        sw_id = "s1"
        dpid = 1

        def __init__(self):
            self.messages = []

        async def send_msg(self, message):
            self.messages.append(message)
            return True

    async def run_test():
        datapath = MockDatapath()
        manager = FlowManager(type("SwitchManager", (), {})())
        match = {"eth_type": ETH_TYPE_IP, "ipv4_dst": "10.0.0.7"}

        assert await manager.install_flow(datapath, match, out_port=1) is True
        assert await manager.install_flow(datapath, match, out_port=2) is True

        assert manager.active_flows["s1_2048_10.0.0.7_100"]["out_port"] == 2
        assert datapath.messages[0][25] == OFPFC_ADD
        assert datapath.messages[1][25] == OFPFC_MODIFY

    asyncio.run(run_test())

def test_failover_recovery_reinstalls_routes_for_known_hosts():
    class MockDatapath:
        def __init__(self, sw_id):
            self.sw_id = sw_id
            self.dpid = int(sw_id[1:])
            self.messages = []

        async def send_msg(self, message):
            self.messages.append(message)
            return True

    async def run_test():
        app = SDNTrafficEngineApp()
        app.initialize_mesh_topology()
        for number in range(1, 8):
            app.switch_manager.datapaths[number] = MockDatapath(f"s{number}")

        events = app.failure_detector.handle_port_down("s1", 1)
        assert events
        await app._recover_host_routes("s1-s2")

        recovery_event = app.event_manager.get_recent_events(1)[0]
        assert recovery_event.data["failed_link"] == "s1-s2"
        assert recovery_event.data["status"] == "routes_recalculated"
        assert app.network_graph.graph["s1"]["s2"]["is_active"] is False
        assert app.network_graph.graph["s1"]["s3"]["is_active"] is True
        assert app.switch_manager.datapaths[3].messages

    asyncio.run(run_test())
