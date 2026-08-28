"""
Controller Event Manager & Notification Dispatcher
"""
import asyncio
import time
from typing import List, Callable, Dict, Any, Optional
from controller.models.event import NetworkEvent, EventType, AlertSeverity
from controller.utils.logger import log

class EventManager:
    def __init__(self):
        self._subscribers: List[Callable[[NetworkEvent], Any]] = []
        self._history: List[NetworkEvent] = []
        self._max_history = 200
        
    def subscribe(self, callback: Callable[[NetworkEvent], Any]):
        """Registers a listener callback for controller events."""
        self._subscribers.append(callback)
        
    def publish(self, event: NetworkEvent):
        """Broadcasts an event to all subscribers."""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)
            
        log.info(f"EVENT [{event.type}] {event.source}: {event.message}")
        
        for sub in self._subscribers:
            try:
                res = sub(event)
                if asyncio.iscoroutine(res):
                    asyncio.create_task(res)
            except Exception as e:
                log.error(f"Error notifying subscriber {sub}: {e}")

    def emit(self, event_type_name: str, data: Dict[str, Any], message: Optional[str] = None):
        """Helper to emit events from dictionary payloads."""
        ev_type = EventType.ALERT
        severity = AlertSeverity.INFO
        
        lower_name = event_type_name.lower()
        if "fail" in lower_name or "down" in lower_name:
            ev_type = EventType.LINK_FAILURE
            severity = AlertSeverity.CRITICAL
        elif "congest" in lower_name:
            ev_type = EventType.LINK_CONGESTION
            severity = AlertSeverity.WARNING
        elif "route" in lower_name or "reroute" in lower_name:
            ev_type = EventType.ROUTE_CHANGE
            severity = AlertSeverity.INFO
        elif "switch" in lower_name or "link" in lower_name or "topo" in lower_name:
            ev_type = EventType.TOPOLOGY_UPDATE
            severity = AlertSeverity.INFO
            
        msg = message if message else f"{event_type_name}: {data}"
        event = NetworkEvent(
            event_id=f"ev_{int(time.time() * 1000)}",
            type=ev_type,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            source="SDN_Controller",
            message=msg,
            severity=severity,
            data=data,
        )
        self.publish(event)

    def get_recent_events(self, limit: int = 50) -> List[NetworkEvent]:
        return self._history[-limit:]
