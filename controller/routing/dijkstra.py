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
        
        for n, d in active_graph.nodes(data=True):
            weighted_graph.add_node(n, **d)
            
        for u, v, d in active_graph.edges(data=True):
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
                for i in range(len(path_nodes) - 1):
                    u, v = path_nodes[i], path_nodes[i+1]
                    edge = G[u][v]
                    cost += edge.get("weight", 0.0)
                    total_latency += edge.get("latency_ms", 5.0)
                    max_util = max(max_util, edge.get("utilization_pct", 0.0))
                    total_loss += edge.get("loss_pct", 0.0)
                    
                results.append({
                    "path": path_nodes,
                    "cost": round(cost, 4),
                    "latency_ms": round(total_latency, 2),
                    "max_utilization_pct": round(max_util, 2),
                    "total_loss_pct": round(total_loss, 2)
                })
        except (nx.NetworkXNoPath, nx.NetworkXError):
            pass
        return results
