"""
SDN-ITE OpenFlow 1.3 Controller Application & Engine
"""
import sys
import os
import asyncio
from typing import Dict, List, Optional, Tuple, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from controller.topology.graph import NetworkGraph
from controller.routing.dijkstra import DijkstraRouter
from controller.routing.path_optimizer import PathOptimizer
from controller.congestion.detector import CongestionDetector
from controller.failure.detector import FailureDetector, RecoveryEngine
from controller.qos.qos_engine import QoSEngine
from controller.events.event_manager import EventManager
from controller.config.settings import settings
from controller.utils.logger import log

from controller.openflow.protocol import (
    OFP_VERSION,
    OFPT_PORT_STATUS,
    OFPPR_DELETE,
    OFPPR_MODIFY,
    parse_port_status,
)
from controller.openflow.switch_manager import SwitchManager, Datapath
from controller.openflow.flow_manager import FlowManager
from controller.openflow.packet_handler import PacketHandler
from controller.openflow.stats_manager import StatsManager
from controller.topology.discovery import TopologyDiscovery


class SDNTrafficEngineApp:
    """
    Main Controller Application combining native OpenFlow 1.3 server runtime
    with intelligent Multi-Metric Routing, Congestion Avoidance, and Fast Failover.
    """
    OFP_VERSIONS = [OFP_VERSION]

    def __init__(self, *args, **kwargs):
        # 1. Core SDN Intelligence Layer
        self.network_graph = NetworkGraph()
        self.router = DijkstraRouter(self.network_graph)
        self.optimizer = PathOptimizer(self.router)
        self.congestion_detector = CongestionDetector(
            threshold_pct=settings.utilization_threshold_pct,
            persistence_cycles=settings.congestion_persistence_cycles,
        )
        self.failure_detector = FailureDetector(self.network_graph)
        self.recovery_engine = RecoveryEngine(self.router)
        self.qos_engine = QoSEngine()
        self.event_manager = EventManager()

        # 2. OpenFlow 1.3 Communication Subsystems
        self.switch_manager = SwitchManager(
            on_switch_connected=self._on_switch_connected,
            on_switch_disconnected=self._on_switch_disconnected,
            on_packet_in=self._on_packet_in,
            on_port_stats_reply=self._on_port_stats_reply,
            on_port_status=self._on_port_status,
        )
        self.flow_manager = FlowManager(self.switch_manager)
        self.topology_discovery = TopologyDiscovery(
            network_graph=self.network_graph,
            switch_manager=self.switch_manager,
            event_manager=self.event_manager,
            probe_interval=3.0,
        )
        self.stats_manager = StatsManager(
            switch_manager=self.switch_manager,
            network_graph=self.network_graph,
            congestion_detector=self.congestion_detector,
            event_manager=self.event_manager,
            on_congestion_alert=self._on_congestion_alert,
            poll_interval=settings.monitor_interval,
        )
        self.packet_handler = PacketHandler(
            switch_manager=self.switch_manager,
            flow_manager=self.flow_manager,
            network_graph=self.network_graph,
            router=self.router,
            topology_discovery=self.topology_discovery,
            event_manager=self.event_manager,
        )

        # Datapath and Flow references
        self.datapaths = self.switch_manager.datapaths
        self.active_flows = self.flow_manager.active_flows

        log.info("=" * 60)
        log.info("SDN Intelligent Traffic Engineering Controller Initialized")
        log.info(
            f"OpenFlow 1.3 | Port: 6653 | Monitor Interval: {settings.monitor_interval}s | "
            f"Congestion Threshold: {settings.utilization_threshold_pct}%"
        )
        log.info("=" * 60)

    # --------------------------------------------------------------------------
    # Switch Event Handlers
    # --------------------------------------------------------------------------
    def _on_switch_connected(self, dp: Datapath):
        """Called when an OpenFlow 1.3 switch finishes handshake."""
        self.network_graph.add_switch(dp.sw_id)
        log.info(f"Connected to Switch {dp.sw_id} ({dp.addr})")
        if self.event_manager:
            self.event_manager.emit(
                "switch_connected", {"switch": dp.sw_id, "dpid": dp.dpid, "addr": str(dp.addr)}
            )

    def _on_switch_disconnected(self, dp: Datapath):
        """Called when a switch disconnects."""
        log.warning(f"Switch Disconnected: {dp.sw_id}")
        if self.event_manager:
            self.event_manager.emit(
                "switch_disconnected", {"switch": dp.sw_id, "dpid": dp.dpid}
            )

    async def _on_packet_in(self, dp: Datapath, raw_data: bytes):
        """Dispatches incoming Packet-In messages."""
        await self.packet_handler.handle_packet_in(dp, raw_data)

    def _on_port_stats_reply(self, dp: Datapath, raw_data: bytes):
        """Dispatches port stats reply to StatsManager."""
        self.stats_manager.handle_port_stats_reply(dp, raw_data)

    def _on_port_status(self, dp: Datapath, raw_data: bytes):
        """Handles OpenFlow Port Status change (link up/down)."""
        status = parse_port_status(raw_data)
        if not status:
            return
        
        # Reason 1: OFPPR_DELETE, or state link down
        is_down = (status.reason == OFPPR_DELETE) or (status.state & 1)  # OFPPS_LINK_DOWN = 1
        if is_down:
            log.error(f"🚨 PORT DOWN DETECTED: Switch {dp.sw_id} Port {status.port_no} ({status.name})")
            events = self.failure_detector.handle_port_down(dp.sw_id, status.port_no)
            for ev in events:
                if self.event_manager:
                    self.event_manager.emit("link_failure", ev.model_dump() if hasattr(ev, 'model_dump') else ev.__dict__)
                # Trigger failover recalculation
                self._trigger_failover_recovery(ev.data.get("link_id", ""))
        else:
            # Port is UP - update any matching links to active
            for u, v, d in self.network_graph.graph.edges(data=True):
                if (u == dp.sw_id and d.get("src_port") == status.port_no) or (v == dp.sw_id and d.get("dst_port") == status.port_no):
                    self.network_graph.update_link_metrics(u, v, utilization_pct=d.get("utilization_pct", 0.0), is_active=True)

    def _on_congestion_alert(self, link_id: str, utilization: float):
        """Triggered when sustained congestion is detected on a link."""
        log.warning(f"⚡ Initiating dynamic rerouting away from congested link {link_id} ({utilization:.1f}%)")
        congested_flows = list(self.active_flows.values())
        if congested_flows:
            new_routes = self.optimizer.optimize_congested_flows(
                congested_flows, congested_link=link_id
            )
            for old_flow, new_path, new_cost in new_routes:
                log.info(f"Rerouted Flow -> New Path: {' -> '.join(new_path)} (Cost: {new_cost:.4f})")
                asyncio.create_task(self._install_rerouted_flow(old_flow, new_path))

    async def _install_rerouted_flow(self, flow_info: Dict[str, Any], path: List[str]):
        """Installs forwarding rules dynamically for a specific rerouted flow using topology-derived endpoints."""
        if not path or len(path) < 2:
            return
        match = flow_info.get("match", {})
        dst_ip = match.get("ipv4_dst")
        if not dst_ip:
            return

        dst_host_info = self.packet_handler.host_ip_table.get(dst_ip)
        if not dst_host_info:
            return
        dst_sw, dst_port, dst_mac = dst_host_info

        src_sw = path[0]
        src_ip = "0.0.0.0"
        src_port = 1
        src_mac = None
        for ip, (sw, port, mac) in self.packet_handler.host_ip_table.items():
            if sw == src_sw and ip != dst_ip:
                src_ip = ip
                src_port = port
                src_mac = mac
                break

        hops = self.packet_handler._build_port_hops(path, ingress_port=src_port, egress_port=dst_port)
        await self.flow_manager.install_path_forwarding(
            path=path,
            port_hops=hops,
            src_ip=src_ip,
            dst_ip=dst_ip,
            src_mac=src_mac,
            dst_mac=dst_mac,
            priority=200,  # Higher priority override
            idle_timeout=300,
        )

    async def _install_rerouted_path(self, path: List[str]):
        """Fallback dynamic rerouter for all flows traversing the path endpoints."""
        if not path or len(path) < 2:
            return
        for flow in list(self.active_flows.values()):
            await self._install_rerouted_flow(flow, path)

    def _trigger_failover_recovery(self, failed_link_id: str):
        """Recalculates paths for affected flows upon link failure."""
        u, v = failed_link_id.split("-") if "-" in failed_link_id else ("", "")
        if not u or not v:
            return
        
        new_path, cost, recovery_time = self.recovery_engine.compute_failover_path(u, v, failed_link_id)
        if new_path and len(new_path) >= 2:
            log.info(
                f"✅ Sub-second Failover Route Computed: {' -> '.join(new_path)} "
                f"(Cost: {cost:.4f}, Recovery Duration: {recovery_time:.2f}ms)"
            )
            if self.event_manager:
                self.event_manager.emit(
                    "failover_recovered",
                    {"failed_link": failed_link_id, "new_path": new_path, "recovery_ms": recovery_time},
                )
            for flow in list(self.active_flows.values()):
                asyncio.create_task(self._install_rerouted_flow(flow, new_path))

    # --------------------------------------------------------------------------
    # Topology Initialization & Startup
    # --------------------------------------------------------------------------
    def initialize_mesh_topology(self):
        """Initializes the baseline target mesh topology for discovery and testing."""
        switches_list = ["s1", "s2", "s3", "s4", "s5", "s6", "s7"]
        for sw in switches_list:
            self.network_graph.add_switch(sw)
            
        links = [
            ("s1", "s2", 1, 1, 100.0, 5.0),
            ("s1", "s3", 2, 1, 100.0, 5.0),
            ("s2", "s4", 2, 1, 100.0, 6.0),
            ("s2", "s5", 3, 1, 100.0, 5.0),
            ("s3", "s4", 2, 2, 100.0, 6.0),
            ("s3", "s6", 3, 1, 100.0, 5.0),
            ("s4", "s7", 3, 1, 100.0, 5.0),
            ("s5", "s7", 2, 2, 100.0, 5.0),
            ("s6", "s7", 2, 3, 100.0, 5.0),
        ]
        
        for u, v, p1, p2, cap, lat in links:
            self.network_graph.add_link(u, v, p1, p2, capacity_mbps=cap, latency_ms=lat)
            self.network_graph.add_link(v, u, p2, p1, capacity_mbps=cap, latency_ms=lat)
            
        log.info(f"Initialized mesh topology with {len(switches_list)} switches and {len(links)*2} directed links.")

    async def _proactive_mesh_route_worker(self):
        """
        Background worker that provisions and maintains proactive baseline OpenFlow routes
        once mesh switches complete their OpenFlow 1.3 handshakes.
        """
        while True:
            try:
                await asyncio.sleep(0.2)
                connected_switches = set(dp.sw_id for dp in self.switch_manager.datapaths.values())
                if len(connected_switches) >= 7 or ("s1" in connected_switches and "s7" in connected_switches):
                    await self.packet_handler.install_proactive_mesh_routes()
                    log.info("[PROACTIVE ROUTE] Baseline OpenFlow forwarding rules successfully provisioned for all mesh switches.")
                    await asyncio.sleep(30.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.warning(f"Proactive route worker notice: {e}")

    async def run(self, host: str = "0.0.0.0", port: int = 6653):
        """Runs the asynchronous OpenFlow 1.3 controller."""
        # Initialize default baseline topology
        self.initialize_mesh_topology()
        
        # Start TCP server
        await self.switch_manager.start_server(host=host, port=port)
        # Start LLDP Discovery loop
        self.topology_discovery.start()
        # Start Statistics Poller
        self.stats_manager.start()
        # Schedule proactive route provisioning worker
        asyncio.create_task(self._proactive_mesh_route_worker())

        log.info(f"🚀 SDN-ITE Controller Engine is LIVE and ready for OpenFlow 1.3 switches on {host}:{port}")

        try:
            while True:
                await asyncio.sleep(3600)
        except (asyncio.CancelledError, KeyboardInterrupt):
            log.info("Stopping SDN-ITE Controller Engine...")
        finally:
            self.topology_discovery.stop()
            self.stats_manager.stop()
            await self.switch_manager.stop_server()


if __name__ == "__main__":
    app = SDNTrafficEngineApp()
    try:
        asyncio.run(app.run(host="0.0.0.0", port=6653))
    except KeyboardInterrupt:
        log.info("Controller exited cleanly.")
