"""
Ryu Controller Handler & Events Stubs
"""
from typing import Any, Callable

HANDSHAKE_DISPATCHER = "handshake"
CONFIG_DISPATCHER = "config"
MAIN_DISPATCHER = "main"
DEAD_DISPATCHER = "dead"

def set_ev_cls(ev: Any, dispatchers: Any = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        return func
    return decorator

def set_ev_handler(ev: Any, dispatchers: Any = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        return func
    return decorator
