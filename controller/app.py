"""
SDN-ITE Ryu OpenFlow 1.3 Controller Application
"""
import sys
import os
from typing import Dict, List, Optional, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, arp
from ryu.topology import event, switches

from controller.topology.graph import NetworkGraph
from controller.routing.dijkstra import DijkstraRouter
from controller.routing.path_optimizer import PathOptimizer
from controller.congestion.detector import CongestionDetector
from controller.failure.detector import FailureDetector, RecoveryEngine
from controller.qos.qos_engine import QoSEngine
from controller.events.event_manager import EventManager
from controller.config.settings import settings
from controller.utils.logger import log

class SDNTrafficEngineApp(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
        
    def __init__(self, *args, **kwargs):
        super(SDNTrafficEngineApp, self).__init__(*args, **kwargs)
        self.network_graph = NetworkGraph()
        self.router = DijkstraRouter(self.network_graph)
        self.optimizer = PathOptimizer(self.router)
        self.congestion_detector = CongestionDetector()
        self.failure_detector = FailureDetector(self.network_graph)
        self.recovery_engine = RecoveryEngine(self.router)
        self.qos_engine = QoSEngine()
        self.event_manager = EventManager()
        
        self.datapaths: Dict[int, Any] = {}
        self.active_flows: Dict[str, Any] = {}
        
        log.info("=" * 60)
        log.info("SDN Intelligent Traffic Engineering Controller Initialized")
        log.info(f"OpenFlow 1.3 | Monitor Interval: {settings.monitor_interval}s | Congestion Threshold: {settings.utilization_threshold_pct}%")
        log.info("=" * 60)

    def initialize_mesh_topology(self):
        """Initializes the baseline target mesh topology for discovery and testing."""
        # Switches: S1, S2, S3, S4, S5, S6, S7
        switches_list = ["s1", "s2", "s3", "s4", "s5", "s6", "s7"]
        for sw in switches_list:
            self.network_graph.add_switch(sw)
            
        # Core links (Bidirectional)
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

if __name__ == "__main__":
    app = SDNTrafficEngineApp()
    app.initialize_mesh_topology()
    path, cost = app.router.calculate_shortest_path("s1", "s7")
    log.info(f"Default shortest path from S1 to S7: {path} (Cost: {cost:.4f})")
