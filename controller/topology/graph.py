"""
Network Graph abstraction using NetworkX
"""
import networkx as nx
from typing import Dict, List, Optional, Tuple, Any
from controller.models.topology import LinkStatus

class NetworkGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        
    def add_switch(self, dpid: str, **attrs):
        self.graph.add_node(dpid, node_type="switch", **attrs)
        
    def remove_switch(self, dpid: str):
        if self.graph.has_node(dpid):
            self.graph.remove_node(dpid)
            
    def add_link(
        self,
        src_dpid: str,
        dst_dpid: str,
        src_port: int,
        dst_port: int,
        capacity_mbps: float = 100.0,
        latency_ms: float = 5.0,
        loss_pct: float = 0.0,
        utilization_pct: float = 0.0,
        is_active: bool = True
    ):
        self.graph.add_edge(
            src_dpid,
            dst_dpid,
            src_port=src_port,
            dst_port=dst_port,
            capacity_mbps=capacity_mbps,
            latency_ms=latency_ms,
            loss_pct=loss_pct,
            utilization_pct=utilization_pct,
            is_active=is_active,
            status=LinkStatus.NORMAL if is_active else LinkStatus.FAILED
        )
        
    def remove_link(self, src_dpid: str, dst_dpid: str):
        if self.graph.has_edge(src_dpid, dst_dpid):
            self.graph.remove_edge(src_dpid, dst_dpid)
            
    def update_link_metrics(
        self,
        src_dpid: str,
        dst_dpid: str,
        utilization_pct: float,
        latency_ms: Optional[float] = None,
        loss_pct: Optional[float] = None,
        is_active: Optional[bool] = None
    ):
        if self.graph.has_edge(src_dpid, dst_dpid):
            edge = self.graph[src_dpid][dst_dpid]
            edge["utilization_pct"] = utilization_pct
            if latency_ms is not None:
                edge["latency_ms"] = latency_ms
            if loss_pct is not None:
                edge["loss_pct"] = loss_pct
            if is_active is not None:
                edge["is_active"] = is_active
                
            # Update status categorization
            if not edge.get("is_active", True):
                edge["status"] = LinkStatus.FAILED
            elif utilization_pct >= 90.0:
                edge["status"] = LinkStatus.CRITICAL
            elif utilization_pct >= 80.0:
                edge["status"] = LinkStatus.HIGH
            elif utilization_pct >= 60.0:
                edge["status"] = LinkStatus.MODERATE
            else:
                edge["status"] = LinkStatus.NORMAL

    def get_active_graph(self) -> nx.DiGraph:
        """Returns a subgraph containing only active, operational links."""
        active_edges = [
            (u, v, k) for u, v, k in self.graph.edges(data=True)
            if k.get("is_active", True)
        ]
        sub = nx.DiGraph()
        for n, d in self.graph.nodes(data=True):
            sub.add_node(n, **d)
        for u, v, d in active_edges:
            sub.add_edge(u, v, **d)
        return sub
