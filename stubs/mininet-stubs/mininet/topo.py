"""Mininet Topology Stub"""
from typing import Any, Optional

class Topo:
    """Network topology base class."""
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    def build(self, *args: Any, **kwargs: Any) -> None: ...
    def addSwitch(self, name: str, **opts: Any) -> str: return name
    def addHost(self, name: str, **opts: Any) -> str: return name
    def addLink(self, node1: Any, node2: Any, **opts: Any) -> Any: return (node1, node2)
    def addController(self, name: str, **opts: Any) -> str: return name
    def switches(self) -> list: return []
    def hosts(self) -> list: return []
    def links(self) -> list: return []
