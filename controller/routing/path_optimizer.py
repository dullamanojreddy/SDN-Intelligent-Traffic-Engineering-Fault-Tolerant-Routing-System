"""
Path Optimizer & Decision Evaluation
"""
from typing import Dict, List, Optional, Tuple, Any
from controller.routing.dijkstra import DijkstraRouter
from controller.models.event import RoutingDecision
import time

class PathOptimizer:
    def __init__(self, router: DijkstraRouter):
        self.router = router
        
    def evaluate_reroute(
        self,
        src_ip: str,
        dst_ip: str,
        src_dpid: str,
        dst_dpid: str,
        current_path: List[str],
        qos_class: str = "DEFAULT"
    ) -> Optional[RoutingDecision]:
        """
        Evaluates whether an active flow should be rerouted.
        Returns RoutingDecision if a meaningfully better path is available, else None.
        """
        k_paths = self.router.calculate_k_shortest_paths(src_dpid, dst_dpid, k=3)
        if not k_paths:
            return None
            
        optimal = k_paths[0]
        optimal_path = optimal["path"]
        optimal_cost = optimal["cost"]
        
        # If optimal path is identical to current path, no reroute needed
        if optimal_path == current_path:
            return None
            
        # Check current path cost
        current_cost = float("inf")
        for p_info in k_paths:
            if p_info["path"] == current_path:
                current_cost = p_info["cost"]
                break
                
        # Hysteresis: only reroute if the improvement is substantial (>15%) or current path is broken
        improvement = (current_cost - optimal_cost) / max(current_cost, 0.001)
        if current_cost == float("inf") or improvement > 0.15:
            decision = RoutingDecision(
                decision_id=f"dec_{int(time.time() * 1000)}",
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                source_ip=src_ip,
                dest_ip=dst_ip,
                old_path=current_path,
                new_path=optimal_path,
                reason=f"Path cost reduced from {current_cost:.2f} to {optimal_cost:.2f} (Improvement: {improvement*100:.1f}%)"
                       if current_cost != float("inf") else "Current path unavailable or severed",
                old_cost=round(current_cost, 4) if current_cost != float("inf") else 999.0,
                new_cost=round(optimal_cost, 4),
                latency_ms=optimal["latency_ms"],
                utilization_pct=optimal["max_utilization_pct"],
                packet_loss_pct=optimal["total_loss_pct"],
                qos_class=qos_class
            )
            return decision
            
        return None
