"""
OpenFlow 1.3 Protocol Encoders, Decoders, and Data Structures
Compliant with OpenFlow Switch Specification Version 1.3.5 (Protocol 0x04)
"""
import struct
import socket
from typing import Dict, List, Tuple, Optional, Any, NamedTuple

# OpenFlow 1.3 Protocol Version
OFP_VERSION = 0x04

# Message Types
OFPT_HELLO = 0
OFPT_ERROR = 1
OFPT_ECHO_REQUEST = 2
OFPT_ECHO_REPLY = 3
OFPT_EXPERIMENTER = 4
OFPT_FEATURES_REQUEST = 5
OFPT_FEATURES_REPLY = 6
OFPT_GET_CONFIG_REQUEST = 7
OFPT_GET_CONFIG_REPLY = 8
OFPT_SET_CONFIG = 9
OFPT_PACKET_IN = 10
OFPT_FLOW_REMOVED = 11
OFPT_PORT_STATUS = 12
OFPT_PACKET_OUT = 13
OFPT_FLOW_MOD = 14
OFPT_GROUP_MOD = 15
OFPT_PORT_MOD = 16
OFPT_TABLE_MOD = 17
OFPT_MULTIPART_REQUEST = 18
OFPT_MULTIPART_REPLY = 19
OFPT_BARRIER_REQUEST = 20
OFPT_BARRIER_REPLY = 21

# Special Port Numbers
OFPP_MAX = 0xffffff00
OFPP_IN_PORT = 0xfffffff8
OFPP_TABLE = 0xfffffff9
OFPP_NORMAL = 0xfffffffa
OFPP_FLOOD = 0xfffffffb
OFPP_ALL = 0xfffffffc
OFPP_CONTROLLER = 0xfffffffd
OFPP_LOCAL = 0xfffffffe
OFPP_ANY = 0xffffffff

# Flow Mod Commands
OFPFC_ADD = 0
OFPFC_MODIFY = 1
OFPFC_MODIFY_STRICT = 2
OFPFC_DELETE = 3
OFPFC_DELETE_STRICT = 4

# Flow Mod Flags
OFPFF_SEND_FLOW_REM = 1 << 0
OFPFF_CHECK_OVERLAP = 1 << 1
OFPFF_RESET_COUNTS = 1 << 2
OFPFF_NO_PKT_COUNTS = 1 << 3
OFPFF_NO_BYT_COUNTS = 1 << 4

# Multipart / Stats Types
OFPMP_DESC = 0
OFPMP_FLOW = 1
OFPMP_AGGREGATE = 2
OFPMP_TABLE = 3
OFPMP_PORT_STATS = 4
OFPMP_QUEUE = 5
OFPMP_GROUP = 6
OFPMP_PORT_DESC = 13

# Instructions
OFPIT_GOTO_TABLE = 1
OFPIT_WRITE_METADATA = 2
OFPIT_WRITE_ACTIONS = 3
OFPIT_APPLY_ACTIONS = 4
OFPIT_CLEAR_ACTIONS = 5
OFPIT_METER = 6

# Actions
OFPAT_OUTPUT = 0
OFPAT_COPY_TTL_OUT = 11
OFPAT_COPY_TTL_IN = 12
OFPAT_SET_MPLS_TTL = 15
OFPAT_DEC_MPLS_TTL = 16
OFPAT_PUSH_VLAN = 17
OFPAT_POP_VLAN = 18
OFPAT_PUSH_MPLS = 19
OFPAT_POP_MPLS = 20
OFPAT_SET_QUEUE = 21
OFPAT_GROUP = 22
OFPAT_SET_NW_TTL = 23
OFPAT_DEC_NW_TTL = 24
OFPAT_SET_FIELD = 25
OFPAT_PUSH_PBB = 26
OFPAT_POP_PBB = 27

# OXM Match Classes
OFPXMC_OPENFLOW_BASIC = 0x8000

# OXM Match Fields
OFPXMT_OFB_IN_PORT = 0
OFPXMT_OFB_IN_PHY_PORT = 1
OFPXMT_OFB_METADATA = 2
OFPXMT_OFB_ETH_DST = 3
OFPXMT_OFB_ETH_SRC = 4
OFPXMT_OFB_ETH_TYPE = 5
OFPXMT_OFB_VLAN_VID = 6
OFPXMT_OFB_VLAN_PCP = 7
OFPXMT_OFB_IP_DSCP = 8
OFPXMT_OFB_IP_ECN = 9
OFPXMT_OFB_IP_PROTO = 10
OFPXMT_OFB_IPV4_SRC = 11
OFPXMT_OFB_IPV4_DST = 12
OFPXMT_OFB_TCP_SRC = 13
OFPXMT_OFB_TCP_DST = 14
OFPXMT_OFB_UDP_SRC = 15
OFPXMT_OFB_UDP_DST = 16
OFPXMT_OFB_SCTP_SRC = 17
OFPXMT_OFB_SCTP_DST = 18
OFPXMT_OFB_ICMPV4_TYPE = 19
OFPXMT_OFB_ICMPV4_CODE = 20
OFPXMT_OFB_ARP_OP = 21
OFPXMT_OFB_ARP_SPA = 22
OFPXMT_OFB_ARP_TPA = 23
OFPXMT_OFB_ARP_SHA = 24
OFPXMT_OFB_ARP_THA = 25

# Ethernet Constants
ETH_TYPE_IP = 0x0800
ETH_TYPE_ARP = 0x0806
ETH_TYPE_LLDP = 0x88CC

# Port Status Reasons
OFPPR_ADD = 0
OFPPR_DELETE = 1
OFPPR_MODIFY = 2


def mac_to_str(mac_bytes: bytes) -> str:
    """Formats 6-byte MAC into colon-separated hex."""
    return ":".join(f"{b:02x}" for b in mac_bytes)


def str_to_mac(mac_str: str) -> bytes:
    """Parses colon-separated hex into 6-byte MAC."""
    return bytes(int(x, 16) for x in mac_str.split(":"))


def ip_to_str(ip_bytes: bytes) -> str:
    """Formats 4-byte IPv4 into dotted decimal."""
    return socket.inet_ntoa(ip_bytes)


def str_to_ip(ip_str: str) -> bytes:
    """Parses dotted decimal IPv4 into 4 bytes."""
    return socket.inet_aton(ip_str)


# ==============================================================================
# OpenFlow Message Headers & Base Builders
# ==============================================================================

class OFPHeader(NamedTuple):
    version: int
    msg_type: int
    length: int
    xid: int


def parse_header(data: bytes) -> Optional[OFPHeader]:
    """Parses standard 8-byte OpenFlow header."""
    if len(data) < 8:
        return None
    version, msg_type, length, xid = struct.unpack("!BBHI", data[:8])
    return OFPHeader(version, msg_type, length, xid)


def build_header(msg_type: int, length: int, xid: int = 1) -> bytes:
    """Builds standard 8-byte OpenFlow 1.3 header."""
    return struct.pack("!BBHI", OFP_VERSION, msg_type, length, xid)


def build_hello(xid: int = 1) -> bytes:
    """Constructs OFPT_HELLO message."""
    return build_header(OFPT_HELLO, 8, xid)


def build_echo_reply(xid: int, payload: bytes = b"") -> bytes:
    """Constructs OFPT_ECHO_REPLY message."""
    hdr = build_header(OFPT_ECHO_REPLY, 8 + len(payload), xid)
    return hdr + payload


def build_features_request(xid: int = 1) -> bytes:
    """Constructs OFPT_FEATURES_REQUEST message."""
    return build_header(OFPT_FEATURES_REQUEST, 8, xid)


def build_get_config_request(xid: int = 1) -> bytes:
    """Constructs OFPT_GET_CONFIG_REQUEST message."""
    return build_header(OFPT_GET_CONFIG_REQUEST, 8, xid)


def build_set_config(flags: int = 0, miss_send_len: int = 0xffff, xid: int = 1) -> bytes:
    """Constructs OFPT_SET_CONFIG message (12 bytes)."""
    hdr = build_header(OFPT_SET_CONFIG, 12, xid)
    return hdr + struct.pack("!HH", flags, miss_send_len)


# ==============================================================================
# OXM (OpenFlow Extensible Match) Serializers
# ==============================================================================

def make_oxm_header(oxm_class: int, field: int, has_mask: bool, length: int) -> int:
    mask_bit = 1 if has_mask else 0
    return (oxm_class << 16) | (field << 9) | (mask_bit << 8) | length


def build_oxm_in_port(port: int) -> bytes:
    hdr = make_oxm_header(OFPXMC_OPENFLOW_BASIC, OFPXMT_OFB_IN_PORT, False, 4)
    return struct.pack("!II", hdr, port)


def build_oxm_eth_src(mac_bytes: bytes) -> bytes:
    hdr = make_oxm_header(OFPXMC_OPENFLOW_BASIC, OFPXMT_OFB_ETH_SRC, False, 6)
    return struct.pack("!I", hdr) + mac_bytes


def build_oxm_eth_dst(mac_bytes: bytes) -> bytes:
    hdr = make_oxm_header(OFPXMC_OPENFLOW_BASIC, OFPXMT_OFB_ETH_DST, False, 6)
    return struct.pack("!I", hdr) + mac_bytes


def build_oxm_eth_type(eth_type: int) -> bytes:
    hdr = make_oxm_header(OFPXMC_OPENFLOW_BASIC, OFPXMT_OFB_ETH_TYPE, False, 2)
    return struct.pack("!IH", hdr, eth_type)


def build_oxm_ip_proto(proto: int) -> bytes:
    hdr = make_oxm_header(OFPXMC_OPENFLOW_BASIC, OFPXMT_OFB_IP_PROTO, False, 1)
    return struct.pack("!IB", hdr, proto)


def build_oxm_ipv4_src(ip_bytes: bytes) -> bytes:
    hdr = make_oxm_header(OFPXMC_OPENFLOW_BASIC, OFPXMT_OFB_IPV4_SRC, False, 4)
    return struct.pack("!I", hdr) + ip_bytes


def build_oxm_ipv4_dst(ip_bytes: bytes) -> bytes:
    hdr = make_oxm_header(OFPXMC_OPENFLOW_BASIC, OFPXMT_OFB_IPV4_DST, False, 4)
    return struct.pack("!I", hdr) + ip_bytes


def build_oxm_tcp_src(port: int) -> bytes:
    hdr = make_oxm_header(OFPXMC_OPENFLOW_BASIC, OFPXMT_OFB_TCP_SRC, False, 2)
    return struct.pack("!IH", hdr, port)


def build_oxm_tcp_dst(port: int) -> bytes:
    hdr = make_oxm_header(OFPXMC_OPENFLOW_BASIC, OFPXMT_OFB_TCP_DST, False, 2)
    return struct.pack("!IH", hdr, port)


def build_oxm_udp_src(port: int) -> bytes:
    hdr = make_oxm_header(OFPXMC_OPENFLOW_BASIC, OFPXMT_OFB_UDP_SRC, False, 2)
    return struct.pack("!IH", hdr, port)


def build_oxm_udp_dst(port: int) -> bytes:
    hdr = make_oxm_header(OFPXMC_OPENFLOW_BASIC, OFPXMT_OFB_UDP_DST, False, 2)
    return struct.pack("!IH", hdr, port)


def build_match(
    in_port: Optional[int] = None,
    eth_src: Optional[str] = None,
    eth_dst: Optional[str] = None,
    eth_type: Optional[int] = None,
    ip_proto: Optional[int] = None,
    ipv4_src: Optional[str] = None,
    ipv4_dst: Optional[str] = None,
    tcp_src: Optional[int] = None,
    tcp_dst: Optional[int] = None,
    udp_src: Optional[int] = None,
    udp_dst: Optional[int] = None,
) -> bytes:
    """
    Constructs an OFPMatch structure (OFPMT_OXM = 1) with 8-byte alignment padding.
    """
    oxm_fields = bytearray()
    if in_port is not None:
        oxm_fields.extend(build_oxm_in_port(in_port))
    if eth_src:
        oxm_fields.extend(build_oxm_eth_src(str_to_mac(eth_src)))
    if eth_dst:
        oxm_fields.extend(build_oxm_eth_dst(str_to_mac(eth_dst)))
    if eth_type is not None:
        oxm_fields.extend(build_oxm_eth_type(eth_type))
    if ip_proto is not None:
        oxm_fields.extend(build_oxm_ip_proto(ip_proto))
    if ipv4_src:
        oxm_fields.extend(build_oxm_ipv4_src(str_to_ip(ipv4_src)))
    if ipv4_dst:
        oxm_fields.extend(build_oxm_ipv4_dst(str_to_ip(ipv4_dst)))
    if tcp_src is not None:
        oxm_fields.extend(build_oxm_tcp_src(tcp_src))
    if tcp_dst is not None:
        oxm_fields.extend(build_oxm_tcp_dst(tcp_dst))
    if udp_src is not None:
        oxm_fields.extend(build_oxm_udp_src(udp_src))
    if udp_dst is not None:
        oxm_fields.extend(build_oxm_udp_dst(udp_dst))

    oxm_len = len(oxm_fields)
    match_len = 4 + oxm_len
    # Pad to 8 bytes
    padded_len = (match_len + 7) & ~7
    pad_bytes = bytes(padded_len - match_len)
    
    # type=1 (OFPMT_OXM), length=match_len
    return struct.pack("!HH", 1, match_len) + bytes(oxm_fields) + pad_bytes


# ==============================================================================
# Instructions & Actions Builders
# ==============================================================================

def build_action_output(port: int, max_len: int = 0xffff) -> bytes:
    """Builds OFPAT_OUTPUT (16 bytes)."""
    # type=0, len=16, port, max_len, pad(6)
    return struct.pack("!HHIH6s", OFPAT_OUTPUT, 16, port, max_len, b"\x00" * 6)


def build_instruction_apply_actions(actions: bytes) -> bytes:
    """Builds OFPIT_APPLY_ACTIONS containing the given serialized actions."""
    inst_len = 8 + len(actions)
    # Pad to 8 bytes
    padded_len = (inst_len + 7) & ~7
    pad = bytes(padded_len - inst_len)
    # type=4, len=padded_len, pad(4)
    return struct.pack("!HHI", OFPIT_APPLY_ACTIONS, padded_len, 0) + actions + pad


# ==============================================================================
# Flow Mod Builder (OFPT_FLOW_MOD)
# ==============================================================================

def build_flow_mod(
    cookie: int = 0,
    cookie_mask: int = 0,
    table_id: int = 0,
    command: int = OFPFC_ADD,
    idle_timeout: int = 0,
    hard_timeout: int = 0,
    priority: int = 32768,
    buffer_id: int = 0xffffffff,
    out_port: int = OFPP_ANY,
    out_group: int = 0xffffffff,
    flags: int = 0,
    match: Optional[bytes] = None,
    instructions: Optional[bytes] = None,
    xid: int = 1,
) -> bytes:
    """
    Constructs a complete OpenFlow 1.3 OFPT_FLOW_MOD message.
    """
    if match is None:
        match = build_match()  # Empty wild-card match
    if instructions is None:
        instructions = b""

    fixed_body = struct.pack(
        "!QQBBHHHIIIH2s",
        cookie,
        cookie_mask,
        table_id,
        command,
        idle_timeout,
        hard_timeout,
        priority,
        buffer_id,
        out_port,
        out_group,
        flags,
        b"\x00\x00"  # pad
    )

    total_len = 8 + len(fixed_body) + len(match) + len(instructions)
    hdr = build_header(OFPT_FLOW_MOD, total_len, xid)

    return hdr + fixed_body + match + instructions


# ==============================================================================
# Packet Out Builder (OFPT_PACKET_OUT)
# ==============================================================================

def build_packet_out(
    buffer_id: int = 0xffffffff,
    in_port: int = OFPP_CONTROLLER,
    actions: Optional[bytes] = None,
    data: bytes = b"",
    xid: int = 1,
) -> bytes:
    """
    Constructs a complete OpenFlow 1.3 OFPT_PACKET_OUT message.
    """
    if actions is None:
        actions = b""
    
    actions_len = len(actions)
    total_len = 8 + 16 + actions_len + len(data)
    hdr = build_header(OFPT_PACKET_OUT, total_len, xid)
    body = struct.pack("!IIH6s", buffer_id, in_port, actions_len, b"\x00" * 6)
    return hdr + body + actions + data


# ==============================================================================
# Multipart / Statistics Request Builders
# ==============================================================================

def build_port_stats_request(port_no: int = OFPP_ANY, xid: int = 1) -> bytes:
    """Constructs OFPMP_PORT_STATS multipart request."""
    # OFPMP_PORT_STATS body is 8 bytes: port_no (4 bytes), pad (4 bytes)
    total_len = 8 + 8 + 8  # header(8) + multipart_hdr(8) + body(8) = 24
    hdr = build_header(OFPT_MULTIPART_REQUEST, total_len, xid)
    mp_hdr = struct.pack("!HH4s", OFPMP_PORT_STATS, 0, b"\x00" * 4)
    body = struct.pack("!I4s", port_no, b"\x00" * 4)
    return hdr + mp_hdr + body


def build_flow_stats_request(
    table_id: int = 0xff,
    out_port: int = OFPP_ANY,
    out_group: int = 0xffffffff,
    cookie: int = 0,
    cookie_mask: int = 0,
    match: Optional[bytes] = None,
    xid: int = 1,
) -> bytes:
    """Constructs OFPMP_FLOW multipart request."""
    if match is None:
        match = build_match()
    body_len = 32 + len(match)
    total_len = 8 + 8 + body_len
    hdr = build_header(OFPT_MULTIPART_REQUEST, total_len, xid)
    mp_hdr = struct.pack("!HH4s", OFPMP_FLOW, 0, b"\x00" * 4)
    body = struct.pack(
        "!BB2sII4sQQ",
        table_id,
        0,  # pad
        b"\x00\x00",
        out_port,
        out_group,
        b"\x00" * 4,
        cookie,
        cookie_mask,
    )
    return hdr + mp_hdr + body + match


# ==============================================================================
# Decoders: Packet-In, Features-Reply, Port-Stats, Port-Status
# ==============================================================================

class DecodedPacketIn(NamedTuple):
    buffer_id: int
    total_len: int
    reason: int
    table_id: int
    cookie: int
    in_port: Optional[int]
    data: bytes


def parse_packet_in(data: bytes) -> Optional[DecodedPacketIn]:
    """Parses OFPT_PACKET_IN payload."""
    if len(data) < 24:
        return None
    
    # 8-byte header was already parsed
    buffer_id, total_len, reason, table_id, cookie = struct.unpack(
        "!IHBBQ", data[8:24]
    )
    
    offset = 24
    in_port = None
    if len(data) > offset + 4:
        match_type, match_len = struct.unpack("!HH", data[offset:offset+4])
        oxm_data = data[offset+4 : offset+match_len]
        padded_match_len = (match_len + 7) & ~7
        offset += padded_match_len + 2  # skip match + 2-byte pad
        
        # Parse OXM for in_port
        idx = 0
        while idx + 4 <= len(oxm_data):
            oxm_hdr = struct.unpack("!I", oxm_data[idx:idx+4])[0]
            oxm_class = (oxm_hdr >> 16) & 0xffff
            field = (oxm_hdr >> 9) & 0x7f
            length = oxm_hdr & 0xff
            idx += 4
            if oxm_class == OFPXMC_OPENFLOW_BASIC and field == OFPXMT_OFB_IN_PORT and length == 4:
                if idx + 4 <= len(oxm_data):
                    in_port = struct.unpack("!I", oxm_data[idx:idx+4])[0]
            idx += length

    pkt_data = data[offset:]
    return DecodedPacketIn(buffer_id, total_len, reason, table_id, cookie, in_port, pkt_data)


class DecodedPortStats(NamedTuple):
    port_no: int
    rx_packets: int
    tx_packets: int
    rx_bytes: int
    tx_bytes: int
    rx_dropped: int
    tx_dropped: int
    rx_errors: int
    tx_errors: int
    duration_sec: int
    duration_nsec: int


def parse_port_stats_reply(data: bytes) -> List[DecodedPortStats]:
    """Parses OFPT_MULTIPART_REPLY of type OFPMP_PORT_STATS."""
    stats_list = []
    # Header(8) + MultipartHdr(8) = 16 bytes offset
    if len(data) < 16:
        return stats_list
    
    offset = 16
    entry_size = 112
    while offset + entry_size <= len(data):
        entry = data[offset : offset + entry_size]
        (
            port_no,
            _,  # pad 4
            rx_packets,
            tx_packets,
            rx_bytes,
            tx_bytes,
            rx_dropped,
            tx_dropped,
            rx_errors,
            tx_errors,
            _,  # rx_frame_err
            _,  # rx_over_err
            _,  # rx_crc_err
            _,  # collisions
            duration_sec,
            duration_nsec,
        ) = struct.unpack("!I4sQQQQQQQQQQQQII", entry)
        
        if port_no <= OFPP_MAX:
            stats_list.append(
                DecodedPortStats(
                    port_no,
                    rx_packets,
                    tx_packets,
                    rx_bytes,
                    tx_bytes,
                    rx_dropped,
                    tx_dropped,
                    rx_errors,
                    tx_errors,
                    duration_sec,
                    duration_nsec,
                )
            )
        offset += entry_size
        
    return stats_list


class DecodedPortStatus(NamedTuple):
    reason: int
    port_no: int
    hw_addr: str
    name: str
    config: int
    state: int


def parse_port_status(data: bytes) -> Optional[DecodedPortStatus]:
    """Parses OFPT_PORT_STATUS message."""
    if len(data) < 80:
        return None
    
    reason = data[8]
    # port desc begins at offset 16 (8 hdr + 8 pad/reason)
    port_data = data[16:80]
    port_no, _, hw_addr_b, _, name_b, config, state = struct.unpack(
        "!I4s6s2s16sII", port_data[:40]
    )
    hw_addr = mac_to_str(hw_addr_b)
    name = name_b.decode("utf-8", errors="ignore").rstrip("\x00")
    return DecodedPortStatus(reason, port_no, hw_addr, name, config, state)


# ==============================================================================
# Packet Parsers: Ethernet, ARP, IPv4, LLDP
# ==============================================================================

class ParsedEthernet(NamedTuple):
    dst_mac: str
    src_mac: str
    eth_type: int
    payload: bytes


def parse_ethernet(data: bytes) -> Optional[ParsedEthernet]:
    """Parses 14-byte Ethernet frame."""
    if len(data) < 14:
        return None
    dst_mac = mac_to_str(data[0:6])
    src_mac = mac_to_str(data[6:12])
    eth_type = struct.unpack("!H", data[12:14])[0]
    return ParsedEthernet(dst_mac, src_mac, eth_type, data[14:])


class ParsedARP(NamedTuple):
    opcode: int
    src_mac: str
    src_ip: str
    dst_mac: str
    dst_ip: str


def parse_arp(data: bytes) -> Optional[ParsedARP]:
    """Parses 28-byte ARP header."""
    if len(data) < 28:
        return None
    hw_type, proto_type, hw_len, proto_len, opcode = struct.unpack("!HHBBH", data[0:8])
    if hw_len != 6 or proto_len != 4:
        return None
    src_mac = mac_to_str(data[8:14])
    src_ip = ip_to_str(data[14:18])
    dst_mac = mac_to_str(data[18:24])
    dst_ip = ip_to_str(data[24:28])
    return ParsedARP(opcode, src_mac, src_ip, dst_mac, dst_ip)


class ParsedIPv4(NamedTuple):
    src_ip: str
    dst_ip: str
    proto: int
    src_port: Optional[int]
    dst_port: Optional[int]
    payload: bytes


def parse_ipv4(data: bytes) -> Optional[ParsedIPv4]:
    """Parses IPv4 header & transport layer ports."""
    if len(data) < 20:
        return None
    ver_ihl, tos, total_len, _, _, ttl, proto, _ = struct.unpack("!BBHHHBBH", data[0:12])
    ihl = (ver_ihl & 0x0f) * 4
    src_ip = ip_to_str(data[12:16])
    dst_ip = ip_to_str(data[16:20])
    
    src_port = None
    dst_port = None
    transport_data = data[ihl:]
    
    if proto in (6, 17) and len(transport_data) >= 4:  # TCP or UDP
        src_port, dst_port = struct.unpack("!HH", transport_data[0:4])
        
    return ParsedIPv4(src_ip, dst_ip, proto, src_port, dst_port, transport_data)


# ==============================================================================
# LLDP Serialization & Deserialization for Dynamic Topology Discovery
# ==============================================================================

def build_lldp_packet(dpid: int, port_no: int, system_name: str = "SDN-ITE") -> bytes:
    """
    Constructs an IEEE 802.1AB LLDP packet inside an Ethernet frame.
    """
    # Chassis ID TLV (Type 1): Subtype 4 (MAC/DPID), Value = 8-byte DPID
    chassis_val = struct.pack("!BQ", 4, dpid)
    chassis_tlv = struct.pack("!H", (1 << 9) | len(chassis_val)) + chassis_val
    
    # Port ID TLV (Type 2): Subtype 2 (Port component / int), Value = 4-byte port_no
    port_val = struct.pack("!BI", 2, port_no)
    port_tlv = struct.pack("!H", (2 << 9) | len(port_val)) + port_val
    
    # TTL TLV (Type 3): 120s
    ttl_val = struct.pack("!H", 120)
    ttl_tlv = struct.pack("!H", (3 << 9) | len(ttl_val)) + ttl_val
    
    # System Name TLV (Type 5)
    sys_val = system_name.encode("utf-8")
    sys_tlv = struct.pack("!H", (5 << 9) | len(sys_val)) + sys_val
    
    # End of LLDPDU TLV (Type 0)
    end_tlv = struct.pack("!H", 0)
    
    lldp_pdu = chassis_tlv + port_tlv + ttl_tlv + sys_tlv + end_tlv
    
    # Ethernet encapsulation (Destination LLDP Multicast: 01:80:c2:00:00:0e)
    dst_mac = bytes([0x01, 0x80, 0xc2, 0x00, 0x00, 0x0e])
    src_mac = bytes([0x00, 0x00, 0x00, 0x00, 0x00, (dpid & 0xff)])
    eth_hdr = dst_mac + src_mac + struct.pack("!H", ETH_TYPE_LLDP)
    
    return eth_hdr + lldp_pdu


class ParsedLLDP(NamedTuple):
    src_dpid: int
    src_port: int


def parse_lldp(payload: bytes) -> Optional[ParsedLLDP]:
    """
    Parses LLDPDU payload to extract source dpid and port.
    """
    offset = 0
    src_dpid = None
    src_port = None
    
    while offset + 2 <= len(payload):
        tlv_hdr = struct.unpack("!H", payload[offset:offset+2])[0]
        tlv_type = (tlv_hdr >> 9) & 0x7f
        tlv_len = tlv_hdr & 0x1ff
        offset += 2
        
        if tlv_type == 0:  # End of LLDPDU
            break
            
        tlv_data = payload[offset : offset + tlv_len]
        offset += tlv_len
        
        if tlv_type == 1 and len(tlv_data) >= 9:  # Chassis ID
            subtype = tlv_data[0]
            if subtype == 4:
                src_dpid = struct.unpack("!Q", tlv_data[1:9])[0]
        elif tlv_type == 2 and len(tlv_data) >= 5:  # Port ID
            subtype = tlv_data[0]
            if subtype == 2:
                src_port = struct.unpack("!I", tlv_data[1:5])[0]
                
    if src_dpid is not None and src_port is not None:
        return ParsedLLDP(src_dpid, src_port)
    return None
