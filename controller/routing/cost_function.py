"""
Normalized Multi-Metric Cost Function for Traffic Engineering
"""
from typing import Dict, Any
import math
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
            
        metrics = self.normalized_metrics(edge_data)
        if metrics is None:
            return float("inf")
        latency, utilization, loss = (
            metrics["latency"],
            metrics["utilization"],
            metrics["packet_loss"],
        )
        
        # Normalization to [0, 1] range
        # Exponential penalty for heavily saturated links (>85%)
        congestion_penalty = 0.0
        if metrics["utilization_pct"] > 85.0:
            congestion_penalty = ((metrics["utilization_pct"] - 85.0) / 15.0) ** 2 * 2.0
            
        cost = (
            self.alpha * latency
            + self.beta * utilization
            + self.gamma * loss
            + congestion_penalty
        )
        return max(cost, 0.001)  # Ensure positive non-zero cost for Dijkstra

    def normalized_metrics(self, edge_data: Dict[str, Any]) -> Dict[str, float] | None:
        """Return measured, finite metrics or None when an edge cannot be evaluated."""
        if not edge_data.get("is_active", True):
            return None
        try:
            latency_ms = float(edge_data["latency_ms"])
            utilization_pct = float(edge_data["utilization_pct"])
            loss_pct = float(edge_data["loss_pct"])
        except (KeyError, TypeError, ValueError):
            return None
        if not all(math.isfinite(value) for value in (latency_ms, utilization_pct, loss_pct)):
            return None
        if latency_ms < 0 or not 0 <= utilization_pct <= 100 or not 0 <= loss_pct <= 100:
            return None
        return {
            "latency": min(latency_ms / self.max_latency_ms, 1.0),
            "utilization": utilization_pct / 100.0,
            "packet_loss": loss_pct / 100.0,
            "latency_ms": latency_ms,
            "utilization_pct": utilization_pct,
            "packet_loss_pct": loss_pct,
        }

    def explain_edge_cost(self, edge_data: Dict[str, Any]) -> Dict[str, Any]:
        metrics = self.normalized_metrics(edge_data)
        if metrics is None:
            return {"valid": False, "reason": "Link is failed, unavailable, or has invalid metrics"}
        congestion_penalty = (
            ((metrics["utilization_pct"] - 85.0) / 15.0) ** 2 * 2.0
            if metrics["utilization_pct"] > 85.0 else 0.0
        )
        components = {
            "latency": self.alpha * metrics["latency"],
            "utilization": self.beta * metrics["utilization"],
            "packet_loss": self.gamma * metrics["packet_loss"],
            "congestion_penalty": congestion_penalty,
        }
        return {
            "valid": True,
            "metrics": {key: round(value, 4) for key, value in metrics.items()},
            "components": {key: round(value, 4) for key, value in components.items()},
            "cost": round(sum(components.values()), 4),
        }
