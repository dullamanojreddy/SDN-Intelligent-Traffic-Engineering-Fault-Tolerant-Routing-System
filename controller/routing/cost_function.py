"""
Normalized Multi-Metric Cost Function for Traffic Engineering
"""
from typing import Dict, Any
from controller.config.settings import settings

class CostCalculator:
    def __init__(
        self,
        alpha: float = settings.latency_weight,
        beta: float = settings.utilization_weight,
        gamma: float = settings.loss_weight,
        max_latency_ms: float = 100.0
    ):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.max_latency_ms = max_latency_ms
        
    def calculate_edge_cost(self, edge_data: Dict[str, Any]) -> float:
        """
        Computes composite cost:
        Cost = alpha * norm_latency + beta * norm_utilization + gamma * norm_loss
        """
        if not edge_data.get("is_active", True):
            return float("inf")
            
        latency = float(edge_data.get("latency_ms", 5.0))
        utilization = float(edge_data.get("utilization_pct", 0.0))
        loss = float(edge_data.get("loss_pct", 0.0))
        
        # Normalization to [0, 1] range
        norm_latency = min(latency / self.max_latency_ms, 1.0)
        norm_utilization = min(utilization / 100.0, 1.0)
        norm_loss = min(loss / 100.0, 1.0)
        
        # Exponential penalty for heavily saturated links (>85%)
        congestion_penalty = 0.0
        if utilization > 85.0:
            congestion_penalty = ((utilization - 85.0) / 15.0) ** 2 * 2.0
            
        cost = (
            self.alpha * norm_latency
            + self.beta * norm_utilization
            + self.gamma * norm_loss
            + congestion_penalty
        )
        return max(cost, 0.001)  # Ensure positive non-zero cost for Dijkstra
