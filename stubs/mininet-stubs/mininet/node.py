"""Mininet Node Stubs"""
from typing import Any, Optional

class Node:
    """Base network node."""
    def __init__(self, name: str, **params: Any) -> None:
        self.name: str = name
        self.params: dict = params

    def cmd(self, *args: Any, **kwargs: Any) -> str: return ""
    def popen(self, *args: Any, **kwargs: Any) -> Any: return None
    def IP(self, intf: Any = None) -> str: return ""
    def MAC(self, intf: Any = None) -> str: return ""

class Host(Node):
    """A host node."""
    pass

class OVSSwitch(Node):
    """Open vSwitch-based switch."""
    def __init__(self, name: str, **params: Any) -> None:
        super().__init__(name, **params)
        self.dpid: str = ""

    def start(self, controllers: Any = None) -> None: ...
    def stop(self, deleteIntfs: bool = True) -> None: ...

class OVSBridge(OVSSwitch):
    """OVS Bridge."""
    pass

class Controller(Node):
    """SDN Controller node."""
    def __init__(self, name: str, **params: Any) -> None:
        super().__init__(name, **params)

    def start(self) -> None: ...
    def stop(self) -> None: ...

class RemoteController(Controller):
    """Remote SDN controller."""
    def __init__(self, name: str, ip: str = '127.0.0.1', port: int = 6653,
                 **kwargs: Any) -> None:
        super().__init__(name, **kwargs)
        self.ip: str = ip
        self.port: int = port
