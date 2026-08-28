"""
Network Graph abstraction using NetworkX
"""
import networkx as nx  # type: ignore
from typing import Dict, List, Optional, Tuple, Any
from controller.models.topology import LinkStatus

class NetworkGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.hosts: Dict[str, Dict[str, Any]] = {}
        
    def add_switch(self, dpid: str, **attrs):
        self.graph.add_node(dpid, node_type="switch", **attrs)
        
    def remove_switch(self, dpid: str):
        if self.graph.has_node(dpid):
            self.graph.remove_node(dpid)

    def add_host(self, host_id: str, switch_dpid: str, port_no: int, ip: str, mac: str):
        """Registers a discovered host node."""
        self.hosts[host_id] = {
            "host_id": host_id,
            "switch": switch_dpid,
            "port": port_no,
            "ip": ip,
            "mac": mac,
        }
            
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

    def update_link_utilization(self, src_dpid: str, dst_dpid: str, utilization_pct: float):
        self.update_link_metrics(src_dpid, dst_dpid, utilization_pct=utilization_pct)

    def update_link_packet_loss(self, src_dpid: str, dst_dpid: str, loss_pct: float):
        if self.graph.has_edge(src_dpid, dst_dpid):
            curr_util = self.graph[src_dpid][dst_dpid].get("utilization_pct", 0.0)
            self.update_link_metrics(src_dpid, dst_dpid, utilization_pct=curr_util, loss_pct=loss_pct)

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

    def get_link_ports(self, src_dpid: str, dst_dpid: str) -> Optional[Tuple[int, int]]:
        """Returns (src_port, dst_port) for a directed edge between two switches."""
        if self.graph.has_edge(src_dpid, dst_dpid):
            edge = self.graph[src_dpid][dst_dpid]
            return (edge.get("src_port", 1), edge.get("dst_port", 1))
        return None

    def get_link_output_port(self, src_dpid: str, dst_dpid: str) -> Optional[int]:
        """Returns the output port on src_dpid that connects to dst_dpid."""
        ports = self.get_link_ports(src_dpid, dst_dpid)
        return ports[0] if ports else None

    def get_link_input_port(self, src_dpid: str, dst_dpid: str) -> Optional[int]:
        """Returns the input port on dst_dpid that connects from src_dpid."""
        ports = self.get_link_ports(src_dpid, dst_dpid)
        return ports[1] if ports else None
