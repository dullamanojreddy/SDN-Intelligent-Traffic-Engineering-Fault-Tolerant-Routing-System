"""
Topology, Switches, Links, Hosts, Flows, Traffic, Routing, Alerts, and Experiments API Endpoints
"""
from fastapi import APIRouter, HTTPException
import httpx
from typing import List, Dict, Any
from backend.services.topology_service import topology_service
from backend.services.runtime import orchestrator, routing_service, controller_monitor, network_agent
from backend.services.network_agent import AgentError
from backend.services.routing_service import UnknownHostError
from backend.database.connection import db_manager
from backend.config.settings import settings
from backend.schemas.network import (
    RecalculateRouteRequest,
    TrafficStartRequest,
    FailureSimulateRequest,
    ExperimentStartRequest,
    SwitchCreateRequest,
    HostCreateRequest,
    LinkCreateRequest,
    LinkUpdateRequest,
    RouteInstallRequest
)
from controller.models.event import RoutingDecision
import time

topology_router = APIRouter(tags=["Topology"])
switches_router = APIRouter(tags=["Switches"])
links_router = APIRouter(tags=["Links"])
hosts_router = APIRouter(tags=["Hosts"])
flows_router = APIRouter(tags=["Flows"])
traffic_router = APIRouter(tags=["Traffic"])
routing_router = APIRouter(tags=["Routing"])
alerts_router = APIRouter(tags=["Alerts"])
experiments_router = APIRouter(tags=["Experiments"])


@topology_router.get("/api/topology")
async def get_topology():
    return topology_service.get_topology()

@switches_router.get("/api/switches")
async def get_switches():
    return topology_service.get_topology().switches

@links_router.get("/api/links")
async def get_links():
    return topology_service.get_topology().links

@hosts_router.get("/api/hosts")
async def get_hosts():
    return topology_service.get_topology().hosts


def _agent_http(exc: AgentError) -> HTTPException:
    """Map a failed network-agent operation to an HTTP error (the model was rolled back)."""
    status = exc.status if exc.status in (404, 409, 422) else 502
    return HTTPException(status_code=status, detail=f"{exc} (topology unchanged)")


@switches_router.post("/api/switches", status_code=201)
async def create_switch(req: SwitchCreateRequest):
    try:
        node, change = await orchestrator.modify(
            f"Switch {req.name.strip().lower()} added",
            lambda: topology_service.add_switch(req.name),
            lambda n: network_agent.add_switch(n.dpid, n.dpid_int),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AgentError as exc:
        raise _agent_http(exc) from exc
    return {**node.model_dump(), **change}


@switches_router.delete("/api/switches/{name}")
async def delete_switch(name: str):
    try:
        removed_hosts, change = await orchestrator.modify(
            f"Switch {name.lower()} removed",
            lambda: topology_service.remove_switch(name),
            lambda _: network_agent.delete_switch(name.lower()),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AgentError as exc:
        raise _agent_http(exc) from exc
    return {"status": "SUCCESS", "removed": name, "removed_hosts": removed_hosts, **change}


@hosts_router.post("/api/hosts", status_code=201)
async def create_host(req: HostCreateRequest):
    try:
        host, change = await orchestrator.modify(
            f"Host {req.name.strip().lower()} ({req.ip}) added on {req.connected_switch.lower()}",
            lambda: topology_service.add_host(req.name, req.ip, req.connected_switch, req.mac),
            lambda h: network_agent.add_host(h.name.lower(), h.ip, h.mac, h.connected_switch, h.connected_port),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AgentError as exc:
        raise _agent_http(exc) from exc
    return {**host.model_dump(), **change}


@hosts_router.delete("/api/hosts/{name}")
async def delete_host(name: str):
    try:
        _, change = await orchestrator.modify(
            f"Host {name.lower()} removed",
            lambda: topology_service.remove_host(name),
            lambda _: network_agent.delete_host(name.lower()),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AgentError as exc:
        raise _agent_http(exc) from exc
    return {"status": "SUCCESS", "removed": name, **change}


def _link_ports(src: str, dst: str):
    edge = topology_service.network_graph.graph[src.lower()][dst.lower()]
    return edge["src_port"], edge["dst_port"]


@links_router.post("/api/links", status_code=201)
async def create_link(req: LinkCreateRequest):
    try:
        _, change = await orchestrator.modify(
            f"Link {req.src.lower()}-{req.dst.lower()} added",
            lambda: topology_service.add_connection(req.src, req.dst, req.capacity_mbps, req.latency_ms, req.loss_pct),
            lambda _: network_agent.add_link(
                req.src.lower(), req.dst.lower(), *_link_ports(req.src, req.dst),
                req.capacity_mbps, req.latency_ms, req.loss_pct),
            lambda _: [(req.src, req.dst)],
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AgentError as exc:
        raise _agent_http(exc) from exc
    return {"status": "SUCCESS", "src": req.src, "dst": req.dst, **change}


@links_router.patch("/api/links/{src}/{dst}")
async def update_link(src: str, dst: str, req: LinkUpdateRequest):
    try:
        applied, change = await orchestrator.modify(
            f"Link {src.lower()}-{dst.lower()} updated",
            lambda: topology_service.update_connection(src, dst, req.capacity_mbps, req.latency_ms, req.loss_pct),
            lambda _: network_agent.update_link(src.lower(), dst.lower(), req.capacity_mbps, req.latency_ms, req.loss_pct),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AgentError as exc:
        raise _agent_http(exc) from exc
    return {"status": "SUCCESS", "src": src, "dst": dst, "applied": applied, **change}


@links_router.delete("/api/links/{src}/{dst}")
async def delete_link(src: str, dst: str):
    try:
        _, change = await orchestrator.modify(
            f"Link {src.lower()}-{dst.lower()} removed",
            lambda: topology_service.remove_connection(src, dst),
            lambda _: network_agent.delete_link(src.lower(), dst.lower()),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AgentError as exc:
        raise _agent_http(exc) from exc
    return {"status": "SUCCESS", "src": src, "dst": dst, **change}


@flows_router.get("/api/flows")
async def get_flows():
    """Flow entries installed in the switches.

    With a network agent these are the real OVS flow tables (``ovs-ofctl dump-flows``,
    including packet/byte counters). Otherwise the controller's registry of rules it
    installed is returned (no counters).
    """
    if network_agent.enabled:
        try:
            tables = await network_agent.flows()
        except AgentError:
            tables = None
        if tables is not None:
            entries = []
            for sw, flows in sorted(tables.items()):
                for index, f in enumerate(flows):
                    if "error" in f:
                        continue
                    match = {k: v for k, v in (
                        ("ipv4_dst", f["match"].get("nw_dst")), ("arp_tpa", f["match"].get("arp_tpa")),
                        ("ipv4_src", f["match"].get("nw_src"))) if v}
                    entries.append({
                        "flow_id": f"{sw}:{f['priority']}:{index}", "dpid": sw, "table_id": f.get("table", 0),
                        "priority": f["priority"], "match": match,
                        "instructions": [{"type": "APPLY_ACTIONS", "actions": (
                            [f"OUTPUT:{p}" for p in f["out_ports"]] or (["CONTROLLER"] if f["to_controller"] else ["DROP"]))}],
                        "packet_count": f.get("n_packets", 0), "byte_count": f.get("n_bytes", 0),
                        "duration_sec": int(f.get("duration", 0)), "status": "ACTIVE", "source": "ovs"})
            return entries
    if controller_monitor.status != "UP":
        return []
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(3.0)) as client:
            response = await client.get(
                f"{controller_monitor.active_url}/flows",
                headers={"Authorization": f"Bearer {settings.controller_api_token}"},
            )
        response.raise_for_status()
        flows = response.json().get("flows", [])
    except (httpx.HTTPError, ValueError):
        return []
    return [
        {
            "flow_id": flow["flow_id"],
            "dpid": flow["switch"],
            "table_id": 0,
            "priority": flow["priority"],
            "match": {k: v for k, v in flow["match"].items() if k in ("ipv4_dst", "ipv4_src", "arp_tpa", "eth_type")},
            "instructions": [{"type": "APPLY_ACTIONS", "actions": [f"OUTPUT:{flow['out_port']}"]}],
            "packet_count": 0,
            "byte_count": 0,
            "duration_sec": 0,
            "status": "ACTIVE",
            "source": "controller-registry",
        }
        for flow in flows
    ]

@routing_router.post("/api/routing/install")
async def install_route(req: RouteInstallRequest):
    document = req.model_dump()
    document["requested_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    document["request_type"] = "manual"
    document["status"] = "REQUESTED"
    if not settings.controller_api_token or settings.controller_api_token == "change-me":
        document.update({"status": "FAILED", "failure_details": "CONTROLLER_API_TOKEN is not configured"})
        await db_manager.insert_one("route_installations", document)
        raise HTTPException(status_code=503, detail="Controller authentication is not configured")
    if controller_monitor.status == "DOWN":
        document.update({"status": "FAILED", "failure_details": "Controller is down"})
        await db_manager.insert_one("route_installations", document)
        raise HTTPException(status_code=503, detail="Controller is down; route cannot be installed")
    try:
        timeout = httpx.Timeout(15.0, connect=3.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{controller_monitor.active_url}/routes/install",
                json=req.model_dump(),
                headers={"Authorization": f"Bearer {settings.controller_api_token}"},
            )
        if response.status_code >= 400:
            document.update({"status": "FAILED", "failure_details": response.text})
            await db_manager.insert_one("route_installations", document)
            raise HTTPException(status_code=502, detail="Controller rejected route installation")
        result = response.json()
        if result.get("status") == "INSTALLED":
            # The controller only proves its own registry; read the real OVS tables.
            check = await orchestrator.verify_route(req.source_ip, req.dest_ip, expected_path=req.path)
            result["datapath_verification"] = check
            if check["status"] != "UNAVAILABLE":
                result["verification_status"] = "VERIFIED" if check["verified"] else check["status"]
                result["verification_details"] = (
                    "Installed OVS flow tables match the requested route." if check["verified"]
                    else "; ".join(check["discrepancies"]) or check["status"])
        document.update(result)
        await db_manager.insert_one("route_installations", document)
        return result
    except httpx.HTTPError as exc:
        document.update({"status": "FAILED", "failure_details": str(exc)})
        await db_manager.insert_one("route_installations", document)
        raise HTTPException(status_code=502, detail="Controller management API is unavailable") from exc

@traffic_router.get("/api/metrics")
async def get_metrics():
    topo = topology_service.get_topology()
    total_bw = sum(l.current_rate_mbps for l in topo.links)
    avg_util = sum(l.utilization_pct for l in topo.links) / max(len(topo.links), 1)
    max_util = max((l.utilization_pct for l in topo.links), default=0.0)
    active_links = [l for l in topo.links if l.is_active]
    avg_latency = sum(l.latency_ms for l in active_links) / max(len(active_links), 1)
    active_flows = (controller_monitor.state or {}).get("flow_count", 0) if controller_monitor.status == "UP" else 0

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_switches": len(topo.switches),
        "total_hosts": len(topo.hosts),
        "total_links": len(topo.links),
        "active_flows": active_flows,
        "total_bandwidth_mbps": round(total_bw, 2),
        "avg_utilization_pct": round(avg_util, 2),
        "max_utilization_pct": round(max_util, 2),
        "congested_links_count": len([l for l in topo.links if l.utilization_pct >= 85.0]),
        "failed_links_count": len([l for l in topo.links if not l.is_active]),
        "avg_latency_ms": round(avg_latency, 2)
    }

@traffic_router.post("/api/network/traffic/start")
async def start_traffic(req: TrafficStartRequest):
    """Start a real iperf3 flow between two hosts of the running network."""
    if not network_agent.enabled:
        raise HTTPException(status_code=503, detail="No network agent attached: traffic cannot be generated")
    hosts = {h.name.lower() for h in topology_service.hosts.values()}
    for name in (req.src_host, req.dst_host):
        if name.lower() not in hosts:
            raise HTTPException(status_code=404, detail=f"Unknown host: {name}")
    try:
        return {"status": "SUCCESS", **await network_agent.traffic_start(
            req.src_host.lower(), req.dst_host.lower(), req.rate_mbps, req.duration_sec, req.protocol)}
    except AgentError as exc:
        raise _agent_http(exc) from exc


@traffic_router.post("/api/network/traffic/stop")
async def stop_traffic():
    if not network_agent.enabled:
        raise HTTPException(status_code=503, detail="No network agent attached")
    try:
        return {"status": "SUCCESS", **await network_agent.traffic_stop()}
    except AgentError as exc:
        raise _agent_http(exc) from exc

@traffic_router.post("/api/network/failure/simulate")
async def simulate_failure(req: FailureSimulateRequest):
    """Fail or restore a link: really (interface down in Mininet) when an agent is
    attached, and always in the model/controller."""
    is_active = req.action.upper() != "DOWN"
    try:
        _, change = await orchestrator.modify(
            f"Link {req.src_switch.lower()}-{req.dst_switch.lower()} {'restored' if is_active else 'failed'}",
            lambda: topology_service.set_link_state(req.src_switch, req.dst_switch, is_active),
            lambda _: network_agent.set_link_state(req.src_switch.lower(), req.dst_switch.lower(), is_active),
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Link not found: {req.src_switch}-{req.dst_switch}",
        ) from exc
    except AgentError as exc:
        raise _agent_http(exc) from exc
    return {
        "status": "SUCCESS",
        "link_id": f"{req.src_switch}-{req.dst_switch}",
        "action": req.action,
        "is_active": is_active,
        **change,
    }

@routing_router.get("/api/routing/verify")
async def verify_route_endpoint(source_ip: str, dest_ip: str):
    """Compare the calculated route with the flow entries installed in OVS."""
    try:
        routing_service.explain(source_ip, dest_ip)
    except UnknownHostError:
        raise HTTPException(status_code=404, detail=f"Unknown host pair: {source_ip} -> {dest_ip}")
    return await orchestrator.verify_route(source_ip, dest_ip)


@routing_router.get("/api/routing/verify/all")
async def verify_all_routes():
    """Verify every host pair against OVS and summarise the discrepancies."""
    return await orchestrator.verify_all()


@routing_router.get("/api/routing/decisions")
async def get_routing_decisions():
    return await db_manager.find("routing_decisions", limit=20)

@routing_router.post("/api/routing/recalculate")
async def recalculate_route(req: RecalculateRouteRequest):
    try:
        explanation = routing_service.explain(req.source_ip, req.dest_ip, req.qos_class, k=req.max_candidates)
    except UnknownHostError:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown host pair: {req.source_ip} -> {req.dest_ip}",
        )
    return {
        "status": "SUCCESS" if explanation["status"] == "ROUTE_FOUND" else "NO_ROUTE",
        "route_status": explanation["status"],
        "source": req.source_ip,
        "dest": req.dest_ip,
        "source_switch": explanation["source_switch"],
        "dest_switch": explanation["dest_switch"],
        "qos_class": req.qos_class,
        "weights": explanation["weights"],
        "formula": explanation["formula"],
        "excluded_links": explanation["excluded_links"],
        "candidate_paths": explanation["candidates"],
        "selected_path": explanation["selected_path"],
        "selected_cost": explanation["selected_cost"],
        "explanation": explanation["explanation"],
    }

@alerts_router.get("/api/alerts")
async def get_alerts():
    return await db_manager.find("alerts", limit=30)

@experiments_router.get("/api/experiments")
async def get_experiments():
    """Recorded experiment runs (none exist until an experiment runner is implemented)."""
    return await db_manager.find("experiments", limit=50)

@experiments_router.post("/api/experiments/start")
async def start_experiment(req: ExperimentStartRequest):
    raise HTTPException(status_code=501, detail="Automated experiments are not implemented")

@experiments_router.post("/api/experiments/stop")
async def stop_experiment():
    raise HTTPException(status_code=409, detail="No experiment is running")
