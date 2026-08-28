"""
OpenFlow 1.3 Port & Flow Statistics Monitoring Subsystem
"""
import asyncio
import time
from typing import Dict, List, Optional, Tuple, Any, Callable
from controller.utils.logger import log
from controller.openflow.protocol import (
    OFPP_ANY,
    build_port_stats_request,
    parse_port_stats_reply,
    DecodedPortStats,
)
from controller.openflow.switch_manager import SwitchManager, Datapath
from controller.topology.graph import NetworkGraph
from controller.congestion.detector import CongestionDetector
from controller.events.event_manager import EventManager

class StatsManager:
    """
    Periodically polls port and flow statistics from OVS switches,
    calculates Mbps throughput, utilization %, and packet drops,
    and feeds telemetry into the NetworkGraph and CongestionDetector.
    """
    def __init__(
        self,
        switch_manager: SwitchManager,
        network_graph: NetworkGraph,
        congestion_detector: CongestionDetector,
        event_manager: Optional[EventManager] = None,
        on_congestion_alert: Optional[Callable[[str, float], Any]] = None,
        poll_interval: float = 2.0,
    ):
        self.switch_manager = switch_manager
        self.network_graph = network_graph
        self.congestion_detector = congestion_detector
        self.event_manager = event_manager
        self.on_congestion_alert = on_congestion_alert
        self.poll_interval = poll_interval
        
        # Previous port stats cache: (dpid, port_no) -> (timestamp, tx_bytes, rx_bytes, tx_pkts, tx_drops)
        self.prev_stats: Dict[Tuple[int, int], Tuple[float, int, int, int, int]] = {}
        # Calculated link metrics: link_id -> {"throughput_mbps": float, "utilization_pct": float, "drop_rate": float}
        self.link_metrics: Dict[str, Dict[str, float]] = {}
        
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self):
        """Starts the periodic statistics polling loop."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._poll_loop())
            log.info(f"Statistics Manager started (polling interval={self.poll_interval}s)")

    def stop(self):
        """Stops the statistics polling loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()

    async def _poll_loop(self):
        """Periodically polls all connected switches for port statistics."""
        while self._running:
            try:
                await self.request_all_port_stats()
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in stats polling loop: {e}")
                await asyncio.sleep(1.0)

    async def request_all_port_stats(self):
        """Sends OFPMP_PORT_STATS requests to all active switches."""
        for dp in list(self.switch_manager.datapaths.values()):
            req = build_port_stats_request(port_no=OFPP_ANY)
            await dp.send_msg(req)

    def handle_port_stats_reply(self, dp: Any, data: bytes):
        """Decodes port stats reply and computes throughput and utilization."""
        stats_list: List[DecodedPortStats] = parse_port_stats_reply(data)
        now = time.time()
        
        for st in stats_list:
            key = (dp.dpid, st.port_no)
            if key in self.prev_stats:
                prev_time, prev_tx_b, prev_rx_b, prev_tx_p, prev_tx_d = self.prev_stats[key]
                dt = now - prev_time
                if dt > 0.1:
                    delta_tx_bytes = max(0, st.tx_bytes - prev_tx_b)
                    delta_tx_pkts = max(0, st.tx_packets - prev_tx_p)
                    delta_tx_drops = max(0, st.tx_dropped - prev_tx_d)
                    
                    # Bandwidth in Mbps: (Bytes * 8) / (dt * 1e6)
                    tx_mbps = (delta_tx_bytes * 8.0) / (dt * 1_000_000.0)
                    
                    # Packet drop rate
                    total_tx = delta_tx_pkts + delta_tx_drops
                    drop_rate = (delta_tx_drops / total_tx) if total_tx > 0 else 0.0
                    
                    # Find matching link in NetworkGraph
                    src_sw = dp.sw_id
                    for u, v, link_data in self.network_graph.graph.edges(data=True):
                        if u == src_sw and link_data.get("src_port") == st.port_no:
                            capacity = link_data.get("capacity_mbps", 100.0)
                            util_pct = min(100.0, (tx_mbps / capacity) * 100.0) if capacity > 0 else 0.0
                            
                            # Update graph metrics
                            self.network_graph.update_link_utilization(u, v, util_pct)
                            self.network_graph.update_link_packet_loss(u, v, drop_rate)
                            
                            link_id = f"{u}-{v}"
                            self.link_metrics[link_id] = {
                                "throughput_mbps": tx_mbps,
                                "utilization_pct": util_pct,
                                "drop_rate": drop_rate,
                            }
                            
                            # Feed into CongestionDetector
                            cong_event = self.congestion_detector.check_link(link_id, util_pct)
                            if cong_event:
                                log.warning(
                                    f"🚨 CONGESTION DETECTED on {link_id}: {util_pct:.1f}% load "
                                    f"(Throughput: {tx_mbps:.2f} Mbps, Drops: {drop_rate*100:.2f}%)"
                                )
                                if self.event_manager:
                                    self.event_manager.publish(cong_event)
                                if self.on_congestion_alert:
                                    self.on_congestion_alert(link_id, util_pct)
                                    
            self.prev_stats[key] = (now, st.tx_bytes, st.rx_bytes, st.tx_packets, st.tx_dropped)
