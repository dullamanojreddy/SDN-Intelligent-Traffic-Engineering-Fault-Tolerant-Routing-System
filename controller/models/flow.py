"""
Flow and Match Data Models
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class FlowMatch(BaseModel):
    in_port: Optional[int] = None
    eth_src: Optional[str] = None
    eth_dst: Optional[str] = None
    eth_type: Optional[int] = None
    ipv4_src: Optional[str] = None
    ipv4_dst: Optional[str] = None
    ip_proto: Optional[int] = None
    tcp_src: Optional[int] = None
    tcp_dst: Optional[int] = None
    udp_src: Optional[int] = None
    udp_dst: Optional[int] = None

class FlowInstruction(BaseModel):
    type: str = "APPLY_ACTIONS"
    actions: List[str] = []

class FlowEntry(BaseModel):
    flow_id: str
    dpid: str
    table_id: int = 0
    priority: int = 0
    match: FlowMatch = Field(default_factory=FlowMatch)
    instructions: List[FlowInstruction] = Field(default_factory=list)
    packet_count: int = 0
    byte_count: int = 0
    duration_sec: int = 0
    idle_timeout: int = 0
    hard_timeout: int = 0
    status: str = "ACTIVE"
