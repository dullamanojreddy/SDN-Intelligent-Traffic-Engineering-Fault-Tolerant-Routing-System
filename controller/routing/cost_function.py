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
        max_latency_ms: float = 100.0,
        delta: float = settings.capacity_weight,
        reference_capacity_mbps: float = settings.reference_capacity_mbps,
        require_confirmed: bool = not settings.route_over_unconfirmed_links,
        noise_floor_pct: float = settings.utilization_noise_floor_pct,
    ):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.max_latency_ms = max_latency_ms
        self.delta = delta                      # weight of the capacity term (0 disables it)
        self.reference_capacity_mbps = reference_capacity_mbps
        # Links nobody has seen in the data plane must not carry real traffic.
        self.require_confirmed = require_confirmed
        # Control-plane chatter (LLDP, echoes) shows up as ~0.0002% utilization; without a
        # floor it breaks ties between equal paths and makes routes flap.
        self.noise_floor_pct = noise_floor_pct
        
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
            + self.delta * metrics["capacity"]
            + congestion_penalty
        )
        return max(cost, 0.001)  # Ensure positive non-zero cost for Dijkstra

    def normalized_metrics(self, edge_data: Dict[str, Any]) -> Dict[str, float] | None:
        """Return measured, finite metrics or None when an edge cannot be evaluated."""
        if not edge_data.get("is_active", True):
            return None
        if self.require_confirmed and edge_data.get("data_plane_confirmed", True) is False:
            return None
        try:
            latency_ms = float(edge_data["latency_ms"])
            utilization_pct = float(edge_data["utilization_pct"])
            # Configured loss (operator/netem) and measured drops both count; use the worse.
            configured_loss = float(edge_data["loss_pct"])
            measured_loss = float(edge_data.get("measured_loss_pct", 0.0))
            loss_pct = max(configured_loss, measured_loss)
            capacity_mbps = float(edge_data.get("capacity_mbps", self.reference_capacity_mbps))
        except (KeyError, TypeError, ValueError):
            return None
        if not all(math.isfinite(value) for value in (latency_ms, utilization_pct, configured_loss, measured_loss, capacity_mbps)):
            return None
        if capacity_mbps <= 0:
            return None
        if utilization_pct < self.noise_floor_pct:
            utilization_pct = 0.0
        if latency_ms < 0 or not 0 <= utilization_pct <= 100 or not 0 <= configured_loss <= 100 or not 0 <= measured_loss <= 100:
            return None
        return {
            "latency": latency_ms / self.max_latency_ms,
            "utilization": utilization_pct / 100.0,
            "packet_loss": loss_pct / 100.0,
            # 0 for links at/above the reference capacity, approaching 1 for very thin links
            "capacity": 1.0 - min(capacity_mbps, self.reference_capacity_mbps) / self.reference_capacity_mbps,
            "capacity_mbps": capacity_mbps,
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
            "capacity": self.delta * metrics["capacity"],
            "congestion_penalty": congestion_penalty,
        }
        return {
            "valid": True,
            "metrics": {key: round(value, 4) for key, value in metrics.items()},
            "components": {key: round(value, 4) for key, value in components.items()},
            "cost": round(sum(components.values()), 4),
        }
