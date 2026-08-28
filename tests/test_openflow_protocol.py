"""
Unit tests for OpenFlow 1.3 Protocol Encoders and Decoders
"""
import pytest
import struct
from controller.openflow.protocol import (
    OFP_VERSION,
    OFPT_HELLO,
    OFPT_FEATURES_REQUEST,
    OFPT_SET_CONFIG,
    OFPT_FLOW_MOD,
    OFPT_PACKET_OUT,
    OFPT_PACKET_IN,
    OFPFC_ADD,
    OFPP_CONTROLLER,
    OFPP_FLOOD,
    ETH_TYPE_IP,
    ETH_TYPE_ARP,
    ETH_TYPE_LLDP,
    build_hello,
    build_echo_reply,
    build_features_request,
    build_set_config,
    build_match,
    build_action_output,
    build_instruction_apply_actions,
    build_flow_mod,
    build_packet_out,
    build_port_stats_request,
    build_lldp_packet,
    parse_header,
    parse_packet_in,
    parse_port_stats_reply,
    parse_port_status,
    parse_ethernet,
    parse_arp,
    parse_ipv4,
    parse_lldp,
    str_to_mac,
    mac_to_str,
    str_to_ip,
    ip_to_str,
)


def test_header_and_hello():
    hello_bytes = build_hello(xid=42)
    hdr = parse_header(hello_bytes)
    assert hdr is not None
    assert hdr.version == OFP_VERSION
    assert hdr.msg_type == OFPT_HELLO
    assert hdr.length == 8
    assert hdr.xid == 42


def test_mac_and_ip_conversion():
    mac_str = "00:00:00:00:00:01"
    mac_bytes = str_to_mac(mac_str)
    assert len(mac_bytes) == 6
    assert mac_to_str(mac_bytes) == mac_str

    ip_str = "10.0.0.1"
    ip_bytes = str_to_ip(ip_str)
    assert len(ip_bytes) == 4
    assert ip_to_str(ip_bytes) == ip_str


def test_match_and_flow_mod():
    match_bytes = build_match(
        in_port=1,
        eth_dst="00:00:00:00:00:02",
        eth_type=ETH_TYPE_IP,
        ipv4_dst="10.0.0.2",
    )
    assert len(match_bytes) % 8 == 0  # 8-byte aligned

    actions = build_action_output(port=2)
    instructions = build_instruction_apply_actions(actions)
    assert len(instructions) % 8 == 0

    flow_mod = build_flow_mod(
        priority=100,
        command=OFPFC_ADD,
        match=match_bytes,
        instructions=instructions,
        xid=10,
    )
    hdr = parse_header(flow_mod)
    assert hdr is not None
    assert hdr.msg_type == OFPT_FLOW_MOD
    assert hdr.xid == 10
    assert hdr.length == len(flow_mod)


def test_packet_out():
    actions = build_action_output(port=OFPP_FLOOD)
    payload = b"\x00" * 64
    pkt_out = build_packet_out(
        buffer_id=0xffffffff,
        in_port=OFPP_CONTROLLER,
        actions=actions,
        data=payload,
        xid=99,
    )
    hdr = parse_header(pkt_out)
    assert hdr is not None
    assert hdr.msg_type == OFPT_PACKET_OUT
    assert hdr.xid == 99


def test_port_stats_request():
    req = build_port_stats_request(port_no=1, xid=5)
    hdr = parse_header(req)
    assert hdr is not None
    assert hdr.length == 24


def test_lldp_packet_serialization_and_deserialization():
    lldp_pkt = build_lldp_packet(dpid=1, port_no=2, system_name="SDN-ITE")
    eth = parse_ethernet(lldp_pkt)
    assert eth is not None
    assert eth.eth_type == ETH_TYPE_LLDP
    assert eth.dst_mac == "01:80:c2:00:00:0e"

    parsed_lldp = parse_lldp(eth.payload)
    assert parsed_lldp is not None
    assert parsed_lldp.src_dpid == 1
    assert parsed_lldp.src_port == 2


def test_arp_and_ipv4_parsing():
    # Build synthetic Ethernet + ARP packet
    src_mac = b"\x00\x00\x00\x00\x00\x01"
    dst_mac = b"\xff\xff\xff\xff\xff\xff"
    eth_hdr = dst_mac + src_mac + struct.pack("!H", ETH_TYPE_ARP)
    arp_body = struct.pack(
        "!HHBBH6s4s6s4s",
        1, 0x0800, 6, 4, 1,
        src_mac, str_to_ip("10.0.0.1"),
        b"\x00" * 6, str_to_ip("10.0.0.2"),
    )
    raw_pkt = eth_hdr + arp_body

    eth = parse_ethernet(raw_pkt)
    assert eth is not None
    assert eth.eth_type == ETH_TYPE_ARP
    
    arp = parse_arp(eth.payload)
    assert arp is not None
    assert arp.src_ip == "10.0.0.1"
    assert arp.dst_ip == "10.0.0.2"
    assert arp.opcode == 1


def test_arp_match_building():
    match_bytes = build_match(
        eth_type=ETH_TYPE_ARP,
        arp_op=1,
        arp_spa="10.0.0.1",
        arp_tpa="10.0.0.7",
    )
    assert len(match_bytes) % 8 == 0
    assert len(match_bytes) > 4
