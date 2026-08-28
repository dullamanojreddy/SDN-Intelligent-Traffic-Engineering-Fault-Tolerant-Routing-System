"""
Dynamic LLDP Topology Discovery Engine
"""
import asyncio
from typing import Dict, Set, Tuple, Optional, Any
from controller.utils.logger import log
from controller.openflow.protocol import (
    OFPP_CONTROLLER,
    build_action_output,
    build_packet_out,
    build_lldp_packet,
    parse_lldp,
)
from controller.topology.graph import NetworkGraph
from controller.openflow.switch_manager import SwitchManager, Datapath
from controller.events.event_manager import EventManager

class TopologyDiscovery:
    """
    Discovers inter-switch links dynamically using periodic LLDP packet broadcasts.
    """
    def __init__(
        self,
        network_graph: NetworkGraph,
        switch_manager: SwitchManager,
        event_manager: Optional[EventManager] = None,
        probe_interval: float = 3.0,
    ):
        self.network_graph = network_graph
        self.switch_manager = switch_manager
        self.event_manager = event_manager
        self.probe_interval = probe_interval
        
        # Discovered links: (src_sw, src_port, dst_sw, dst_port)
        self.inter_switch_links: Set[Tuple[str, int, str, int]] = set()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self):
        """Starts the periodic LLDP probe loop."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._probe_loop())
            log.info(f"Topology Discovery LLDP probe loop started (interval={self.probe_interval}s)")

    def stop(self):
        """Stops the LLDP probe loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()

    async def _probe_loop(self):
        """Continuously broadcasts LLDP packets across all switch ports."""
        while self._running:
            try:
                await self.send_lldp_probes()
                await asyncio.sleep(self.probe_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in LLDP probe loop: {e}")
                await asyncio.sleep(1.0)

    async def send_lldp_probes(self):
        """Sends LLDP probe packets out of all active switch ports."""
        for dpid, dp in list(self.switch_manager.datapaths.items()):
            # By default probe ports 1..16 if specific port list is not yet populated
            ports_to_probe = list(dp.ports.keys()) if dp.ports else list(range(1, 8))
            for port_no in ports_to_probe:
                lldp_pkt = build_lldp_packet(dpid, port_no)
                actions = build_action_output(port_no)
                pkt_out = build_packet_out(
                    buffer_id=0xffffffff,
                    in_port=OFPP_CONTROLLER,
                    actions=actions,
                    data=lldp_pkt,
                )
                await dp.send_msg(pkt_out)

    def handle_lldp_packet(self, dst_dp: Datapath, in_port: int, lldp_payload: bytes):
        """Processes received LLDP packet to discover an inter-switch link."""
        parsed = parse_lldp(lldp_payload)
        if not parsed:
            return
            
        src_sw = f"s{parsed.src_dpid}"
        dst_sw = dst_dp.sw_id
        src_port = parsed.src_port
        dst_port = in_port
        
        link_tuple = (src_sw, src_port, dst_sw, dst_port)
        if link_tuple not in self.inter_switch_links:
            self.inter_switch_links.add(link_tuple)
            
            # Ensure switches exist in graph
            self.network_graph.add_switch(src_sw)
            self.network_graph.add_switch(dst_sw)
            
            # Add bidirectional link to NetworkGraph
            self.network_graph.add_link(
                src_sw, dst_sw, src_port, dst_port, capacity_mbps=100.0, latency_ms=5.0
            )
            self.network_graph.add_link(
                dst_sw, src_sw, dst_port, src_port, capacity_mbps=100.0, latency_ms=5.0
            )
            
            log.info(f"Discovered Link: {src_sw}:p{src_port} <---> {dst_sw}:p{dst_port}")
            if self.event_manager:
                self.event_manager.emit(
                    "link_discovered",
                    {"src": src_sw, "src_port": src_port, "dst": dst_sw, "dst_port": dst_port},
                )
