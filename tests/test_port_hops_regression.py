"""
Regression and Port-Hop Topology Verification Tests
Verifies that multi-hop paths correctly derive input and output ports across all valid mesh combinations.
"""
import pytest
from controller.topology.graph import NetworkGraph
from controller.openflow.packet_handler import PacketHandler
from controller.routing.dijkstra import DijkstraRouter


def build_mesh_graph() -> NetworkGraph:
    """Builds the 7-switch mesh topology matching Mininet."""
    g = NetworkGraph()
    for sw in ["s1", "s2", "s3", "s4", "s5", "s6", "s7"]:
        g.add_switch(sw)

    links = [
        ("s1", "s2", 1, 1, 100.0, 5.0),
        ("s1", "s3", 2, 1, 100.0, 5.0),
        ("s2", "s4", 2, 1, 100.0, 6.0),
        ("s2", "s5", 3, 1, 100.0, 5.0),
        ("s3", "s4", 2, 2, 100.0, 6.0),
        ("s3", "s6", 3, 1, 100.0, 5.0),
        ("s4", "s7", 3, 1, 100.0, 5.0),
        ("s5", "s7", 2, 2, 100.0, 5.0),
        ("s6", "s7", 2, 3, 100.0, 5.0),
    ]
    for u, v, p1, p2, cap, lat in links:
        g.add_link(u, v, p1, p2, capacity_mbps=cap, latency_ms=lat)
        g.add_link(v, u, p2, p1, capacity_mbps=cap, latency_ms=lat)
    return g


class FakePacketHandler:
    """Wrapper to test _build_port_hops independently."""
    def __init__(self, network_graph: NetworkGraph):
        self.network_graph = network_graph
        self._build_port_hops = PacketHandler._build_port_hops.__get__(self)


def test_port_hops_s1_s2_s5_s7():
    """Verify s1 -> s2 -> s5 -> s7 produces exact output ports."""
    g = build_mesh_graph()
    handler = FakePacketHandler(g)
    path = ["s1", "s2", "s5", "s7"]
    hops = handler._build_port_hops(path, ingress_port=3, egress_port=4)

    assert hops == [
        ("s1", 3, 1),  # s1: in=h1(3), out=s2(1)
        ("s2", 1, 3),  # s2: in=s1(1), out=s5(3)
        ("s5", 1, 2),  # s5: in=s2(1), out=s7(2)
        ("s7", 2, 4),  # s7: in=s5(2), out=h7(4)
    ]


def test_port_hops_s1_s3_s6_s7():
    """Verify s1 -> s3 -> s6 -> s7 produces exact output ports."""
    g = build_mesh_graph()
    handler = FakePacketHandler(g)
    path = ["s1", "s3", "s6", "s7"]
    hops = handler._build_port_hops(path, ingress_port=3, egress_port=4)

    assert hops == [
        ("s1", 3, 2),  # s1: in=h1(3), out=s3(2)
        ("s3", 1, 3),  # s3: in=s1(1), out=s6(3)
        ("s6", 1, 2),  # s6: in=s3(1), out=s7(2)
        ("s7", 3, 4),  # s7: in=s6(3), out=h7(4)
    ]


def test_port_hops_s1_s2_s4_s7():
    """Verify s1 -> s2 -> s4 -> s7 produces exact output ports."""
    g = build_mesh_graph()
    handler = FakePacketHandler(g)
    path = ["s1", "s2", "s4", "s7"]
    hops = handler._build_port_hops(path, ingress_port=3, egress_port=4)

    assert hops == [
        ("s1", 3, 1),  # s1: in=h1(3), out=s2(1)
        ("s2", 1, 2),  # s2: in=s1(1), out=s4(2)
        ("s4", 1, 3),  # s4: in=s2(1), out=s7(3)
        ("s7", 1, 4),  # s7: in=s4(1), out=h7(4)
    ]


def test_port_hops_s1_s3_s4_s7():
    """Verify s1 -> s3 -> s4 -> s7 produces exact output ports."""
    g = build_mesh_graph()
    handler = FakePacketHandler(g)
    path = ["s1", "s3", "s4", "s7"]
    hops = handler._build_port_hops(path, ingress_port=3, egress_port=4)

    assert hops == [
        ("s1", 3, 2),  # s1: in=h1(3), out=s3(2)
        ("s3", 1, 2),  # s3: in=s1(1), out=s4(2)
        ("s4", 2, 3),  # s4: in=s3(2), out=s7(3)
        ("s7", 1, 4),  # s7: in=s4(1), out=h7(4)
    ]


def test_port_hops_reverse_s7_s6_s3_s1():
    """Verify return path s7 -> s6 -> s3 -> s1 produces exact return ports."""
    g = build_mesh_graph()
    handler = FakePacketHandler(g)
    path = ["s7", "s6", "s3", "s1"]
    hops = handler._build_port_hops(path, ingress_port=4, egress_port=3)

    assert hops == [
        ("s7", 4, 3),  # s7: in=h7(4), out=s6(3)
        ("s6", 2, 1),  # s6: in=s7(2), out=s3(1)
        ("s3", 3, 1),  # s3: in=s6(3), out=s1(1)
        ("s1", 2, 3),  # s1: in=s3(2), out=h1(3)
    ]


def test_port_hops_reverse_s7_s5_s2_s1():
    """Verify return path s7 -> s5 -> s2 -> s1 produces exact return ports."""
    g = build_mesh_graph()
    handler = FakePacketHandler(g)
    path = ["s7", "s5", "s2", "s1"]
    hops = handler._build_port_hops(path, ingress_port=5, egress_port=4)  # h8 -> h2

    assert hops == [
        ("s7", 5, 2),  # s7: in=h8(5), out=s5(2)
        ("s5", 2, 1),  # s5: in=s7(2), out=s2(1)
        ("s2", 3, 1),  # s2: in=s5(3), out=s1(1)
        ("s1", 1, 4),  # s1: in=s2(1), out=h2(4)
    ]


def test_port_hops_graceful_on_empty_and_single_node():
    """Verify graceful behavior on empty and 1-hop path."""
    g = build_mesh_graph()
    handler = FakePacketHandler(g)
    assert handler._build_port_hops([], 1, 2) == []
    assert handler._build_port_hops(["s1"], 3, 4) == [("s1", 3, 4)]
