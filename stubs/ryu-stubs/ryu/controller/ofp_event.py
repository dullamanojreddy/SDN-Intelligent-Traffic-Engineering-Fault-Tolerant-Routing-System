"""Ryu OpenFlow Event Stubs"""
from typing import Any

class EventOFPSwitchFeatures:
    """Switch features reply event."""
    msg: Any = None

class EventOFPPacketIn:
    """Packet-In event."""
    msg: Any = None

class EventOFPPortStatus:
    """Port status change event."""
    msg: Any = None

class EventOFPFlowStatsReply:
    """Flow stats reply event."""
    msg: Any = None

class EventOFPPortStatsReply:
    """Port stats reply event."""
    msg: Any = None
