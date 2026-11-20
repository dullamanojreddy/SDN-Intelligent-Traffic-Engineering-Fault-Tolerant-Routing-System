"""
Topology Service - Aggregates Live Controller Graph and Real-time Telemetry
"""
from typing import List, Dict, Optional, Any
import re
import threading
from controller.topology.graph import NetworkGraph
from controller.models.topology import SwitchNode, HostNode, LinkEdge, TopologyData, SwitchPort, LinkStatus
from controller.topology.state_bridge import get_link_states
import time

class TopologyService:
    def __init__(self):
        self.network_graph = NetworkGraph()
        self.hosts: Dict[str, HostNode] = {}
        self._lock = threading.RLock()
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
            
        self.hosts = {
            host.name.lower(): host for host in [
            HostNode(mac="00:00:00:00:00:01", ip="10.0.0.1", connected_switch="s1", connected_port=3, name="Host 1 (H1)"),
            HostNode(mac="00:00:00:00:00:02", ip="10.0.0.2", connected_switch="s1", connected_port=4, name="Host 2 (H2)"),
            HostNode(mac="00:00:00:00:00:07", ip="10.0.0.7", connected_switch="s7", connected_port=4, name="Host 7 (H7)"),
            HostNode(mac="00:00:00:00:00:08", ip="10.0.0.8", connected_switch="s7", connected_port=5, name="Host 8 (H8)"),
            ]
        }
        
        controller_states = get_link_states()
        links: List[LinkEdge] = []
        for u, v, d in self.network_graph.graph.edges(data=True):
            link_id = f"{u}-{v}"
            is_active = controller_states.get(link_id, d.get("is_active", True))
            status = LinkStatus.FAILED if not is_active else d.get("status", LinkStatus.NORMAL)
            links.append(LinkEdge(
                link_id=link_id,
                src_dpid=u,
                src_port=d.get("src_port", 1),
                dst_dpid=v,
                dst_port=d.get("dst_port", 1),
                capacity_mbps=d.get("capacity_mbps", 100.0),
                current_rate_mbps=round(d.get("utilization_pct", 0.0) * d.get("capacity_mbps", 100.0) / 100.0, 2),
                utilization_pct=d.get("utilization_pct", 0.0),
                latency_ms=d.get("latency_ms", 5.0),
                packet_loss_pct=d.get("loss_pct", 0.0),
                status=status,
                is_active=is_active
            ))
            
        return TopologyData(
            switches=switches,
            hosts=list(self.hosts.values()),
            links=links,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )

    @staticmethod
    def _normalise_name(name: str) -> str:
        return name.strip().lower()

    def add_switch(self, name: str) -> SwitchNode:
        with self._lock:
            node_id = self._normalise_name(name)
            if not re.fullmatch(r"[a-z][a-z0-9_-]*", node_id):
                raise ValueError("Switch name must start with a letter and contain only letters, numbers, _ or -")
            if self.network_graph.graph.has_node(node_id):
                raise ValueError(f"Switch already exists: {name}")
            numeric_ids = [
                data.get("dpid_int", 0)
                for _, data in self.network_graph.graph.nodes(data=True)
            ]
            dpid_int = max(numeric_ids, default=0) + 1
            self.network_graph.add_switch(
                node_id, dpid_int=dpid_int, name=name.strip(), active_flows=0
            )
            return self.get_topology().switches[-1]

    def remove_switch(self, name: str) -> None:
        with self._lock:
            node_id = self._normalise_name(name)
            if not self.network_graph.graph.has_node(node_id):
                raise KeyError(f"Switch not found: {name}")
            self.network_graph.remove_switch(node_id)
            for host_id in [
                host_id for host_id, host in self.hosts.items()
                if host.connected_switch == node_id
            ]:
                del self.hosts[host_id]

    def add_host(self, name: str, ip: str, switch: str, mac: Optional[str] = None) -> HostNode:
        with self._lock:
            host_id = self._normalise_name(name)
            switch_id = self._normalise_name(switch)
            if host_id in self.hosts:
                raise ValueError(f"Host already exists: {name}")
            if not self.network_graph.graph.has_node(switch_id):
                raise KeyError(f"Switch not found: {switch}")
            if any(host.ip == ip for host in self.hosts.values()):
                raise ValueError(f"IP address already exists: {ip}")
            port = max(
                [edge.get("src_port", 0) for _, _, edge in self.network_graph.graph.edges(switch_id, data=True)]
                + [host.connected_port for host in self.hosts.values() if host.connected_switch == switch_id]
                + [0]
            ) + 1
            host = HostNode(
                mac=mac or f"02:00:00:00:{len(self.hosts) // 256:02x}:{len(self.hosts) % 256:02x}",
                ip=ip,
                connected_switch=switch_id,
                connected_port=port,
                name=name.strip(),
            )
            self.hosts[host_id] = host
            return host

    def remove_host(self, name: str) -> None:
        with self._lock:
            host_id = self._normalise_name(name)
            if host_id not in self.hosts:
                raise KeyError(f"Host not found: {name}")
            del self.hosts[host_id]

    def add_connection(self, src: str, dst: str, capacity_mbps: float, latency_ms: float) -> None:
        with self._lock:
            src_id, dst_id = self._normalise_name(src), self._normalise_name(dst)
            if src_id == dst_id:
                raise ValueError("A node cannot connect to itself")
            if not self.network_graph.graph.has_node(src_id) or not self.network_graph.graph.has_node(dst_id):
                raise KeyError("Both endpoints must be existing switches")
            if self.network_graph.graph.has_edge(src_id, dst_id):
                raise ValueError(f"Connection already exists: {src}-{dst}")
            src_port = self._next_switch_port(src_id)
            dst_port = self._next_switch_port(dst_id)
            self.network_graph.add_link(src_id, dst_id, src_port, dst_port, capacity_mbps, latency_ms)
            self.network_graph.add_link(dst_id, src_id, dst_port, src_port, capacity_mbps, latency_ms)

    def remove_connection(self, src: str, dst: str) -> None:
        with self._lock:
            src_id, dst_id = self._normalise_name(src), self._normalise_name(dst)
            if not self.network_graph.graph.has_edge(src_id, dst_id):
                raise KeyError(f"Connection not found: {src}-{dst}")
            self.network_graph.remove_link(src_id, dst_id)
            self.network_graph.remove_link(dst_id, src_id)

    def _next_switch_port(self, switch: str) -> int:
        ports = [
            data.get("src_port", 0)
            for _, _, data in self.network_graph.graph.out_edges(switch, data=True)
        ]
        ports.extend(
            host.connected_port
            for host in self.hosts.values()
            if host.connected_switch == switch
        )
        return max(ports, default=0) + 1

topology_service = TopologyService()
