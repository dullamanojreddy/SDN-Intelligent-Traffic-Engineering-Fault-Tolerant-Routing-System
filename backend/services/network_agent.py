"""Client for the Mininet network agent (network/agent.py).

When configured, every topology edit is applied to the *running* network first;
the backend model only changes if the agent succeeded.
"""
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("backend.network_agent")


class AgentError(Exception):
    """The agent rejected or failed an operation (the network is unchanged)."""

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


class NetworkAgentClient:
    def __init__(self, url: str, token: str, timeout: float = 20.0,
                 transport: Optional[httpx.AsyncBaseTransport] = None):
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.transport = transport

    @property
    def enabled(self) -> bool:
        return bool(self.url)

    async def call(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Any:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, connect=3.0),
                                         transport=self.transport) as client:
                response = await client.request(
                    method, f"{self.url}{path}", json=body,
                    headers={"Authorization": f"Bearer {self.token}"})
        except httpx.HTTPError as exc:
            raise AgentError(f"network agent unreachable: {exc.__class__.__name__}") from exc
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise AgentError(f"network agent refused the change: {detail}", response.status_code)
        return response.json()

    # ----------------------------------------------------------------- reads
    async def topology(self) -> Dict[str, Any]:
        return await self.call("GET", "/topology")

    async def flows(self) -> Dict[str, Any]:
        return (await self.call("GET", "/flows"))["flows"]

    async def switch_roles(self) -> Dict[str, Any]:
        return await self.call("GET", "/switch-roles")

    # ------------------------------------------------------------- mutations
    async def add_switch(self, name: str, dpid: int):
        return await self.call("POST", "/switches", {"name": name, "dpid": dpid})

    async def delete_switch(self, name: str):
        return await self.call("DELETE", f"/switches/{name}")

    async def add_host(self, name: str, ip: str, mac: str, switch: str, port: int):
        return await self.call("POST", "/hosts", {"name": name, "ip": ip, "mac": mac, "switch": switch, "port": port})

    async def delete_host(self, name: str):
        return await self.call("DELETE", f"/hosts/{name}")

    async def add_link(self, src: str, dst: str, src_port: int, dst_port: int,
                       capacity_mbps: float, latency_ms: float, loss_pct: float):
        return await self.call("POST", "/links", {
            "src": src, "dst": dst, "src_port": src_port, "dst_port": dst_port,
            "bw": capacity_mbps, "delay_ms": latency_ms, "loss": loss_pct})

    async def delete_link(self, src: str, dst: str):
        return await self.call("DELETE", f"/links/{src}/{dst}")

    async def update_link(self, src: str, dst: str, capacity_mbps=None, latency_ms=None, loss_pct=None):
        return await self.call("PATCH", f"/links/{src}/{dst}", {
            "bw": capacity_mbps, "delay_ms": latency_ms, "loss": loss_pct})

    async def traffic_start(self, src: str, dst: str, rate_mbps: float, duration_sec: int, protocol: str):
        return await self.call("POST", "/traffic-start", {
            "src": src, "dst": dst, "rate_mbps": rate_mbps, "duration_sec": duration_sec, "protocol": protocol})

    async def traffic_stop(self):
        return await self.call("POST", "/traffic-stop", {})

    async def set_link_state(self, src: str, dst: str, up: bool):
        return await self.call("POST", "/link-state", {"src": src, "dst": dst, "up": up})
