"""
Dijkstra Routing Engine & Path Computation
"""
import networkx as nx  # type: ignore
from typing import List, Dict, Optional, Tuple, Any
from controller.topology.graph import NetworkGraph
from controller.routing.cost_function import CostCalculator
from controller.utils.logger import log

class DijkstraRouter:
    def __init__(self, network_graph: NetworkGraph, cost_calculator: Optional[CostCalculator] = None):
        self.network_graph = network_graph
        self.cost_calculator = cost_calculator or CostCalculator()
        
    def get_weighted_graph(self) -> nx.DiGraph:
        """Constructs an active DiGraph with edge weights calculated via the cost function."""
        active_graph = self.network_graph.get_active_graph()
        weighted_graph = nx.DiGraph()
        
        # Build in sorted order so equal-cost ties resolve identically in every
        # process (controller and backend) regardless of discovery/insertion order.
        for n, d in sorted(active_graph.nodes(data=True), key=lambda item: str(item[0])):
            weighted_graph.add_node(n, **d)
            
        for u, v, d in sorted(active_graph.edges(data=True), key=lambda item: (str(item[0]), str(item[1]))):
            weight = self.cost_calculator.calculate_edge_cost(d)
            if weight < float("inf"):
                weighted_graph.add_edge(u, v, weight=weight, **d)
                
        return weighted_graph

    def calculate_shortest_path(self, src_dpid: str, dst_dpid: str) -> Tuple[Optional[List[str]], float]:
        """Calculates optimal path from src_dpid to dst_dpid."""
        if src_dpid == dst_dpid:
            return [src_dpid], 0.0
            
        G = self.get_weighted_graph()
        if not G.has_node(src_dpid) or not G.has_node(dst_dpid):
            log.warning(f"Dijkstra: Node missing in active topology: {src_dpid} or {dst_dpid}")
            return None, float("inf")
            
        try:
            raw_path = nx.dijkstra_path(G, source=src_dpid, target=dst_dpid, weight="weight")
            path: List[str] = [str(n) for n in raw_path]
            cost: float = nx.dijkstra_path_length(G, source=src_dpid, target=dst_dpid, weight="weight")
            return path, cost
        except nx.NetworkXNoPath:
            log.error(f"Dijkstra: No viable path from {src_dpid} to {dst_dpid}")
            return None, float("inf")

    def calculate_k_shortest_paths(self, src_dpid: str, dst_dpid: str, k: int = 3) -> List[Dict[str, Any]]:
        """Calculates up to K alternate candidate paths."""
        G = self.get_weighted_graph()
        if not G.has_node(src_dpid) or not G.has_node(dst_dpid):
            return []
            
        results = []
        try:
            paths = list(nx.shortest_simple_paths(G, source=src_dpid, target=dst_dpid, weight="weight"))
            for p in paths[:k]:
                path_nodes: List[str] = [str(n) for n in p]
                # Calculate metrics for path
                cost = 0.0
                total_latency = 0.0
                max_util = 0.0
                total_loss = 0.0
                cost_breakdown = {"latency": 0.0, "utilization": 0.0, "packet_loss": 0.0, "capacity": 0.0, "congestion_penalty": 0.0}
                edge_metrics = []
                for i in range(len(path_nodes) - 1):
                    u, v = path_nodes[i], path_nodes[i+1]
                    edge = G[u][v]
                    cost += edge.get("weight", 0.0)
                    total_latency += edge.get("latency_ms", 5.0)
                    max_util = max(max_util, edge.get("utilization_pct", 0.0))
                    total_loss += max(edge.get("loss_pct", 0.0), edge.get("measured_loss_pct", 0.0))
                    explanation = self.cost_calculator.explain_edge_cost(edge)
                    if explanation["valid"]:
                        for key, value in explanation["components"].items():
                            cost_breakdown[key] += value
                        edge_metrics.append({
                            "src": u,
                            "dst": v,
                            **explanation["metrics"],
                            "capacity_mbps": edge.get("capacity_mbps"),
                            "cost": explanation["cost"],
                        })
                    
                results.append({
                    "path": path_nodes,
                    "cost": round(cost, 4),
                    "latency_ms": round(total_latency, 2),
                    "max_utilization_pct": round(max_util, 2),
                    "total_loss_pct": round(total_loss, 2),
                    "cost_breakdown": {
                        key: round(value, 4) for key, value in cost_breakdown.items()
                    },
                    "edge_metrics": edge_metrics,
                })
        except (nx.NetworkXNoPath, nx.NetworkXError):
            pass
        return results

    def excluded_links(self) -> List[Dict[str, Any]]:
        """Directed links the router cannot use, with the reason for each."""
        excluded = []
        for u, v, d in self.network_graph.graph.edges(data=True):
            if not d.get("is_active", True):
                reason = "link is down or administratively disabled"
            elif self.cost_calculator.require_confirmed and d.get("data_plane_confirmed", True) is False:
                reason = "link is not confirmed in the data plane (model-only), so it cannot carry real traffic"
            elif self.cost_calculator.normalized_metrics(d) is None:
                reason = "link has invalid or missing metrics"
            else:
                continue
            excluded.append({"src": u, "dst": v, "reason": reason})
        return excluded

    def diagnose_unreachable(self, src_dpid: str, dst_dpid: str) -> str:
        """Explain, from the actual graph, why dst cannot be reached from src."""
        graph = self.network_graph.graph
        for name in (src_dpid, dst_dpid):
            if not graph.has_node(name):
                return f"Switch {name} does not exist in the topology."
        weighted = self.get_weighted_graph()
        reachable = sorted(nx.descendants(weighted, src_dpid))
        down = [f"{x['src']}-{x['dst']}" for x in self.excluded_links()]
        reach_txt = ", ".join(reachable) if reachable else "no other switch"
        text = (
            f"No usable path from {src_dpid} to {dst_dpid}: over active links "
            f"{src_dpid} can only reach {reach_txt}."
        )
        if down:
            text += f" Unusable links: {', '.join(down)}."
        return text

    @staticmethod
    def _describe_cost_gap(candidate: Dict[str, Any], selected: Dict[str, Any]) -> str:
        """Break a cost difference down by metric component."""
        names = {
            "latency": "latency", "utilization": "utilization",
            "packet_loss": "packet loss", "capacity": "link capacity", "congestion_penalty": "congestion penalty",
        }
        parts = []
        for key, label in names.items():
            gap = candidate["cost_breakdown"].get(key, 0.0) - selected["cost_breakdown"].get(key, 0.0)
            if abs(gap) >= 0.0001:
                parts.append(f"{label} {'+' if gap > 0 else ''}{gap:.4f}")
        return ", ".join(parts) if parts else "no per-metric difference"

    def explain_route(self, src_dpid: str, dst_dpid: str, k: int = 3) -> Dict[str, Any]:
        calc = self.cost_calculator
        base = {
            "weights": {"latency": calc.alpha, "utilization": calc.beta, "packet_loss": calc.gamma, "capacity": calc.delta},
            "formula": ("cost(link) = a*latency/%.0fms + b*utilization/100 + g*loss/100 + d*(1 - min(capacity,%.0fMbps)/%.0fMbps) "
                        "+ congestion penalty above 85%%" % (calc.max_latency_ms, calc.reference_capacity_mbps, calc.reference_capacity_mbps)),
            "excluded_links": self.excluded_links(),
        }
        if src_dpid == dst_dpid and self.network_graph.graph.has_node(src_dpid):
            return {
                **base,
                "status": "ROUTE_FOUND",
                "selected_path": [src_dpid],
                "selected_cost": 0.0,
                "candidates": [{
                    "path": [src_dpid], "cost": 0.0, "latency_ms": 0.0,
                    "max_utilization_pct": 0.0, "total_loss_pct": 0.0, "hops": 0,
                    "cost_breakdown": {"latency": 0.0, "utilization": 0.0, "packet_loss": 0.0, "capacity": 0.0, "congestion_penalty": 0.0},
                    "edge_metrics": [], "rank": 1, "selected": True,
                    "decision": "Selected: source and destination share switch " + src_dpid + ".",
                }],
                "explanation": f"Source and destination attach to the same switch {src_dpid}; no inter-switch link is needed.",
            }
        candidates = self.calculate_k_shortest_paths(src_dpid, dst_dpid, k=k)
        if not candidates:
            return {
                **base,
                "status": "NO_ROUTE",
                "selected_path": None,
                "selected_cost": None,
                "candidates": [],
                "explanation": self.diagnose_unreachable(src_dpid, dst_dpid),
            }
        selected = candidates[0]
        for index, candidate in enumerate(candidates):
            candidate["rank"] = index + 1
            candidate["selected"] = index == 0
            candidate["hops"] = len(candidate["path"]) - 1
            if index == 0:
                candidate["decision"] = "Selected: lowest measured composite cost."
                continue
            gap = candidate["cost"] - selected["cost"]
            if abs(gap) < 1e-9:
                candidate["decision"] = (
                    "Rejected: equal composite cost to the selected path; the deterministic "
                    "tie-break (lexicographic switch order) picked the other path."
                )
            else:
                candidate["decision"] = (
                    f"Rejected: composite cost is {gap:.4f} higher than the selected path "
                    f"({self._describe_cost_gap(candidate, selected)})."
                )
        text = (
            f"Selected {' -> '.join(selected['path'])} because it has the lowest "
            f"measured composite cost ({selected['cost']:.4f}) among {len(candidates)} "
            f"reachable candidate{'s' if len(candidates) != 1 else ''}."
        )
        if len(candidates) == 1:
            text += " No alternative path exists over the currently usable links."
        if base["excluded_links"]:
            text += " Excluded links: " + ", ".join(
                f"{x['src']}-{x['dst']}" for x in base["excluded_links"]) + "."
        return {
            **base,
            "status": "ROUTE_FOUND",
            "selected_path": selected["path"],
            "selected_cost": selected["cost"],
            "candidates": candidates,
            "explanation": text,
        }

    def path_cost(self, path: List[str]) -> Optional[float]:
        """Current composite cost of a specific path, or None if any hop is unusable."""
        if not path:
            return None
        weighted = self.get_weighted_graph()
        total = 0.0
        for u, v in zip(path, path[1:]):
            if not weighted.has_edge(u, v):
                return None
            total += weighted[u][v]["weight"]
        return round(total, 4)

    def first_unusable_hop(self, path: List[str]) -> Optional[str]:
        """Describe the first hop of a path that no longer exists or is down."""
        graph = self.network_graph.graph
        for node in path:
            if not graph.has_node(node):
                return f"switch {node} was removed"
        for u, v in zip(path, path[1:]):
            if not graph.has_edge(u, v):
                return f"link {u}-{v} was removed"
            if not graph[u][v].get("is_active", True):
                return f"link {u}-{v} is down"
            if self.cost_calculator.normalized_metrics(graph[u][v]) is None:
                return f"link {u}-{v} has invalid metrics"
        return None
