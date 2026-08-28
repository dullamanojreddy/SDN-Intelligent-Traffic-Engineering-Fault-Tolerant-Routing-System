"""
SDN Data Models for Topology, Nodes, and Links
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum

class NodeRole(str, Enum):
    SWITCH = "switch"
    HOST = "host"

class LinkStatus(str, Enum):
    NORMAL = "normal"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"
    FAILED = "failed"

class SwitchPort(BaseModel):
    port_no: int
    name: str = ""
    hw_addr: str = ""
    config: int = 0
    state: int = 0
    curr_speed: int = 0
    max_speed: int = 0

class SwitchNode(BaseModel):
    dpid: str
    dpid_int: int
    name: str
    ports: List[SwitchPort] = []
    ip: Optional[str] = None
    connected: bool = True
    active_flows: int = 0

class HostNode(BaseModel):
    mac: str
    ip: str
    connected_switch: str
    connected_port: int
    name: Optional[str] = None

class LinkEdge(BaseModel):
    link_id: str
    src_dpid: str
    src_port: int
    dst_dpid: str
    dst_port: int
    capacity_mbps: float = 100.0
    current_rate_mbps: float = 0.0
    utilization_pct: float = 0.0
    latency_ms: float = 5.0
    packet_loss_pct: float = 0.0
    status: LinkStatus = LinkStatus.NORMAL
    is_active: bool = True

class TopologyData(BaseModel):
    switches: List[SwitchNode] = []
    hosts: List[HostNode] = []
    links: List[LinkEdge] = []
    timestamp: str = ""
