"""
Network Event & Alert Models
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum

class EventType(str, Enum):
    TOPOLOGY_UPDATE = "TOPOLOGY_UPDATE"
    METRIC_UPDATE = "METRIC_UPDATE"
    LINK_CONGESTION = "LINK_CONGESTION"
    LINK_FAILURE = "LINK_FAILURE"
    ROUTE_CHANGE = "ROUTE_CHANGE"
    RECOVERY = "RECOVERY"
    ALERT = "ALERT"
    FLOW_UPDATE = "FLOW_UPDATE"
    EXPERIMENT_UPDATE = "EXPERIMENT_UPDATE"

class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class NetworkEvent(BaseModel):
    event_id: str
    type: EventType
    timestamp: str
    source: str
    message: str
    severity: AlertSeverity = AlertSeverity.INFO
    data: Dict[str, Any] = Field(default_factory=dict)

class RoutingDecision(BaseModel):
    decision_id: str
    timestamp: str
    source_ip: str
    dest_ip: str
    old_path: List[str]
    new_path: List[str]
    reason: str
    old_cost: float
    new_cost: float
    latency_ms: float
    utilization_pct: float
    packet_loss_pct: float
    qos_class: str = "DEFAULT"
