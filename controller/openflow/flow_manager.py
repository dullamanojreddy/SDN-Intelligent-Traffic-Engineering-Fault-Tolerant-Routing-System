"""
OpenFlow 1.3 Flow Modification & Installation Manager
"""
import time
from typing import Dict, List, Optional, Any, Tuple
from controller.utils.logger import log
from controller.openflow.protocol import (
    OFPFC_ADD,
    OFPFC_MODIFY,
    OFPFC_DELETE,
    OFPFC_DELETE_STRICT,
    OFPP_ANY,
    build_flow_mod,
    build_match,
    build_action_output,
    build_instruction_apply_actions,
    ETH_TYPE_IP,
    ETH_TYPE_ARP,
)
from controller.openflow.switch_manager import SwitchManager, Datapath

class FlowManager:
    """
    Manages the installation, modification, and deletion of OpenFlow forwarding rules.
    """
    def __init__(self, switch_manager: SwitchManager):
        self.switch_manager = switch_manager
        # Flow cache: flow_id -> flow metadata
        self.active_flows: Dict[str, Dict[str, Any]] = {}

    async def install_flow(
        self,
        datapath: Datapath,
        match_kwargs: dict,
        out_port: int,
        priority: int = 100,
        idle_timeout: int = 60,
        hard_timeout: int = 0,
        cookie: int = 0,
        command: int = OFPFC_ADD,
        replace: bool = False,
    ) -> bool:
        """Installs a single OpenFlow rule on the specified switch.

        ``replace=True`` always sends ADD (which overwrites an identical match). Use it
        when re-asserting desired state: MODIFY is a no-op if the switch no longer has
        the rule (deleted externally, restarted), and the controller cache cannot know.
        """
        match_bytes = build_match(**match_kwargs)
        actions = build_action_output(out_port)
        instructions = build_instruction_apply_actions(actions)

        # Replace an existing destination rule rather than keeping multiple
        # cached versions with different output ports.
        flow_id = self.flow_id_for(datapath.sw_id, match_kwargs, priority)
        existing = self.active_flows.get(flow_id)
        if existing and command == OFPFC_ADD and not replace and not self._is_expired(existing):
            command = OFPFC_MODIFY

        flow_mod = build_flow_mod(
            cookie=cookie,
            command=command,
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout,
            priority=priority,
            match=match_bytes,
            instructions=instructions,
        )
        
        success = await datapath.send_msg(flow_mod)
        if success:
            self.active_flows[flow_id] = {
                "switch": datapath.sw_id,
                "dpid": datapath.dpid,
                "match": match_kwargs,
                "out_port": out_port,
                "priority": priority,
                "idle_timeout": idle_timeout,
                "hard_timeout": hard_timeout,
                "installed_at": time.monotonic(),
            }
            log.debug(f"[{datapath.sw_id}] Flow rule installed -> Port {out_port} (Pri: {priority}, Match: {match_kwargs})")
        return success

    @staticmethod
    def flow_id_for(sw_id: str, match_kwargs: dict, priority: int) -> str:
        """Cache key for a destination rule on one switch."""
        dst_target = (
            match_kwargs.get("ipv4_dst")
            or match_kwargs.get("arp_tpa")
            or match_kwargs.get("eth_dst", "")
        )
        return f"{sw_id}_{match_kwargs.get('eth_type', '')}_{dst_target}_{priority}"

    @staticmethod
    def _is_expired(entry: Dict[str, Any]) -> bool:
        """True when the switch has probably aged the rule out already.

        OFPFC_MODIFY on a missing rule is a no-op in OpenFlow 1.3, so a cached
        rule that may have idled out must be re-added instead of modified.
        """
        idle = entry.get("idle_timeout", 0)
        hard = entry.get("hard_timeout", 0)
        age = time.monotonic() - entry.get("installed_at", 0.0)
        return (idle > 0 and age >= idle) or (hard > 0 and age >= hard)

    def forget_switch(self, sw_id: str) -> int:
        """Drop cached rules for a switch whose table is no longer trusted
        (disconnect/reconnect/removal). Returns the number of dropped entries."""
        stale = [k for k, v in self.active_flows.items() if v["switch"] == sw_id]
        for key in stale:
            del self.active_flows[key]
        return len(stale)

    async def delete_cached_flow(self, flow_id: str) -> bool:
        """Delete one cached destination rule from its switch and the cache."""
        entry = self.active_flows.pop(flow_id, None)
        if not entry:
            return False
        datapath = self.switch_manager.get_datapath(entry["dpid"])
        if not datapath:
            return False
        match = {k: v for k, v in entry["match"].items()}
        del_mod = build_flow_mod(
            command=OFPFC_DELETE_STRICT,
            priority=entry["priority"],
            match=build_match(**match),
            out_port=OFPP_ANY,
        )
        return await datapath.send_msg(del_mod)

    async def remove_flows_for_switch(self, datapath: Datapath):
        """Flushes all installed flows on a switch."""
        del_mod = build_flow_mod(
            command=OFPFC_DELETE,
            match=build_match(),
            out_port=OFPP_ANY,
        )
        await datapath.send_msg(del_mod)
        # Clear matching active flows
        to_del = [k for k, v in self.active_flows.items() if v["switch"] == datapath.sw_id]
        for k in to_del:
            del self.active_flows[k]
        log.info(f"[{datapath.sw_id}] Flushed flow table")

    async def install_path_forwarding(
        self,
        path: List[str],
        port_hops: List[Tuple[str, int, int]],  # (switch, in_port, out_port)
        src_ip: str,
        dst_ip: str,
        src_mac: Optional[str] = None,
        dst_mac: Optional[str] = None,
        priority: int = 100,
        idle_timeout: int = 300,
        hard_timeout: int = 0,
        cookie: int = 0,
        replace: bool = False,
    ) -> bool:
        """
        Installs multi-hop forwarding rules along a computed path for IPv4 and ARP traffic.
        """
        all_success = True
        for sw_id, in_p, out_p in port_hops:
            dp = self.switch_manager.get_datapath_by_name(sw_id)
            if not dp:
                log.warning(
                    "[FLOW] Cannot install %s -> %s route on %s: datapath is not connected",
                    src_ip,
                    dst_ip,
                    sw_id,
                )
                all_success = False
                continue
                
            # IPv4 Flow Rule (destination-based matching for seamless multi-hop forwarding)
            match_ip = {
                "eth_type": ETH_TYPE_IP,
                "ipv4_dst": dst_ip,
            }
            ok1 = await self.install_flow(
                dp, match_ip, out_port=out_p, priority=priority, idle_timeout=idle_timeout,
                hard_timeout=hard_timeout, cookie=cookie, replace=replace,
            )
            
            # ARP Flow Rule (for direct ARP resolution using target IPv4 address)
            match_arp = {
                "eth_type": ETH_TYPE_ARP,
                "arp_tpa": dst_ip,
            }
            ok2 = await self.install_flow(
                dp, match_arp, out_port=out_p, priority=priority, idle_timeout=idle_timeout,
                hard_timeout=hard_timeout, cookie=cookie, replace=replace,
            )
                
            if not (ok1 and ok2):
                all_success = False
                
        log.info(f"Installed Path Flows along {' -> '.join(path)} for {src_ip} -> {dst_ip}")
        return all_success

    async def install_bidirectional_path_forwarding(
        self,
        forward_path: List[str],
        forward_hops: List[Tuple[str, int, int]],
        reverse_path: List[str],
        reverse_hops: List[Tuple[str, int, int]],
        src_ip: str,
        dst_ip: str,
        src_mac: Optional[str] = None,
        dst_mac: Optional[str] = None,
        priority: int = 100,
        idle_timeout: int = 300,
        hard_timeout: int = 0,
    ) -> bool:
        """
        Installs forward and return path forwarding rules simultaneously.
        """
        fwd_ok = await self.install_path_forwarding(
            path=forward_path,
            port_hops=forward_hops,
            src_ip=src_ip,
            dst_ip=dst_ip,
            src_mac=src_mac,
            dst_mac=dst_mac,
            priority=priority,
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout,
        )
        rev_ok = await self.install_path_forwarding(
            path=reverse_path,
            port_hops=reverse_hops,
            src_ip=dst_ip,
            dst_ip=src_ip,
            src_mac=dst_mac,
            dst_mac=src_mac,
            priority=priority,
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout,
        )
        return fwd_ok and rev_ok
