"""Controller-owned route validation and OpenFlow installation."""
from typing import Any, Dict, List
import asyncio
import time


class RouteInstallationService:
    def __init__(self, app: Any):
        self.app = app
        self.installations: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def install(self, request: Dict[str, Any]) -> Dict[str, Any]:
        installation_id = request["installation_id"]
        async with self._lock:
            existing = self.installations.get(installation_id)
            if existing:
                return existing

            result: Dict[str, Any] = {
                "installation_id": installation_id,
                "status": "VALIDATING",
                "installation_status": "REQUESTED",
                "verification_status": "NOT_RUN",
                "connectivity_status": "NOT_RUN",
                "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "failed_switches": [],
                "details": [],
            }
            self.installations[installation_id] = result

            try:
                src_ip = request["source_ip"]
                dst_ip = request["dest_ip"]
                path = request["path"]
                if not path or len(path) < 1:
                    raise ValueError("Selected route must contain at least one switch")
                if not all(self.app.network_graph.graph.has_node(sw) for sw in path):
                    raise ValueError("Selected route contains an unknown switch")
                for src, dst in zip(path, path[1:]):
                    edge = self.app.network_graph.graph.get_edge_data(src, dst)
                    if not edge or not edge.get("is_active", True):
                        raise ValueError(f"Route link is unavailable: {src}-{dst}")

                src_host = self.app.packet_handler.host_ip_table.get(src_ip)
                dst_host = self.app.packet_handler.host_ip_table.get(dst_ip)
                if not src_host or not dst_host:
                    raise ValueError("Controller has not discovered both source and destination hosts")
                if src_host[0] != path[0] or dst_host[0] != path[-1]:
                    raise ValueError("Route endpoints do not match discovered host attachments")

                hops = self.app.packet_handler._build_port_hops(
                    path, ingress_port=src_host[1], egress_port=dst_host[1]
                )
                result["status"] = "INSTALLING"
                result["installation_status"] = "INSTALLING"
                ok = await self.app.flow_manager.install_path_forwarding(
                    path=path,
                    port_hops=hops,
                    src_ip=src_ip,
                    dst_ip=dst_ip,
                    src_mac=src_host[2],
                    dst_mac=dst_host[2],
                    priority=int(request.get("priority", 100)),
                    idle_timeout=int(request.get("idle_timeout", 300)),
                    cookie=int(request.get("cookie", 0)),
                    replace=True,
                )
                if not ok:
                    result["status"] = "PARTIALLY_INSTALLED"
                    result["installation_status"] = "PARTIALLY_INSTALLED"
                    result["details"].append("One or more OpenFlow messages were not accepted")
                    return result

                result["installation_status"] = "INSTALLED"
                expected_switches = set(path)
                installed_switches = {
                    flow["switch"]
                    for flow in self.app.flow_manager.active_flows.values()
                    if flow.get("match", {}).get("ipv4_dst") == dst_ip
                    and flow.get("switch") in expected_switches
                }
                result["installed_switches"] = sorted(installed_switches)
                if installed_switches != expected_switches:
                    result["status"] = "FAILED"
                    result["verification_status"] = "CONTROLLER_REGISTRY_FAILED"
                    result["failure_details"] = "Controller flow registry does not contain every route switch"
                    return result

                result["status"] = "INSTALLED"
                result["verification_status"] = "NOT_RUN"
                result["registry_verification_status"] = "VERIFIED"
                result["verification_details"] = (
                    "Controller flow registry contains the expected rules. "
                    "Actual OpenFlow flow-table verification has not been performed."
                )
                result["active_route"] = {
                    "source_ip": src_ip,
                    "dest_ip": dst_ip,
                    "path": path,
                    "installation_id": installation_id,
                }
                return result
            except (KeyError, TypeError, ValueError) as exc:
                result["status"] = "FAILED"
                result["installation_status"] = "FAILED"
                result["failure_details"] = str(exc)
                return result
