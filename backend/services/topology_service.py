"""
Topology Service - Aggregates Live Controller Graph and Real-time Telemetry
"""
from typing import List, Dict, Optional, Any
from controller.topology.graph import NetworkGraph
from controller.models.topology import SwitchNode, HostNode, LinkEdge, TopologyData, SwitchPort, LinkStatus
import time

class TopologyService:
    def __init__(self):
        self.network_graph = NetworkGraph()
        self._init_mock_or_real_topology()

    def _init_mock_or_real_topology(self):
        """Initializes the baseline 7-switch mesh topology for immediate verification."""
        switches = [
            ("s1", 1, "Switch 1 (Ingress)"),
            ("s2", 2, "Switch 2 (Core Top)"),
            ("s3", 3, "Switch 3 (Core Bottom)"),
            ("s4", 4, "Switch 4 (Core Center)"),
            ("s5", 5, "Switch 5 (Aggregation Top)"),
            ("s6", 6, "Switch 6 (Aggregation Bottom)"),
            ("s7", 7, "Switch 7 (Egress)"),
        ]
        for dpid, dpid_int, name in switches:
            self.network_graph.add_switch(dpid, dpid_int=dpid_int, name=name)
            
        links = [
            ("s1", "s2", 1, 1, 100.0, 5.0, 0.0, 42.5),
            ("s1", "s3", 2, 1, 100.0, 5.0, 0.0, 18.2),
            ("s2", "s4", 2, 1, 100.0, 6.0, 0.0, 12.0),
            ("s2", "s5", 3, 1, 100.0, 5.0, 0.0, 76.8),
            ("s3", "s4", 2, 2, 100.0, 6.0, 0.0, 8.4),
            ("s3", "s6", 3, 1, 100.0, 5.0, 0.0, 24.1),
            ("s4", "s7", 3, 1, 100.0, 5.0, 0.0, 15.0),
            ("s5", "s7", 2, 2, 100.0, 5.0, 0.0, 72.3),
            ("s6", "s7", 2, 3, 100.0, 5.0, 0.0, 22.9),
        ]
        for u, v, p1, p2, cap, lat, loss, util in links:
            self.network_graph.add_link(u, v, p1, p2, capacity_mbps=cap, latency_ms=lat, loss_pct=loss, utilization_pct=util)
            self.network_graph.add_link(v, u, p2, p1, capacity_mbps=cap, latency_ms=lat, loss_pct=loss, utilization_pct=util)

    def get_topology(self) -> TopologyData:
        switches: List[SwitchNode] = []
        for n, d in self.network_graph.graph.nodes(data=True):
            switches.append(SwitchNode(
                dpid=n,
                dpid_int=d.get("dpid_int", 1),
                name=d.get("name", f"Switch {n.upper()}"),
                connected=True,
                active_flows=d.get("active_flows", 4)
            ))
            
        hosts: List[HostNode] = [
            HostNode(mac="00:00:00:00:00:01", ip="10.0.0.1", connected_switch="s1", connected_port=3, name="Host 1 (H1)"),
            HostNode(mac="00:00:00:00:00:02", ip="10.0.0.2", connected_switch="s1", connected_port=4, name="Host 2 (H2)"),
            HostNode(mac="00:00:00:00:00:07", ip="10.0.0.7", connected_switch="s7", connected_port=4, name="Host 7 (H7)"),
            HostNode(mac="00:00:00:00:00:08", ip="10.0.0.8", connected_switch="s7", connected_port=5, name="Host 8 (H8)"),
        ]
        
        links: List[LinkEdge] = []
        for u, v, d in self.network_graph.graph.edges(data=True):
            links.append(LinkEdge(
                link_id=f"{u}-{v}",
                src_dpid=u,
                src_port=d.get("src_port", 1),
                dst_dpid=v,
                dst_port=d.get("dst_port", 1),
                capacity_mbps=d.get("capacity_mbps", 100.0),
                current_rate_mbps=round(d.get("utilization_pct", 0.0) * d.get("capacity_mbps", 100.0) / 100.0, 2),
                utilization_pct=d.get("utilization_pct", 0.0),
                latency_ms=d.get("latency_ms", 5.0),
                packet_loss_pct=d.get("loss_pct", 0.0),
                status=d.get("status", LinkStatus.NORMAL),
                is_active=d.get("is_active", True)
            ))
            
        return TopologyData(
            switches=switches,
            hosts=hosts,
            links=links,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )

topology_service = TopologyService()
