"""
Link and Switch Failure Detector & Recovery Engine
"""
import time
from typing import Dict, List, Optional, Tuple, Any
from controller.models.event import NetworkEvent, EventType, AlertSeverity
from controller.topology.graph import NetworkGraph
from controller.routing.dijkstra import DijkstraRouter
from controller.utils.logger import log

class FailureDetector:
    def __init__(self, network_graph: NetworkGraph):
        self.network_graph = network_graph
        
    def handle_port_down(self, dpid: str, port_no: int) -> List[NetworkEvent]:
        """Handles an OFPPortStatus down event."""
        events = []
        now = time.time()
        
        # Locate corresponding link in graph
        edges_to_fail = []
        for u, v, d in self.network_graph.graph.edges(data=True):
            if (u == dpid and d.get("src_port") == port_no) or (v == dpid and d.get("dst_port") == port_no):
                edges_to_fail.append((u, v))
                
        for u, v in edges_to_fail:
            self.network_graph.update_link_metrics(u, v, utilization_pct=0.0, is_active=False)
            link_id = f"{u}-{v}"
            log.error(f"FAILURE DETECTED: Link {link_id} down (Switch {dpid} Port {port_no})")
            
            event = NetworkEvent(
                event_id=f"ev_fail_{int(now * 1000)}",
                type=EventType.LINK_FAILURE,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                source=f"PortStatus {dpid}:{port_no}",
                message=f"Link {link_id} severed. Topology graph updated.",
                severity=AlertSeverity.CRITICAL,
                data={"dpid": dpid, "port_no": port_no, "link_id": link_id}
            )
            events.append(event)
            
        return events

class RecoveryEngine:
    def __init__(self, router: DijkstraRouter):
        self.router = router
        
    def compute_failover_path(
        self,
        src_dpid: str,
        dst_dpid: str,
        failed_link_id: str
    ) -> Tuple[Optional[List[str]], float, float]:
        """
        Computes a resilient alternate path avoiding the failed link.
        Returns: (new_path, new_cost, recovery_duration_ms)
        """
        start_time = time.time()
        new_path, cost = self.router.calculate_shortest_path(src_dpid, dst_dpid)
        recovery_duration_ms = (time.time() - start_time) * 1000.0
        
        return new_path, cost, recovery_duration_ms
