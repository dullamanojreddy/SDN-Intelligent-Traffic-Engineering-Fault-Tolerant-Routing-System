"""
FastAPI Request & Response Schemas
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from controller.models.topology import SwitchNode, HostNode, LinkEdge, TopologyData
from controller.models.flow import FlowEntry
from controller.models.metric import NetworkSummaryMetrics, PortMetric
from controller.models.event import NetworkEvent, RoutingDecision

class SystemStatusResponse(BaseModel):
    status: str = "ONLINE"
    version: str = "1.0.0"
    environment: str = "development"
    controller_connected: bool = True
    database_connected: bool = False
    database_mode: str = "IN_MEMORY"
    active_switches: int = 0
    active_hosts: int = 0
    active_links: int = 0
    active_flows: int = 0
    uptime_sec: float = 0.0

class RecalculateRouteRequest(BaseModel):
    source_ip: str
    dest_ip: str
    qos_class: str = "DEFAULT"

class TrafficStartRequest(BaseModel):
    src_host: str
    dst_host: str
    rate_mbps: float = 50.0
    duration_sec: int = 30
    protocol: str = "TCP"

class FailureSimulateRequest(BaseModel):
    src_switch: str
    dst_switch: str
    action: str = "DOWN"  # DOWN or UP

class ExperimentStartRequest(BaseModel):
    name: str
    type: str
    topology: str = "mesh"
    traffic_rate_mbps: float = 80.0
    duration_sec: int = 60
