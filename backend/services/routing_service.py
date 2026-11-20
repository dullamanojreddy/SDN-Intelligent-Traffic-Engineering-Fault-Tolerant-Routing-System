"""Routing decisions and explanations computed from the live topology model.

Every explanation is produced by ``DijkstraRouter.explain_route`` over the actual
graph and cost function; nothing here is canned. ``refresh`` re-evaluates every
host pair after a topology or telemetry change and records a decision whenever
the selected path changes.
"""
import time
from typing import Any, Dict, List, Optional, Tuple

from controller.config.settings import settings as controller_settings
from controller.routing.cost_function import CostCalculator
from controller.routing.dijkstra import DijkstraRouter
from backend.services.topology_service import TopologyService


class UnknownHostError(KeyError):
    pass


class RoutingService:
    def __init__(self, topology: TopologyService):
        self.topology = topology
        # (src_ip, dst_ip) -> {"path": [...], "cost": float}
        self.current: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._seq = 0

    def router_for(self, qos_class: str = "DEFAULT") -> DijkstraRouter:
        profile = controller_settings.qos_profiles.get(qos_class.upper())
        if profile:
            calc = CostCalculator(alpha=profile["latency"], beta=profile["utilization"], gamma=profile["loss"],
                                  delta=profile.get("capacity", 0.0))
        else:
            calc = CostCalculator(
                alpha=controller_settings.latency_weight,
                beta=controller_settings.utilization_weight,
                gamma=controller_settings.loss_weight,
            )
        return DijkstraRouter(self.topology.network_graph, calc)

    def _switch_of(self, ip: str) -> str:
        for host in self.topology.hosts.values():
            if host.ip == ip:
                return host.connected_switch
        raise UnknownHostError(ip)

    def explain(self, source_ip: str, dest_ip: str, qos_class: str = "DEFAULT", k: int = 3) -> Dict[str, Any]:
        with self.topology._lock:
            src_sw, dst_sw = self._switch_of(source_ip), self._switch_of(dest_ip)
            result = self.router_for(qos_class).explain_route(src_sw, dst_sw, k=k)
        return {**result, "source_switch": src_sw, "dest_switch": dst_sw}

    # ------------------------------------------------------------- decisions
    def _next_id(self) -> str:
        self._seq += 1
        return f"dec_{int(time.time() * 1000)}_{self._seq}"

    def refresh(self, trigger: str) -> List[Dict[str, Any]]:
        """Recompute all host-pair routes; return decisions for pairs whose path changed."""
        decisions: List[Dict[str, Any]] = []
        with self.topology._lock:
            router = self.router_for("DEFAULT")
            hosts = list(self.topology.hosts.values())
            live_pairs = set()
            for src in hosts:
                for dst in hosts:
                    if src.ip == dst.ip or src.connected_switch == dst.connected_switch:
                        continue
                    key = (src.ip, dst.ip)
                    live_pairs.add(key)
                    explanation = router.explain_route(src.connected_switch, dst.connected_switch, k=3)
                    new_path: Optional[List[str]] = explanation["selected_path"]
                    previous = self.current.get(key)
                    self.current[key] = {"path": new_path, "cost": explanation["selected_cost"]}
                    if previous is None or previous["path"] == new_path:
                        continue
                    decisions.append(self._decision(router, key, previous, explanation, trigger))
            for stale in set(self.current) - live_pairs:
                del self.current[stale]
        return decisions

    def _decision(self, router: DijkstraRouter, key: Tuple[str, str], previous: Dict[str, Any],
                  explanation: Dict[str, Any], trigger: str) -> Dict[str, Any]:
        old_path: List[str] = previous["path"] or []
        new_path: List[str] = explanation["selected_path"] or []
        if not new_path:
            why = f"No route remains. {explanation['explanation']}"
            old_cost = router.path_cost(old_path) if old_path else None
            new_cost = 999.0
        elif not old_path:
            why = f"Connectivity restored. {explanation['explanation']}"
            old_cost, new_cost = 999.0, float(explanation["selected_cost"])
        else:
            blocked = router.first_unusable_hop(old_path)
            old_cost = router.path_cost(old_path)
            new_cost = float(explanation["selected_cost"])
            if blocked:
                why = (f"Previous path {' -> '.join(old_path)} is unusable: {blocked}. "
                       f"{explanation['explanation']}")
            else:
                why = (f"Previous path {' -> '.join(old_path)} now costs {old_cost} versus "
                       f"{new_cost} for the new path after the change. {explanation['explanation']}")
        best = (explanation["candidates"] or [{}])[0]
        return {
            "decision_id": self._next_id(),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_ip": key[0],
            "dest_ip": key[1],
            "old_path": old_path,
            "new_path": new_path,
            "reason": f"{trigger}: {why}",
            "trigger": trigger,
            "old_cost": 999.0 if old_cost is None else old_cost,
            "new_cost": new_cost,
            "latency_ms": best.get("latency_ms", 0.0),
            "utilization_pct": best.get("max_utilization_pct", 0.0),
            "packet_loss_pct": best.get("total_loss_pct", 0.0),
            "qos_class": "DEFAULT",
            "status": explanation["status"],
        }
