"""Ryu Topology Switches Stubs"""
from typing import Any, List, Optional

class Port:
    """Represents an OpenFlow switch port."""
    def __init__(self) -> None:
        self.dpid: int = 0
        self.port_no: int = 0
        self.name: str = ""
        self.hw_addr: str = ""
        self.is_live: bool = True

class Switch:
    """Represents an OpenFlow switch."""
    def __init__(self) -> None:
        self.dp: Any = None
        self.ports: List[Port] = []

class Link:
    """Represents a link between two ports."""
    def __init__(self) -> None:
        self.src: Port = Port()
        self.dst: Port = Port()
