"""Ryu Controller Handler & Events Stubs"""
from typing import Any, Callable

HANDSHAKE_DISPATCHER: str = "handshake"
CONFIG_DISPATCHER: str = "config"
MAIN_DISPATCHER: str = "main"
DEAD_DISPATCHER: str = "dead"

def set_ev_cls(ev: Any, dispatchers: Any = None) -> Callable:
    """Decorator for event handler methods."""
    def decorator(func: Callable) -> Callable:
        return func
    return decorator

def set_ev_handler(ev: Any, dispatchers: Any = None) -> Callable:
    """Decorator for event handler methods."""
    def decorator(func: Callable) -> Callable:
        return func
    return decorator
