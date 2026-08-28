"""
Controller Event Manager & Notification Dispatcher
"""
import asyncio
from typing import List, Callable, Dict, Any
from controller.models.event import NetworkEvent
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

    def get_recent_events(self, limit: int = 50) -> List[NetworkEvent]:
        return self._history[-limit:]
