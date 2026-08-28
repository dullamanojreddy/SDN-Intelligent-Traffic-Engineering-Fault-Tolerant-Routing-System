"""
Controller Configuration & Settings
"""
from pydantic import BaseModel, Field
import os

class ControllerSettings(BaseModel):
    # Network & OF
    of_port: int = Field(default=6653, description="OpenFlow listen port")
    rest_port: int = Field(default=8080, description="Controller REST API port")
    
    # Traffic Monitoring
    monitor_interval: float = Field(default=2.0, description="Monitoring loop cycle in seconds")
    
    # Congestion Detection
    utilization_threshold_pct: float = Field(default=85.0, description="Utilization percentage threshold for congestion")
    congestion_persistence_cycles: int = Field(default=3, description="Number of consecutive cycles required to confirm congestion")
    congestion_cooldown_sec: float = Field(default=10.0, description="Cooldown seconds before rerouting again to prevent flapping")
    
    # Multi-metric Routing Cost Weights (must sum to 1.0)
    latency_weight: float = Field(default=0.4, description="Weight alpha for normalized latency")
    utilization_weight: float = Field(default=0.4, description="Weight beta for normalized utilization")
    loss_weight: float = Field(default=0.2, description="Weight gamma for normalized packet loss")
    
    # QoS Profiles (latency_weight, utilization_weight, loss_weight)
    qos_profiles: dict = Field(
        default={
            "VOICE": {"latency": 0.7, "utilization": 0.1, "loss": 0.2, "priority": 50},
            "VIDEO": {"latency": 0.2, "utilization": 0.6, "loss": 0.2, "priority": 40},
            "WEB": {"latency": 0.4, "utilization": 0.4, "loss": 0.2, "priority": 30},
            "BACKGROUND": {"latency": 0.1, "utilization": 0.8, "loss": 0.1, "priority": 20},
        }
    )

settings = ControllerSettings(
    monitor_interval=float(os.getenv("MONITOR_INTERVAL_SEC", 2.0)),
    utilization_threshold_pct=float(os.getenv("UTILIZATION_THRESHOLD_PCT", 85.0)),
    congestion_persistence_cycles=int(os.getenv("CONGESTION_PERSISTENCE_CYCLES", 3)),
    congestion_cooldown_sec=float(os.getenv("CONGESTION_COOLDOWN_SEC", 10.0)),
    latency_weight=float(os.getenv("LATENCY_WEIGHT", 0.4)),
    utilization_weight=float(os.getenv("UTILIZATION_WEIGHT", 0.4)),
    loss_weight=float(os.getenv("LOSS_WEIGHT", 0.2)),
)
