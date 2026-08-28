"""Mininet Net Stub"""
from typing import Any, Optional

class Mininet:
    """Primary Mininet network emulation class."""
    def __init__(self, topo: Any = None, switch: Any = None, host: Any = None,
                 controller: Any = None, link: Any = None, intf: Any = None,
                 build: bool = True, xterms: bool = False, cleanup: bool = False,
                 ipBase: str = '10.0.0.0/8', inNamespace: bool = False,
                 autoSetMacs: bool = False, autoStaticArp: bool = False,
                 autoPinCpus: bool = False, listenPort: Optional[int] = None,
                 waitConnected: bool = False) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def pingAll(self, timeout: Optional[int] = None) -> float: return 0.0
    def ping(self, hosts: Any = None, timeout: Optional[int] = None) -> float: return 0.0
    def iperf(self, hosts: Any = None, l4Type: str = 'TCP', udpBw: str = '10M',
              fmt: Optional[str] = None, seconds: int = 5, port: int = 5001) -> list: return []
    def get(self, name: str) -> Any: return None
    def addHost(self, name: str, **params: Any) -> Any: return None
    def addSwitch(self, name: str, **params: Any) -> Any: return None
    def addLink(self, node1: Any, node2: Any, **params: Any) -> Any: return None
    def configureControlNetwork(self) -> None: ...
