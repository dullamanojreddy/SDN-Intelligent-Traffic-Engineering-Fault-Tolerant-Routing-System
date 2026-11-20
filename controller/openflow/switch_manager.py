"""
OpenFlow 1.3 Datapath & Switch Connection Manager
"""
import asyncio
import struct
import time
from typing import Dict, List, Optional, Callable, Any
from controller.utils.logger import log
from controller.openflow.protocol import (
    OFP_VERSION,
    OFPT_HELLO,
    OFPT_ECHO_REQUEST,
    OFPT_ECHO_REPLY,
    OFPT_ERROR,
    OFPT_ROLE_REPLY,
    OFPCR_ROLE_EQUAL,
    parse_role_reply,
    OFPT_FEATURES_REQUEST,
    OFPT_FEATURES_REPLY,
    OFPT_SET_CONFIG,
    OFPT_PACKET_IN,
    OFPT_PORT_STATUS,
    OFPT_MULTIPART_REPLY,
    OFPMP_PORT_STATS,
    OFPP_CONTROLLER,
    OFPP_ANY,
    OFPFC_ADD,
    build_hello,
    build_echo_reply,
    build_header,
    build_features_request,
    build_set_config,
    build_flow_mod,
    build_action_output,
    build_instruction_apply_actions,
    parse_header,
    parse_port_status,
)

# Message types a SLAVE controller must never send (they modify the switch).
_WRITE_MESSAGE_TYPES = {13, 14, 15, 16, 17}  # PACKET_OUT, FLOW_MOD, GROUP_MOD, PORT_MOD, TABLE_MOD


class Datapath:
    """Represents an OpenFlow 1.3 Connected Switch Datapath."""
    def __init__(
        self,
        dpid: int,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        addr: tuple,
        write_guard: Optional[Callable[[], bool]] = None,
    ):
        # Returns False while this controller must not modify the switch (SLAVE).
        self.write_guard = write_guard
        self.dpid: int = dpid
        self.sw_id: str = f"s{dpid}"
        self.reader: asyncio.StreamReader = reader
        self.writer: asyncio.StreamWriter = writer
        self.addr: tuple = addr
        self.ports: Dict[int, Any] = {}
        self.n_tables: int = 254
        self.capabilities: int = 0
        self.is_active: bool = True
        self.last_seen: float = time.monotonic()
        # Role this controller holds on the switch (EQUAL until negotiated).
        self.role: int = OFPCR_ROLE_EQUAL

    async def send_msg(self, msg: bytes) -> bool:
        """Sends binary OpenFlow message to the switch."""
        if not self.is_active or self.writer.is_closing():
            return False
        if (self.write_guard is not None and len(msg) >= 2
                and msg[1] in _WRITE_MESSAGE_TYPES and not self.write_guard()):
            return False  # standby controllers never program switches
        try:
            self.writer.write(msg)
            await self.writer.drain()
            return True
        except Exception as e:
            log.warning(f"[{self.sw_id}] Failed to send message: {e}")
            self.is_active = False
            return False

    def close(self):
        """Closes the socket connection."""
        self.is_active = False
        try:
            self.writer.close()
        except Exception:
            pass


class SwitchManager:
    """
    Manages TCP OpenFlow 1.3 switch sessions and handshakes.
    """
    def __init__(
        self,
        on_switch_connected: Optional[Callable[[Datapath], Any]] = None,
        on_switch_disconnected: Optional[Callable[[Datapath], Any]] = None,
        on_packet_in: Optional[Callable[[Datapath, bytes], Any]] = None,
        on_port_stats_reply: Optional[Callable[[Datapath, bytes], Any]] = None,
        on_port_status: Optional[Callable[[Datapath, bytes], Any]] = None,
        on_role_reply: Optional[Callable[[Datapath, Any], Any]] = None,
        on_error: Optional[Callable[[Datapath, int, int], Any]] = None,
        keepalive_interval: float = 5.0,
        keepalive_timeout: float = 15.0,
    ):
        self.write_guard: Optional[Callable[[], bool]] = None
        self.on_role_reply = on_role_reply
        self.on_error = on_error
        self.keepalive_interval = keepalive_interval
        self.keepalive_timeout = keepalive_timeout
        self.datapaths: Dict[int, Datapath] = {}
        self.on_switch_connected = on_switch_connected
        self.on_switch_disconnected = on_switch_disconnected
        self.on_packet_in = on_packet_in
        self.on_port_stats_reply = on_port_stats_reply
        self.on_port_status = on_port_status
        self._server: Optional[asyncio.Server] = None

    def get_datapath(self, dpid: int) -> Optional[Datapath]:
        return self.datapaths.get(dpid)

    def get_datapath_by_name(self, sw_name: str) -> Optional[Datapath]:
        try:
            dpid = int(sw_name.replace("s", ""))
            return self.datapaths.get(dpid)
        except Exception:
            return None

    async def start_server(self, host: str = "0.0.0.0", port: int = 6653):
        """Starts the OpenFlow 1.3 TCP server."""
        self._server = await asyncio.start_server(
            self._handle_client_connection, host, port
        )
        log.info(f"OpenFlow 1.3 Controller Server listening on {host}:{port}")

    async def stop_server(self):
        """Shuts down all connections and stops listening."""
        for dp in list(self.datapaths.values()):
            dp.close()
        self.datapaths.clear()
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            log.info("OpenFlow Controller Server stopped.")

    async def _handle_client_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        addr = writer.get_extra_info("peername")
        log.info(f"New switch connection from {addr}")
        
        # 1. Perform OpenFlow 1.3 Handshake
        try:
            # Send HELLO
            writer.write(build_hello(xid=1))
            await writer.drain()
            
            # Read Switch HELLO
            hdr_bytes = await reader.readexactly(8)
            hdr = parse_header(hdr_bytes)
            if not hdr or hdr.version != OFP_VERSION:
                log.warning(f"Unsupported OF version ({hdr.version if hdr else 'None'}) from {addr}")
                writer.close()
                return
            if hdr.length > 8:
                await reader.readexactly(hdr.length - 8)
                
            # Send FEATURES_REQUEST
            writer.write(build_features_request(xid=2))
            await writer.drain()
            
            # Read FEATURES_REPLY
            rep_hdr_bytes = await reader.readexactly(8)
            rep_hdr = parse_header(rep_hdr_bytes)
            if not rep_hdr or rep_hdr.msg_type != OFPT_FEATURES_REPLY:
                log.warning(f"Expected FEATURES_REPLY, got msg_type={rep_hdr.msg_type if rep_hdr else 'None'}")
                writer.close()
                return
                
            body = await reader.readexactly(rep_hdr.length - 8)
            # Body format: datapath_id(8), n_buffers(4), n_tables(1), auxiliary_id(1), pad(2), capabilities(4)
            dpid, n_buffers, n_tables, auxiliary_id, _, capabilities = struct.unpack("!QIBB2sI", body[:20])
            
            # Send SET_CONFIG (miss_send_len=0xffff)
            writer.write(build_set_config(flags=0, miss_send_len=0xffff, xid=3))
            await writer.drain()
            
            # Initialize Datapath
            dp = Datapath(dpid, reader, writer, addr, write_guard=self.write_guard)
            dp.n_tables = n_tables
            dp.capabilities = capabilities
            self.datapaths[dpid] = dp
            
            log.info(f"Switch Handshake Complete: {dp.sw_id} (DPID: {dpid:#018x}, Tables: {n_tables}) from {addr}")
            
            # Install Default Table-Miss Flow Rule (Priority 0 -> Controller)
            actions = build_action_output(OFPP_CONTROLLER, max_len=0xffff)
            instructions = build_instruction_apply_actions(actions)
            table_miss_flow = build_flow_mod(
                priority=0,
                command=OFPFC_ADD,
                match=None,
                instructions=instructions,
                xid=4,
            )
            await dp.send_msg(table_miss_flow)
            log.debug(f"[{dp.sw_id}] Installed Default Table-Miss Flow Rule (Priority 0 -> Controller)")
            
            # Callback
            if self.on_switch_connected:
                try:
                    res = self.on_switch_connected(dp)
                    if asyncio.iscoroutine(res):
                        await res
                except Exception as e:
                    log.error(f"Error in on_switch_connected callback: {e}")
                    
            # 2. Liveness supervision + main message read loop
            keepalive_task = asyncio.create_task(self._keepalive_loop(dp))
            try:
                await self._datapath_message_loop(dp)
            finally:
                keepalive_task.cancel()
            
        except asyncio.IncompleteReadError:
            log.info(f"Switch connection closed abruptly: {addr}")
        except Exception as e:
            log.error(f"Error in switch session from {addr}: {e}")
        finally:
            writer.close()
            # Clean up
            for dp_id, dp_obj in list(self.datapaths.items()):
                if dp_obj.writer == writer:
                    del self.datapaths[dp_id]
                    log.info(f"Switch disconnected: {dp_obj.sw_id}")
                    if self.on_switch_disconnected:
                        try:
                            res = self.on_switch_disconnected(dp_obj)
                            if asyncio.iscoroutine(res):
                                await res
                        except Exception as ex:
                            log.error(f"Error in on_switch_disconnected callback: {ex}")
                    break

    async def _keepalive_loop(self, dp: Datapath):
        """Probe the switch with ECHO_REQUEST and drop half-open sessions."""
        xid = 0x7000
        while dp.is_active:
            await asyncio.sleep(self.keepalive_interval)
            silent_for = time.monotonic() - dp.last_seen
            if silent_for > self.keepalive_timeout:
                log.error(
                    f"[{dp.sw_id}] No OpenFlow traffic for {silent_for:.1f}s; "
                    "declaring switch connection dead"
                )
                dp.close()
                return
            xid += 1
            await dp.send_msg(build_header(OFPT_ECHO_REQUEST, 8, xid))

    async def _datapath_message_loop(self, dp: Datapath):
        """Continuously reads and dispatches OpenFlow messages from switch."""
        while dp.is_active:
            try:
                hdr_bytes = await dp.reader.readexactly(8)
                hdr = parse_header(hdr_bytes)
                if not hdr or hdr.version != OFP_VERSION:
                    log.warning(f"[{dp.sw_id}] Invalid header: {hdr}")
                    break
                    
                payload_len = hdr.length - 8
                payload = await dp.reader.readexactly(payload_len) if payload_len > 0 else b""
                dp.last_seen = time.monotonic()
                full_msg = hdr_bytes + payload
                
                # Dispatch message type
                if hdr.msg_type == OFPT_ECHO_REQUEST:
                    await dp.send_msg(build_echo_reply(hdr.xid, payload))
                    
                elif hdr.msg_type == OFPT_PACKET_IN:
                    if self.on_packet_in:
                        try:
                            res = self.on_packet_in(dp, full_msg)
                            if asyncio.iscoroutine(res):
                                await res
                        except Exception as e:
                            log.error(f"[{dp.sw_id}] Error in packet_in handler: {e}")
                            
                elif hdr.msg_type == OFPT_MULTIPART_REPLY:
                    if self.on_port_stats_reply:
                        try:
                            res = self.on_port_stats_reply(dp, full_msg)
                            if asyncio.iscoroutine(res):
                                await res
                        except Exception as e:
                            log.error(f"[{dp.sw_id}] Error in stats reply handler: {e}")
                            
                elif hdr.msg_type == OFPT_PORT_STATUS:
                    if self.on_port_status:
                        try:
                            res = self.on_port_status(dp, full_msg)
                            if asyncio.iscoroutine(res):
                                await res
                        except Exception as e:
                            log.error(f"[{dp.sw_id}] Error in port status handler: {e}")

                elif hdr.msg_type == OFPT_ROLE_REPLY:
                    reply = parse_role_reply(full_msg)
                    if reply:
                        dp.role = reply.role
                        if self.on_role_reply:
                            try:
                                res = self.on_role_reply(dp, reply)
                                if asyncio.iscoroutine(res):
                                    await res
                            except Exception as e:
                                log.error(f"[{dp.sw_id}] Error in role reply handler: {e}")

                elif hdr.msg_type == OFPT_ERROR:
                    if len(payload) >= 4:
                        err_type, err_code = struct.unpack("!HH", payload[:4])
                        log.error(f"[{dp.sw_id}] ⚠️ OpenFlow Error from switch: type={err_type}, code={err_code}, data_len={len(payload)-4}")
                        if self.on_error:
                            try:
                                res = self.on_error(dp, err_type, err_code)
                                if asyncio.iscoroutine(res):
                                    await res
                            except Exception as e:
                                log.error(f"[{dp.sw_id}] Error in error handler: {e}")
                            
            except asyncio.IncompleteReadError:
                break
            except Exception as e:
                log.error(f"[{dp.sw_id}] Message loop exception: {e}")
                break
