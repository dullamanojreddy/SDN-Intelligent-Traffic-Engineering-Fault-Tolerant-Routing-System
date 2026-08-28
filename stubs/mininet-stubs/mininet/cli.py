"""Mininet CLI Stub"""
from typing import Any

class CLI:
    """Mininet interactive command-line interface."""
    def __init__(self, mininet: Any, stdin: Any = None, script: Any = None,
                 **kwargs: Any) -> None: ...
    def do_help(self, line: str) -> None: ...
    def do_quit(self, line: str) -> bool: return True
    def default(self, line: str) -> None: ...
