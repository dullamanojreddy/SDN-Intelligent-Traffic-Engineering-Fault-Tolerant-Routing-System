"""
OpenFlow 1.3 Packet-In & Dynamic Forwarding Engine
"""
import struct
from typing import Dict, List, Optional, Tuple, Any
from controller.utils.logger import log
from controller.openflow.protocol import (
    OFPP_FLOOD,
    OFPP_CONTROLLER,
    ETH_TYPE_IP,
    ETH_TYPE_ARP,
    ETH_TYPE_LLDP,
    build_action_output,
    build_packet_out,
    parse_packet_in,
    parse_ethernet,
    parse_arp,
    parse_ipv4,
    str_to_mac,
    str_to_ip,
)
from controller.openflow.switch_manager import SwitchManager, Datapath
from controller.openflow.flow_manager import FlowManager
from controller.topology.graph import NetworkGraph
from controller.topology.discovery import TopologyDiscovery
from controller.routing.dijkstra import DijkstraRouter
from controller.events.event_manager import EventManager

class PacketHandler:
    """
    Handles Packet-In messages:
    - Filters LLDP for dynamic topology discovery
    - Learns Host MAC/IP to switch:port bindings
    - Safely resolves ARP requests
    - Computes Multi-Metric Dijkstra paths for IPv4 traffic and programs flow tables
    """
    def __init__(
        self,
        switch_manager: SwitchManager,
        flow_manager: FlowManager,
        network_graph: NetworkGraph,
        router: DijkstraRouter,
        topology_discovery: TopologyDiscovery,
        event_manager: Optional[EventManager] = None,
    ):
        self.switch_manager = switch_manager
        self.flow_manager = flow_manager
        self.network_graph = network_graph
        self.router = router
        self.topology_discovery = topology_discovery
        self.event_manager = event_manager

        # Host Tables:
        # mac -> (switch_id, in_port, ip)
        self.host_mac_table: Dict[str, Tuple[str, int, Optional[str]]] = {}
        # ip -> (switch_id, in_port, mac)
        self.host_ip_table: Dict[str, Tuple[str, int, str]] = {}

    async def handle_packet_in(self, dp: Datapath, raw_data: bytes):
        """Dispatches incoming Packet-In messages."""
        pkt_in = parse_packet_in(raw_data)
        if not pkt_in or not pkt_in.data:
            return

        in_port = pkt_in.in_port if pkt_in.in_port is not None else 1
        eth = parse_ethernet(pkt_in.data)
        if not eth:
            return

        # 1. Handle LLDP packets for dynamic link discovery
        if eth.eth_type == ETH_TYPE_LLDP:
            self.topology_discovery.handle_lldp_packet(dp, in_port, eth.payload)
            return

        # 2. Host Learning
        src_mac = eth.src_mac
        src_sw = dp.sw_id
        
        # 3. Handle ARP packets
        if eth.eth_type == ETH_TYPE_ARP:
            arp = parse_arp(eth.payload)
            if arp:
                self.host_mac_table[src_mac] = (src_sw, in_port, arp.src_ip)
                self.host_ip_table[arp.src_ip] = (src_sw, in_port, src_mac)
                self.network_graph.add_host(f"h_{arp.src_ip}", src_sw, in_port, arp.src_ip, src_mac)
                
                await self._handle_arp(dp, in_port, eth, arp, pkt_in.buffer_id, pkt_in.data)
            return

        # 4. Handle IPv4 packets
        if eth.eth_type == ETH_TYPE_IP:
            ipv4 = parse_ipv4(eth.payload)
            if ipv4:
                self.host_mac_table[src_mac] = (src_sw, in_port, ipv4.src_ip)
                self.host_ip_table[ipv4.src_ip] = (src_sw, in_port, src_mac)
                
                await self._handle_ipv4(dp, in_port, eth, ipv4, pkt_in.buffer_id, pkt_in.data)
            return

    async def _handle_arp(
        self,
        dp: Datapath,
        in_port: int,
        eth: Any,
        arp: Any,
        buffer_id: int,
        raw_pkt: bytes,
    ):
        """Processes ARP request / reply."""
        # Opcode 1: Request, Opcode 2: Reply
        target_ip = arp.dst_ip
        
        # If target IP is already known, we can proxy-reply or forward directly
        if target_ip in self.host_ip_table:
            dst_sw, dst_port, dst_mac = self.host_ip_table[target_ip]
            
            if arp.opcode == 1:  # ARP Request -> Send direct ARP Reply
                reply_eth_hdr = str_to_mac(arp.src_mac) + str_to_mac(dst_mac) + struct.pack("!H", ETH_TYPE_ARP)
                reply_arp_hdr = struct.pack(
                    "!HHBBH6s4s6s4s",
                    1, 0x0800, 6, 4, 2,  # Opcode 2 (Reply)
                    str_to_mac(dst_mac), str_to_ip(target_ip),
                    str_to_mac(arp.src_mac), str_to_ip(arp.src_ip),
                )
                reply_pkt = reply_eth_hdr + reply_arp_hdr
                
                actions = build_action_output(in_port)
                pkt_out = build_packet_out(
                    buffer_id=0xffffffff,
                    in_port=OFPP_CONTROLLER,
                    actions=actions,
                    data=reply_pkt,
                )
                await dp.send_msg(pkt_out)
                return

        # Otherwise flood ARP out to discover target host
        actions = build_action_output(OFPP_FLOOD)
        pkt_out = build_packet_out(
            buffer_id=buffer_id,
            in_port=in_port,
            actions=actions,
            data=raw_pkt if buffer_id == 0xffffffff else b"",
        )
        await dp.send_msg(pkt_out)

    async def _handle_ipv4(
        self,
        dp: Datapath,
        in_port: int,
        eth: Any,
        ipv4: Any,
        buffer_id: int,
        raw_pkt: bytes,
    ):
        """Computes Dijkstra path and installs end-to-end OpenFlow rules."""
        src_sw = dp.sw_id
        dst_ip = ipv4.dst_ip
        src_ip = ipv4.src_ip
        
        # Check if destination host switch is known
        if dst_ip not in self.host_ip_table:
            # Destination not yet learned: flood or drop
            actions = build_action_output(OFPP_FLOOD)
            pkt_out = build_packet_out(
                buffer_id=buffer_id,
                in_port=in_port,
                actions=actions,
                data=raw_pkt if buffer_id == 0xffffffff else b"",
            )
            await dp.send_msg(pkt_out)
            return

        dst_sw, dst_host_port, dst_mac = self.host_ip_table[dst_ip]
        
        # 1. Local delivery on the same switch
        if src_sw == dst_sw:
            # Install flow rule on local switch
            match_kwargs = {"eth_type": ETH_TYPE_IP, "ipv4_dst": dst_ip}
            await self.flow_manager.install_flow(dp, match_kwargs, out_port=dst_host_port, priority=100)
            
            # Forward buffered packet
            actions = build_action_output(dst_host_port)
            pkt_out = build_packet_out(
                buffer_id=buffer_id,
                in_port=in_port,
                actions=actions,
                data=raw_pkt if buffer_id == 0xffffffff else b"",
            )
            await dp.send_msg(pkt_out)
            return

        # 2. Multi-hop delivery across switches via Dijkstra Routing
        path, cost = self.router.calculate_shortest_path(src_sw, dst_sw)
        if not path or len(path) < 2:
            log.warning(f"No reachable path from {src_sw} to {dst_sw}")
            return

        log.info(f"⚡ Dijkstra Path Computed: {' -> '.join(path)} (Cost: {cost:.4f}) for {src_ip} -> {dst_ip}")
        if self.event_manager:
            self.event_manager.emit(
                "routing_decision",
                {"src": src_sw, "dst": dst_sw, "path": path, "cost": cost, "traffic": f"{src_ip} -> {dst_ip}"},
            )

        # Build port hops along the path: (switch_id, in_port, out_port)
        port_hops: List[Tuple[str, int, int]] = []
        for i in range(len(path)):
            curr_sw = path[i]
            
            # Ingress switch
            if i == 0:
                next_sw = path[1]
                edge_data = self.network_graph.graph.get_edge_data(curr_sw, next_sw, default={})
                out_p = edge_data.get("src_port", 1)
                port_hops.append((curr_sw, in_port, out_p))
            # Egress switch
            elif i == len(path) - 1:
                prev_sw = path[i - 1]
                edge_data = self.network_graph.graph.get_edge_data(prev_sw, curr_sw, default={})
                in_p = edge_data.get("dst_port", 1)
                port_hops.append((curr_sw, in_p, dst_host_port))
            # Intermediate transit switch
            else:
                prev_sw = path[i - 1]
                next_sw = path[i + 1]
                edge_in = self.network_graph.graph.get_edge_data(prev_sw, curr_sw, default={})
                edge_out = self.network_graph.graph.get_edge_data(curr_sw, next_sw, default={})
                in_p = edge_in.get("dst_port", 1)
                out_p = edge_out.get("src_port", 1)
                port_hops.append((curr_sw, in_p, out_p))

        # Install flows on all switches along the path
        await self.flow_manager.install_path_forwarding(
            path=path,
            port_hops=port_hops,
            src_ip=src_ip,
            dst_ip=dst_ip,
            src_mac=eth.src_mac,
            dst_mac=dst_mac,
            priority=100,
            idle_timeout=60,
        )

        # Send initial packet out along first hop
        first_out_port = port_hops[0][2]
        actions = build_action_output(first_out_port)
        pkt_out = build_packet_out(
            buffer_id=buffer_id,
            in_port=in_port,
            actions=actions,
            data=raw_pkt if buffer_id == 0xffffffff else b"",
        )
        await dp.send_msg(pkt_out)
