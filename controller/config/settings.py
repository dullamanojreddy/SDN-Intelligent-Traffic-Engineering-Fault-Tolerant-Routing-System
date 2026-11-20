"""
Controller Configuration & Settings
"""
from pydantic import BaseModel, Field
import os

class ControllerSettings(BaseModel):
    # Network & OF
    of_port: int = Field(default=6653, description="OpenFlow listen port")
    rest_port: int = Field(default=8080, description="Controller REST API port")
    api_token: str = Field(default="", description="Token for controller management API")
    controller_id: str = Field(default="primary", description="Name reported by this controller instance")
    preferred: bool = Field(default=True, description="Preferred (primary) controller takes mastership back after recovery")
    peer_api_url: str = Field(default="", description="Management API of the peer controller used for HA supervision")
    ha_interval_sec: float = Field(default=1.0, description="Peer heartbeat interval")
    ha_failure_threshold: int = Field(default=3, description="Missed peer heartbeats before a slave promotes itself")
    ha_recovery_threshold: int = Field(default=3, description="Healthy peer heartbeats before a standby yields mastership")
    route_over_unconfirmed_links: bool = Field(default=False, description="Allow routing over links never confirmed in the data plane (unsafe)")
    reference_capacity_mbps: float = Field(default=100.0, description="Capacity at/above which a link has no capacity penalty")
    capacity_weight: float = Field(default=0.0, description="Default weight of the capacity term in the link cost")
    utilization_noise_floor_pct: float = Field(default=1.0, description="Utilization below this is measurement noise (LLDP/echo traffic) and costs nothing")
    seed_mesh: bool = Field(default=True, description="Pre-seed the demo 7-switch mesh until a topology snapshot arrives")
    
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
            "VOICE": {"latency": 0.7, "utilization": 0.1, "loss": 0.2, "capacity": 0.0, "priority": 50},
            "VIDEO": {"latency": 0.2, "utilization": 0.6, "loss": 0.2, "capacity": 0.15, "priority": 40},
            "WEB": {"latency": 0.4, "utilization": 0.4, "loss": 0.2, "capacity": 0.0, "priority": 30},
            "BACKGROUND": {"latency": 0.1, "utilization": 0.8, "loss": 0.1, "capacity": 0.0, "priority": 20},
        }
    )

settings = ControllerSettings(
    of_port=int(os.getenv("CONTROLLER_OF_PORT", 6653)),
    rest_port=int(os.getenv("CONTROLLER_REST_PORT", 8080)),
    controller_id=os.getenv("CONTROLLER_ID", "primary"),
    preferred=os.getenv("CONTROLLER_ROLE", "primary").lower() != "standby",
    peer_api_url=os.getenv("CONTROLLER_PEER_API_URL", ""),
    ha_interval_sec=float(os.getenv("CONTROLLER_HA_INTERVAL_SEC", 1.0)),
    ha_failure_threshold=int(os.getenv("CONTROLLER_HA_FAILURE_THRESHOLD", 3)),
    ha_recovery_threshold=int(os.getenv("CONTROLLER_HA_RECOVERY_THRESHOLD", 3)),
    route_over_unconfirmed_links=os.getenv("ROUTE_OVER_UNCONFIRMED_LINKS", "false").lower() == "true",
    reference_capacity_mbps=float(os.getenv("REFERENCE_CAPACITY_MBPS", 100.0)),
    capacity_weight=float(os.getenv("CAPACITY_WEIGHT", 0.0)),
    utilization_noise_floor_pct=float(os.getenv("UTILIZATION_NOISE_FLOOR_PCT", 1.0)),
    seed_mesh=os.getenv("CONTROLLER_SEED_MESH", "true").lower() != "false",
    monitor_interval=float(os.getenv("MONITOR_INTERVAL_SEC", 2.0)),
    utilization_threshold_pct=float(os.getenv("UTILIZATION_THRESHOLD_PCT", 85.0)),
    congestion_persistence_cycles=int(os.getenv("CONGESTION_PERSISTENCE_CYCLES", 3)),
    congestion_cooldown_sec=float(os.getenv("CONGESTION_COOLDOWN_SEC", 10.0)),
    latency_weight=float(os.getenv("LATENCY_WEIGHT", 0.4)),
    utilization_weight=float(os.getenv("UTILIZATION_WEIGHT", 0.4)),
    loss_weight=float(os.getenv("LOSS_WEIGHT", 0.2)),
    api_token=os.getenv("CONTROLLER_API_TOKEN", ""),
)
