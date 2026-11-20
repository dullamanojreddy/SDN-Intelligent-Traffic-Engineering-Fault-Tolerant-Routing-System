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


class SwitchCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=32, pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")


class HostCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=32, pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")
    ip: str = Field(..., min_length=7, max_length=64)
    mac: Optional[str] = None
    connected_switch: str = Field(..., min_length=2, max_length=32)


class LinkCreateRequest(BaseModel):
    src: str = Field(..., min_length=2, max_length=32)
    dst: str = Field(..., min_length=2, max_length=32)
    capacity_mbps: float = Field(default=100.0, gt=0, le=100000)
    latency_ms: float = Field(default=5.0, ge=0, le=60000)


class RouteInstallRequest(BaseModel):
    installation_id: str = Field(..., min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    source_ip: str = Field(..., min_length=7, max_length=64)
    dest_ip: str = Field(..., min_length=7, max_length=64)
    path: List[str] = Field(..., min_length=1, max_length=64)
    priority: int = Field(default=100, ge=1, le=65535)
    idle_timeout: int = Field(default=300, ge=0, le=86400)
    cookie: int = Field(default=0, ge=0)
