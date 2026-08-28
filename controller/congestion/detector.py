"""
Stateful Congestion Detector with Persistence and Anti-Flapping
"""
import time
from typing import Dict, List, Optional, Set
from controller.config.settings import settings
from controller.models.event import NetworkEvent, EventType, AlertSeverity
from controller.utils.logger import log

class CongestionDetector:
    def __init__(
        self,
        threshold_pct: float = settings.utilization_threshold_pct,
        persistence_cycles: int = settings.congestion_persistence_cycles,
        cooldown_sec: float = settings.congestion_cooldown_sec
    ):
        self.threshold_pct = threshold_pct
        self.persistence_cycles = persistence_cycles
        self.cooldown_sec = cooldown_sec
        
        # Link state: (src_dpid, dst_dpid) -> consecutive cycles above threshold
        self.consecutive_breaches: Dict[str, int] = {}
        # Cooldown timer: (src_dpid, dst_dpid) -> last reroute timestamp
        self.last_reroute_time: Dict[str, float] = {}
        
    def check_link(self, link_id: str, utilization_pct: float) -> Optional[NetworkEvent]:
        """
        Updates link reading and triggers CONGESTION_EVENT if persistent congestion is confirmed.
        """
        now = time.time()
        
        if utilization_pct >= self.threshold_pct:
            self.consecutive_breaches[link_id] = self.consecutive_breaches.get(link_id, 0) + 1
            log.debug(f"Link {link_id} utilization at {utilization_pct:.1f}% (Cycle {self.consecutive_breaches[link_id]}/{self.persistence_cycles})")
            
            if self.consecutive_breaches[link_id] >= self.persistence_cycles:
                # Check cooldown to prevent route flapping
                last_time = self.last_reroute_time.get(link_id, 0)
                if (now - last_time) >= self.cooldown_sec:
                    self.last_reroute_time[link_id] = now
                    # Reset counter
                    self.consecutive_breaches[link_id] = 0
                    
                    event = NetworkEvent(
                        event_id=f"ev_cong_{int(now * 1000)}",
                        type=EventType.LINK_CONGESTION,
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        source=f"Link {link_id}",
                        message=f"Persistent congestion detected: {utilization_pct:.1f}% utilization over {self.persistence_cycles} cycles",
                        severity=AlertSeverity.WARNING,
                        data={"link_id": link_id, "utilization_pct": utilization_pct}
                    )
                    return event
        else:
            # Recovery / normal reading resets breach count
            if link_id in self.consecutive_breaches:
                self.consecutive_breaches[link_id] = 0
                
        return None
