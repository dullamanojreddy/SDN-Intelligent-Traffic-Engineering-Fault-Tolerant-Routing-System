"""Ryu Topology Event Stubs"""
from typing import Any

class EventSwitchEnter:
    """Event triggered when a new switch connects."""
    switch: Any = None

class EventSwitchLeave:
    """Event triggered when a switch disconnects."""
    switch: Any = None

class EventLinkAdd:
    """Event triggered when a new link is discovered."""
    link: Any = None

class EventLinkDelete:
    """Event triggered when a link goes down."""
    link: Any = None
