"""Glue between topology edits, controller synchronisation, routing and notifications."""
import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional

from backend.database.connection import db_manager
from backend.services.controller_monitor import ControllerMonitor
from backend.services.network_agent import AgentError, NetworkAgentClient
from backend.services.route_verifier import verify_route
from backend.services.routing_service import RoutingService
from backend.services.topology_service import TopologyService
from backend.websocket.manager import ws_manager

logger = logging.getLogger("backend.orchestrator")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class NetworkOrchestrator:
    def __init__(self, topology: TopologyService, monitor: ControllerMonitor, routing: RoutingService,
                 agent: Optional[NetworkAgentClient] = None):
        self.topology = topology
        self.monitor = monitor
        self.routing = routing
        self.agent = agent
        self._edit_lock = asyncio.Lock()   # edits are applied to the network one at a time

    async def modify(
        self,
        description: str,
        mutate: Callable[[], Any],
        agent_op: Optional[Callable[[Any], Awaitable[Any]]] = None,
        confirm_links: Optional[Callable[[Any], List[tuple]]] = None,
    ) -> tuple:
        """Apply one topology edit atomically across model, network and controller.

        1. validate + apply to the backend model (``mutate`` raises on invalid input);
        2. apply to the running network through the agent - if that fails the model is
           rolled back and the error propagates, so model and network never diverge;
        3. sync the controller and re-evaluate routes (``apply_change``).
        Links created through the agent are confirmed real; without an agent they stay
        unconfirmed and the router refuses to use them.
        """
        async with self._edit_lock:
            checkpoint = self.topology.checkpoint()
            result = mutate()
            if self.agent and self.agent.enabled and agent_op:
                try:
                    await agent_op(result)
                except AgentError:
                    self.topology.restore(checkpoint)
                    raise
                for src, dst in (confirm_links(result) if confirm_links else []):
                    self.topology.mark_confirmed(src, dst, True)
            change = await self.apply_change(description)
            return result, change

    async def verify_route(self, source_ip: str, dest_ip: str,
                           expected_path: Optional[List[str]] = None) -> Dict[str, Any]:
        """Compare the calculated route with what OVS actually holds in its flow tables."""
        base = {"source_ip": source_ip, "dest_ip": dest_ip}
        if not (self.agent and self.agent.enabled):
            return {**base, "status": "UNAVAILABLE", "verified": False,
                    "reason": "no network agent attached: OVS flow tables cannot be read"}
        explanation = self.routing.explain(source_ip, dest_ip)
        if expected_path is None:
            expected_path = explanation["selected_path"]
        hosts = {h.ip: h for h in self.topology.hosts.values()}
        dst = hosts[dest_ip]
        try:
            flows = await self.agent.flows()
        except AgentError as exc:
            return {**base, "status": "UNAVAILABLE", "verified": False, "reason": str(exc)}
        with self.topology._lock:
            graph = self.topology.network_graph.graph
            neighbors = {(u, d["src_port"]): v for u, v, d in graph.edges(data=True)}
            expected_ports = {}
            if expected_path:
                for u, v in zip(expected_path, expected_path[1:]):
                    expected_ports[u] = graph[u][v]["src_port"]
                expected_ports[expected_path[-1]] = dst.connected_port
        result = verify_route(expected_path, hosts[source_ip].connected_switch, dst.connected_switch,
                              dst.connected_port, dest_ip, flows, neighbors, expected_ports)
        if expected_path is None:
            result["discrepancies"].insert(0, "no route is calculated for this pair: " + explanation["explanation"])
        return {**base, "route_status": explanation["status"], **result}

    async def verify_all(self) -> Dict[str, Any]:
        hosts = list(self.topology.hosts.values())
        results = []
        for src in hosts:
            for dst in hosts:
                if src.ip != dst.ip and src.connected_switch != dst.connected_switch:
                    results.append(await self.verify_route(src.ip, dst.ip))
        counts: Dict[str, int] = {}
        for r in results:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        return {"all_verified": bool(results) and all(r["verified"] for r in results),
                "counts": counts, "results": results}

    async def network_status(self) -> Dict[str, Any]:
        """Is a live network attached, and does the model still match it?"""
        if not (self.agent and self.agent.enabled):
            return {"agent_enabled": False, "reachable": False, "in_sync": None, "drift": [],
                    "note": "model-only mode: links added through the API stay unconfirmed and unroutable"}
        try:
            real = await self.agent.topology()
        except AgentError as exc:
            return {"agent_enabled": True, "reachable": False, "in_sync": None, "drift": [], "error": str(exc)}
        drift = self.topology.drift(real)
        return {"agent_enabled": True, "reachable": True, "in_sync": not drift, "drift": drift}

    async def reconcile(self, mode: str = "report") -> Dict[str, Any]:
        """Report drift, or ``adopt`` the running network as the new model."""
        status = await self.network_status()
        if mode == "adopt" and status.get("reachable") and status["drift"]:
            async with self._edit_lock:
                self.topology.adopt(await self.agent.topology())
                self.routing.current.clear()
                self.routing.refresh("Reconciled with running network")
            change = await self.apply_change("Model reconciled with the running network")
            status = {**await self.network_status(), "adopted": True, **change}
        return status

    async def adopt_on_startup(self) -> bool:
        if not (self.agent and self.agent.enabled):
            return False
        try:
            self.topology.adopt(await self.agent.topology())
        except AgentError as exc:
            logger.warning("network agent unavailable at startup, keeping default model: %s", exc)
            return False
        self.routing.current.clear()
        self.routing.refresh("Initial topology")
        logger.info("model adopted from the running network")
        return True

    async def _record_alert(self, type_: str, severity: str, source: str, message: str,
                            status: str = "ACTIVE", **data: Any) -> None:
        await db_manager.insert_one("alerts", {
            "timestamp": _now(), "type": type_, "severity": severity,
            "source": source, "message": message, "status": status, "data": data,
        })

    async def _record_decisions(self, decisions: List[Dict[str, Any]]) -> None:
        for decision in decisions:
            await db_manager.insert_one("routing_decisions", decision)
        if decisions:
            await ws_manager.broadcast({"type": "ROUTE_CHANGE", "timestamp": _now(), "data": decisions})

    async def apply_change(self, description: str) -> Dict[str, Any]:
        """Run after every topology mutation: sync to the controller, re-route, notify."""
        sync_status = await self.monitor.sync_now()
        decisions = self.routing.refresh(description)
        await self._record_decisions(decisions)
        severity = "INFO" if sync_status == "SYNCED" else "WARNING"
        await self._record_alert(
            "TOPOLOGY_CHANGE", severity, "Backend",
            f"{description} (controller sync: {sync_status}; {len(decisions)} route change(s))",
            status="RESOLVED" if sync_status == "SYNCED" else "ACTIVE",
            sync_status=sync_status, route_changes=len(decisions),
        )
        await ws_manager.broadcast({
            "type": "TOPOLOGY_UPDATE", "timestamp": _now(),
            "data": {"description": description, "sync_status": sync_status,
                     "version": self.topology.version},
        })
        return {
            "sync_status": sync_status,
            "topology_version": self.topology.version,
            "route_changes": decisions,
        }

    async def on_controller_event(self, event: Dict[str, Any]) -> None:
        """Persist and broadcast a controller liveness event."""
        severity = event["severity"]
        await self._record_alert(
            event["type"], severity, f"Controller {event['data'].get('active_url', '')}",
            event["message"],
            status="ACTIVE" if event["type"] == "CONTROLLER_DOWN" else "RESOLVED",
        )
        if event["type"] != "CONTROLLER_DOWN" and event["data"].get("sync_status") == "SYNCED":
            # The outage is over and queued edits have been applied: close the open alerts.
            for open_type in ("CONTROLLER_DOWN", "TOPOLOGY_CHANGE"):
                await db_manager.update_many("alerts", {"type": open_type, "status": "ACTIVE"},
                                             {"status": "RESOLVED"})
        await ws_manager.broadcast({"type": "CONTROLLER_STATUS", "timestamp": event["timestamp"], "data": event})
        # Recovery/failover changes the live telemetry source: re-evaluate routes.
        if event["type"] != "CONTROLLER_DOWN":
            await self._record_decisions(self.routing.refresh(event["type"]))

    async def on_live_state(self, state: Dict[str, Any]) -> None:
        """Merge fresh controller telemetry; record decisions if paths changed."""
        self.topology.apply_live_state(state)
        decisions = self.routing.refresh("Network conditions changed")
        await self._record_decisions(decisions)
