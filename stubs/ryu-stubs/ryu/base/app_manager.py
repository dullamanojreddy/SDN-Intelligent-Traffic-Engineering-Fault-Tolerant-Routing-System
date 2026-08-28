"""Ryu App Manager Stub"""
from typing import List, Any, Dict

class RyuApp:
    """Base class for Ryu applications."""
    OFP_VERSIONS: List[int] = []
    _CONTEXTS: Dict[str, Any] = {}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.logger: Any = None

    def start(self) -> None: ...
    def stop(self) -> None: ...
