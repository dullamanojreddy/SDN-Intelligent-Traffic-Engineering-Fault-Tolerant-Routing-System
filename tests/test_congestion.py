"""
Unit tests for Congestion Detection, Failure Recovery, and Backend APIs
"""
import pytest
from controller.topology.graph import NetworkGraph
from controller.congestion.detector import CongestionDetector
from controller.failure.detector import FailureDetector, RecoveryEngine
from controller.routing.dijkstra import DijkstraRouter
from controller.models.event import EventType

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
