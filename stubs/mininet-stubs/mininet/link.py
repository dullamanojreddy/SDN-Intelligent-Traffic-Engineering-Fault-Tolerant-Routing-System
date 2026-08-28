"""Mininet Link Stubs"""
from typing import Any, Optional

class Link:
    """A basic link."""
    def __init__(self, node1: Any = None, node2: Any = None, **params: Any) -> None:
        self.intf1: Any = None
        self.intf2: Any = None

class TCLink(Link):
    """Link with traffic control (bandwidth, delay, loss)."""
    def __init__(self, node1: Any = None, node2: Any = None, port1: Optional[int] = None,
                 port2: Optional[int] = None, bw: Optional[float] = None,
                 delay: Optional[str] = None, loss: Optional[float] = None,
                 max_queue_size: Optional[int] = None, **params: Any) -> None:
        super().__init__(node1, node2, **params)

class TCIntf:
    """Traffic control interface."""
    pass

class Intf:
    """Basic interface."""
    def __init__(self, name: str, node: Any = None, **params: Any) -> None:
        self.name: str = name
        self.node: Any = node
