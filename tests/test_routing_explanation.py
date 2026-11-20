"""Routing decision and explanation logic, driven by the real graph and cost model."""
import pytest

from controller.routing.cost_function import CostCalculator
from controller.routing.dijkstra import DijkstraRouter
from controller.topology.graph import NetworkGraph


def diamond(lat_top=5.0, lat_bottom=5.0):
    g = NetworkGraph()
    for sw in ("s1", "s2", "s3", "s4"):
        g.add_switch(sw)
    for u, v, p1, p2, lat in (("s1", "s2", 1, 1, lat_top), ("s2", "s4", 2, 1, lat_top),
                              ("s1", "s3", 2, 1, lat_bottom), ("s3", "s4", 2, 2, lat_bottom)):
        g.add_link(u, v, p1, p2, latency_ms=lat)
        g.add_link(v, u, p2, p1, latency_ms=lat)
    return g


def test_explanation_contains_real_costs_and_rejection_reasons():
    g = diamond(lat_top=5.0, lat_bottom=20.0)
    result = DijkstraRouter(g).explain_route("s1", "s4")
    assert result["status"] == "ROUTE_FOUND"
    assert result["selected_path"] == ["s1", "s2", "s4"]
    top, bottom = result["candidates"]
    assert top["selected"] and not bottom["selected"]
    # 2 hops * (0.4 * 5/100) vs 2 hops * (0.4 * 20/100)
    assert top["cost"] == pytest.approx(0.04)
    assert bottom["cost"] == pytest.approx(0.16)
    assert "0.1200 higher" in bottom["decision"] and "latency +0.1200" in bottom["decision"]
    assert result["weights"] == {"latency": 0.4, "utilization": 0.4, "packet_loss": 0.2, "capacity": 0.0}


def test_equal_cost_paths_are_reported_as_ties():
    result = DijkstraRouter(diamond()).explain_route("s1", "s4")
    assert result["candidates"][0]["cost"] == result["candidates"][1]["cost"]
    assert "equal composite cost" in result["candidates"][1]["decision"]


def test_changing_latency_changes_selection_and_explanation():
    g = diamond()
    router = DijkstraRouter(g)
    first = router.explain_route("s1", "s4")["selected_path"]
    g.graph["s1"]["s2"]["latency_ms"] = 50.0
    g.graph["s2"]["s1"]["latency_ms"] = 50.0
    second = router.explain_route("s1", "s4")
    assert first == ["s1", "s2", "s4"] and second["selected_path"] == ["s1", "s3", "s4"]
    assert "latency" in second["candidates"][1]["decision"]


def test_latency_beyond_normalisation_ceiling_still_differentiates():
    g = diamond(lat_top=500.0, lat_bottom=200.0)
    assert DijkstraRouter(g).calculate_shortest_path("s1", "s4")[0] == ["s1", "s3", "s4"]


def test_unreachable_destination_is_diagnosed_from_the_graph():
    g = diamond()
    for u, v in (("s1", "s2"), ("s2", "s1"), ("s1", "s3"), ("s3", "s1")):
        g.update_link_metrics(u, v, utilization_pct=0.0, is_active=False)
    result = DijkstraRouter(g).explain_route("s1", "s4")
    assert result["status"] == "NO_ROUTE" and result["selected_path"] is None
    assert "can only reach no other switch" in result["explanation"]
    assert {"src": "s1", "dst": "s2", "reason": "link is down or administratively disabled"} in result["excluded_links"]


def test_unknown_switch_is_reported():
    result = DijkstraRouter(diamond()).explain_route("s1", "s9")
    assert result["status"] == "NO_ROUTE" and "s9 does not exist" in result["explanation"]


def test_same_switch_needs_no_links():
    result = DijkstraRouter(diamond()).explain_route("s2", "s2")
    assert result["selected_path"] == ["s2"] and result["selected_cost"] == 0.0


def test_single_candidate_says_no_alternative():
    g = NetworkGraph()
    g.add_switch("a"); g.add_switch("b")
    g.add_link("a", "b", 1, 1)
    result = DijkstraRouter(g).explain_route("a", "b")
    assert len(result["candidates"]) == 1 and "No alternative path" in result["explanation"]


@pytest.mark.parametrize("field,value", [("latency_ms", -1.0), ("latency_ms", float("nan")),
                                         ("utilization_pct", 101.0), ("loss_pct", -5.0),
                                         ("loss_pct", float("inf"))])
def test_invalid_metrics_exclude_the_link(field, value):
    g = diamond()
    g.graph["s1"]["s2"][field] = value
    router = DijkstraRouter(g)
    assert router.calculate_shortest_path("s1", "s4")[0] == ["s1", "s3", "s4"]
    reasons = [x["reason"] for x in router.excluded_links() if (x["src"], x["dst"]) == ("s1", "s2")]
    assert reasons == ["link has invalid or missing metrics"]


def test_qos_weights_change_the_winner():
    g = diamond()
    # top path: low latency but busy; bottom: higher latency but idle
    for a, b in (("s1", "s2"), ("s2", "s4")):
        g.graph[a][b]["latency_ms"] = 5.0
        g.graph[a][b]["utilization_pct"] = 70.0
    for a, b in (("s1", "s3"), ("s3", "s4")):
        g.graph[a][b]["latency_ms"] = 15.0
    voice = DijkstraRouter(g, CostCalculator(alpha=0.7, beta=0.1, gamma=0.2))
    video = DijkstraRouter(g, CostCalculator(alpha=0.2, beta=0.6, gamma=0.2))
    assert voice.calculate_shortest_path("s1", "s4")[0] == ["s1", "s2", "s4"]
    assert video.calculate_shortest_path("s1", "s4")[0] == ["s1", "s3", "s4"]


def test_path_cost_and_first_unusable_hop():
    g = diamond()
    router = DijkstraRouter(g)
    assert router.path_cost(["s1", "s2", "s4"]) == pytest.approx(0.04)
    g.remove_link("s2", "s4")
    assert router.path_cost(["s1", "s2", "s4"]) is None
    assert router.first_unusable_hop(["s1", "s2", "s4"]) == "link s2-s4 was removed"
    g.remove_switch("s3")
    assert router.first_unusable_hop(["s1", "s3", "s4"]) == "switch s3 was removed"


def test_equal_cost_tie_break_is_independent_of_insertion_order():
    """The controller and backend build their graphs in different orders; they must
    still pick the same path among equal-cost routes."""
    def build(order):
        g = NetworkGraph()
        for sw in order:
            g.add_switch(sw)
        pairs = [("s1", "s2"), ("s2", "s5"), ("s5", "s7"), ("s1", "s3"), ("s3", "s6"), ("s6", "s7")]
        for u, v in (pairs if order[0] == "s1" else reversed(pairs)):
            g.add_link(u, v, 1, 1)
            g.add_link(v, u, 1, 1)
        return g
    a = DijkstraRouter(build(["s1", "s2", "s3", "s5", "s6", "s7"])).calculate_shortest_path("s1", "s7")[0]
    b = DijkstraRouter(build(["s7", "s6", "s5", "s3", "s2", "s1"])).calculate_shortest_path("s1", "s7")[0]
    assert a == b == ["s1", "s2", "s5", "s7"]
