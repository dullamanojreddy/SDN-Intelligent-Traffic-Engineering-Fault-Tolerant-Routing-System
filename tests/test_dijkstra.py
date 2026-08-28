"""
Unit tests for Dijkstra multi-metric routing & path optimization
"""
import pytest
from controller.topology.graph import NetworkGraph
from controller.routing.dijkstra import DijkstraRouter
from controller.routing.cost_function import CostCalculator
from controller.routing.path_optimizer import PathOptimizer

def create_sample_diamond_topology():
    g = NetworkGraph()
    for sw in ["s1", "s2", "s3", "s4"]:
        g.add_switch(sw)
    # Primary top path: s1-s2-s4
    g.add_link("s1", "s2", 1, 1, capacity_mbps=100.0, latency_ms=5.0, utilization_pct=20.0)
    g.add_link("s2", "s4", 2, 1, capacity_mbps=100.0, latency_ms=5.0, utilization_pct=20.0)
    # Alternate bottom path: s1-s3-s4
    g.add_link("s1", "s3", 2, 1, capacity_mbps=100.0, latency_ms=10.0, utilization_pct=20.0)
    g.add_link("s3", "s4", 2, 2, capacity_mbps=100.0, latency_ms=10.0, utilization_pct=20.0)
    return g

def test_dijkstra_shortest_path():
    g = create_sample_diamond_topology()
    router = DijkstraRouter(g)
    path, cost = router.calculate_shortest_path("s1", "s4")
    assert path == ["s1", "s2", "s4"]
    assert cost > 0

def test_dijkstra_reroutes_on_congestion():
    g = create_sample_diamond_topology()
    # Heavily congest S2-S4 link (95% utilization)
    g.update_link_metrics("s2", "s4", utilization_pct=95.0)
    
    router = DijkstraRouter(g)
    path, cost = router.calculate_shortest_path("s1", "s4")
    # Bottom path s1-s3-s4 should now be preferred over congested top path
    assert path == ["s1", "s3", "s4"]

def test_dijkstra_k_shortest_paths():
    g = create_sample_diamond_topology()
    router = DijkstraRouter(g)
    k_paths = router.calculate_k_shortest_paths("s1", "s4", k=2)
    assert len(k_paths) == 2
    assert k_paths[0]["path"] == ["s1", "s2", "s4"]
    assert k_paths[1]["path"] == ["s1", "s3", "s4"]

def test_dijkstra_unreachable():
    g = NetworkGraph()
    g.add_switch("s1")
    g.add_switch("s2")
    router = DijkstraRouter(g)
    path, cost = router.calculate_shortest_path("s1", "s2")
    assert path is None
    assert cost == float("inf")
