"""
Comprehensive Integration tests for SDN-ITE OpenFlow 1.3 Controller Server
"""
import pytest
import asyncio
import struct
from controller.app import SDNTrafficEngineApp
from controller.openflow.protocol import (
    OFP_VERSION,
    OFPT_HELLO,
    OFPT_FEATURES_REQUEST,
    OFPT_FEATURES_REPLY,
    OFPT_SET_CONFIG,
    OFPT_FLOW_MOD,
    OFPT_PACKET_IN,
    OFPT_PACKET_OUT,
    OFPT_MULTIPART_REPLY,
    OFPT_PORT_STATUS,
    OFPMP_PORT_STATS,
    OFPPR_DELETE,
    ETH_TYPE_ARP,
    ETH_TYPE_IP,
    build_hello,
    build_match,
    build_flow_mod,
    parse_header,
    str_to_mac,
    str_to_ip,
)


def test_controller_handshake_and_table_miss():
    async def run_test():
        app = SDNTrafficEngineApp()
        test_port = 6698
        
        await app.switch_manager.start_server(host="127.0.0.1", port=test_port)
        
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", test_port)
            
            # 1. Receive Controller HELLO
            ctrl_hello_bytes = await reader.readexactly(8)
            ctrl_hello = parse_header(ctrl_hello_bytes)
            assert ctrl_hello is not None
            assert ctrl_hello.msg_type == OFPT_HELLO
            
            # 2. Send Switch HELLO
            writer.write(build_hello(xid=100))
            await writer.drain()
            
            # 3. Receive FEATURES_REQUEST
            feat_req_bytes = await reader.readexactly(8)
            feat_req = parse_header(feat_req_bytes)
            assert feat_req is not None
            assert feat_req.msg_type == OFPT_FEATURES_REQUEST
            
            # 4. Send FEATURES_REPLY (DPID = 1, tables=254)
            dpid = 1
            n_buffers = 256
            n_tables = 254
            capabilities = 0x4f
            body = struct.pack("!QIBB2sI", dpid, n_buffers, n_tables, 0, b"\x00\x00", capabilities)
            hdr = struct.pack("!BBHI", OFP_VERSION, OFPT_FEATURES_REPLY, 8 + len(body), feat_req.xid)
            writer.write(hdr + body)
            await writer.drain()
            
            # 5. Receive SET_CONFIG
            set_cfg_bytes = await reader.readexactly(12)
            set_cfg_hdr = parse_header(set_cfg_bytes)
            assert set_cfg_hdr is not None
            assert set_cfg_hdr.msg_type == OFPT_SET_CONFIG
            
            # 6. Receive Table-Miss FLOW_MOD
            flow_mod_hdr_bytes = await reader.readexactly(8)
            flow_mod_hdr = parse_header(flow_mod_hdr_bytes)
            assert flow_mod_hdr is not None
            assert flow_mod_hdr.msg_type == OFPT_FLOW_MOD
            
            flow_mod_body = await reader.readexactly(flow_mod_hdr.length - 8)
            assert len(flow_mod_body) > 0
            
            await asyncio.sleep(0.05)
            
            assert 1 in app.switch_manager.datapaths
            dp = app.switch_manager.datapaths[1]
            assert dp.sw_id == "s1"
            assert dp.dpid == 1
            
            writer.close()
            await writer.wait_closed()
            
        finally:
            await app.switch_manager.stop_server()

    asyncio.run(run_test())


def test_packet_in_arp_learning_and_ipv4_forwarding():
    async def run_test():
        app = SDNTrafficEngineApp()
        app.initialize_mesh_topology()
        test_port = 6697
        
        await app.switch_manager.start_server(host="127.0.0.1", port=test_port)
        
        try:
            # Connect switch S1
            r1, w1 = await asyncio.open_connection("127.0.0.1", test_port)
            await r1.readexactly(8)  # HELLO
            w1.write(build_hello(xid=1))
            await w1.drain()
            req1 = parse_header(await r1.readexactly(8))
            assert req1 is not None
            body1 = struct.pack("!QIBB2sI", 1, 256, 254, 0, b"\x00\x00", 0x4f)
            w1.write(struct.pack("!BBHI", OFP_VERSION, OFPT_FEATURES_REPLY, 8 + len(body1), req1.xid) + body1)
            await w1.drain()
            await r1.readexactly(12)  # SET_CONFIG
            fmod1 = parse_header(await r1.readexactly(8))
            assert fmod1 is not None
            await r1.readexactly(fmod1.length - 8)  # Table miss
            
            # Connect switch S7
            r7, w7 = await asyncio.open_connection("127.0.0.1", test_port)
            await r7.readexactly(8)
            w7.write(build_hello(xid=1))
            await w7.drain()
            req7 = parse_header(await r7.readexactly(8))
            assert req7 is not None
            body7 = struct.pack("!QIBB2sI", 7, 256, 254, 0, b"\x00\x00", 0x4f)
            w7.write(struct.pack("!BBHI", OFP_VERSION, OFPT_FEATURES_REPLY, 8 + len(body7), req7.xid) + body7)
            await w7.drain()
            await r7.readexactly(12)
            fmod7 = parse_header(await r7.readexactly(8))
            assert fmod7 is not None
            await r7.readexactly(fmod7.length - 8)
            
            await asyncio.sleep(0.05)
            
            # 1. Host 1 on S1 sends ARP Packet-In
            src_mac = b"\x00\x00\x00\x00\x00\x01"
            dst_mac = b"\xff\xff\xff\xff\xff\xff"
            eth_hdr = dst_mac + src_mac + struct.pack("!H", ETH_TYPE_ARP)
            arp_body = struct.pack(
                "!HHBBH6s4s6s4s",
                1, 0x0800, 6, 4, 1,
                src_mac, str_to_ip("10.0.0.1"),
                b"\x00" * 6, str_to_ip("10.0.0.7"),
            )
            raw_arp = eth_hdr + arp_body
            
            # Build Packet-In message for S1 (Host 1 on Edge Port 3)
            match_in_port = build_match(in_port=3)
            pin_hdr = struct.pack("!BBHI", OFP_VERSION, OFPT_PACKET_IN, 8 + 16 + len(match_in_port) + 2 + len(raw_arp), 50)
            pin_body = struct.pack("!IHBBQ", 0xffffffff, len(raw_arp), 0, 0, 0)
            
            dp1 = app.switch_manager.datapaths[1]
            await app.packet_handler.handle_packet_in(dp1, pin_hdr + pin_body + match_in_port + b"\x00\x00" + raw_arp)
            
            # Check host learning
            assert "10.0.0.1" in app.packet_handler.host_ip_table
            assert app.packet_handler.host_ip_table["10.0.0.1"][0] == "s1"
            assert app.packet_handler.host_ip_table["10.0.0.1"][1] == 3
            
            # 2. Host 7 on S7 sends ARP Packet-In (Host 7 on Edge Port 4)
            src_mac7 = b"\x00\x00\x00\x00\x00\x07"
            eth_hdr7 = dst_mac + src_mac7 + struct.pack("!H", ETH_TYPE_ARP)
            arp_body7 = struct.pack(
                "!HHBBH6s4s6s4s",
                1, 0x0800, 6, 4, 1,
                src_mac7, str_to_ip("10.0.0.7"),
                b"\x00" * 6, str_to_ip("10.0.0.1"),
            )
            raw_arp7 = eth_hdr7 + arp_body7
            match_in_port7 = build_match(in_port=4)
            pin_hdr7 = struct.pack("!BBHI", OFP_VERSION, OFPT_PACKET_IN, 8 + 16 + len(match_in_port7) + 2 + len(raw_arp7), 51)
            dp7 = app.switch_manager.datapaths[7]
            await app.packet_handler.handle_packet_in(dp7, pin_hdr7 + pin_body + match_in_port7 + b"\x00\x00" + raw_arp7)
            
            assert "10.0.0.7" in app.packet_handler.host_ip_table
            assert app.packet_handler.host_ip_table["10.0.0.7"][0] == "s7"
            assert app.packet_handler.host_ip_table["10.0.0.7"][1] == 4
            
            # 3. Host 1 sends IPv4 Packet-In towards Host 7
            ip_data = b"\x45\x00\x00\x54\x00\x01\x00\x00\x40\x01\x00\x00" + str_to_ip("10.0.0.1") + str_to_ip("10.0.0.7") + (b"\x00" * 64)
            ip_eth = str_to_mac("00:00:00:00:00:07") + str_to_mac("00:00:00:00:00:01") + struct.pack("!H", ETH_TYPE_IP)
            raw_ip = ip_eth + ip_data
            
            await app.packet_handler.handle_packet_in(dp1, pin_hdr + pin_body + match_in_port + b"\x00\x00" + raw_ip)
            
            # Assert flow table was populated
            assert len(app.flow_manager.active_flows) > 0
            
            w1.close()
            w7.close()
            await w1.wait_closed()
            await w7.wait_closed()
            
        finally:
            await app.switch_manager.stop_server()

    asyncio.run(run_test())


def test_port_stats_and_congestion_trigger():
    app = SDNTrafficEngineApp()
    app.initialize_mesh_topology()
    
    # Create fake datapath
    class FakeDP:
        dpid = 1
        sw_id = "s1"
        ports = {1: {}}
        is_active = True
        
    dp = FakeDP()
    
    # Send initial port stats sample (time 0)
    entry1 = struct.pack("!I4sQQQQQQQQQQQQII", 1, b"\x00"*4, 1000, 1000, 1_000_000, 1_000_000, 0, 0, 0, 0, 0, 0, 0, 0, 10, 0)
    mp_hdr = struct.pack("!BBHI", OFP_VERSION, OFPT_MULTIPART_REPLY, 8 + 8 + len(entry1), 1)
    body1 = struct.pack("!HH4s", OFPMP_PORT_STATS, 0, b"\x00"*4) + entry1
    
    app.stats_manager.handle_port_stats_reply(dp, mp_hdr + body1)
    
    # Mock previous timestamp to 1 second prior to simulate high 90 Mbps throughput
    now_key = (1, 1)
    if now_key in app.stats_manager.prev_stats:
        t, rxb, txb, rxp, txp = app.stats_manager.prev_stats[now_key]
        app.stats_manager.prev_stats[now_key] = (t - 1.0, rxb, txb, rxp, txp)
        
    # Send second port stats sample with +11.25 MB (90 Mbps on 100 Mbps link = 90% utilization)
    entry2 = struct.pack("!I4sQQQQQQQQQQQQII", 1, b"\x00"*4, 2000, 2000, 1_000_000, 1_000_000 + 11_250_000, 0, 50, 0, 0, 0, 0, 0, 0, 11, 0)
    body2 = struct.pack("!HH4s", OFPMP_PORT_STATS, 0, b"\x00"*4) + entry2
    
    # Trigger 3 cycles to satisfy hysteresis persistence
    for _ in range(3):
        app.stats_manager.handle_port_stats_reply(dp, mp_hdr + body2)
        
    assert "s1-s2" in app.stats_manager.link_metrics
    metrics = app.stats_manager.link_metrics["s1-s2"]
    assert metrics["utilization_pct"] >= 85.0
