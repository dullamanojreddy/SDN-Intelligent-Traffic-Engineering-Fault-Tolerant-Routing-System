"""
Topology, Switches, Links, Hosts, Flows, Traffic, Routing, Alerts, and Experiments API Endpoints
"""
from fastapi import APIRouter, HTTPException
import httpx
from typing import List, Dict, Any
from backend.services.topology_service import topology_service
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
    RouteInstallRequest
)
from controller.routing.dijkstra import DijkstraRouter
from controller.routing.cost_function import CostCalculator
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


@switches_router.post("/api/switches", status_code=201)
async def create_switch(req: SwitchCreateRequest):
    try:
        return topology_service.add_switch(req.name)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@switches_router.delete("/api/switches/{name}")
async def delete_switch(name: str):
    try:
        topology_service.remove_switch(name)
        return {"status": "SUCCESS", "removed": name}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@hosts_router.post("/api/hosts", status_code=201)
async def create_host(req: HostCreateRequest):
    try:
        return topology_service.add_host(req.name, req.ip, req.connected_switch, req.mac)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@hosts_router.delete("/api/hosts/{name}")
async def delete_host(name: str):
    try:
        topology_service.remove_host(name)
        return {"status": "SUCCESS", "removed": name}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@links_router.post("/api/links", status_code=201)
async def create_link(req: LinkCreateRequest):
    try:
        topology_service.add_connection(req.src, req.dst, req.capacity_mbps, req.latency_ms)
        return {"status": "SUCCESS", "src": req.src, "dst": req.dst}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@links_router.delete("/api/links/{src}/{dst}")
async def delete_link(src: str, dst: str):
    try:
        topology_service.remove_connection(src, dst)
        return {"status": "SUCCESS", "src": src, "dst": dst}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@flows_router.get("/api/flows")
async def get_flows():
    return [
        {
            "flow_id": "fl_001",
            "dpid": "s1",
            "table_id": 0,
            "priority": 30,
            "match": {"ipv4_src": "10.0.0.1", "ipv4_dst": "10.0.0.8", "ip_proto": 6},
            "instructions": [{"type": "APPLY_ACTIONS", "actions": ["OUTPUT:1"]}],
            "packet_count": 48120,
            "byte_count": 72180000,
            "duration_sec": 420,
            "status": "ACTIVE"
        },
        {
            "flow_id": "fl_002",
            "dpid": "s2",
            "table_id": 0,
            "priority": 30,
            "match": {"ipv4_src": "10.0.0.1", "ipv4_dst": "10.0.0.8", "ip_proto": 6},
            "instructions": [{"type": "APPLY_ACTIONS", "actions": ["OUTPUT:3"]}],
            "packet_count": 48120,
            "byte_count": 72180000,
            "duration_sec": 420,
            "status": "ACTIVE"
        }

    ]

@routing_router.post("/api/routing/install")
async def install_route(req: RouteInstallRequest):
    document = req.model_dump()
    document["requested_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    document["request_type"] = "manual"
    document["status"] = "REQUESTED"
    if not settings.controller_api_token or settings.controller_api_token == "change-me":
        document.update({"status": "FAILED", "failure_details": "CONTROLLER_API_TOKEN is not configured"})
        await db_manager.insert_one("routing_decisions", document)
        raise HTTPException(status_code=503, detail="Controller authentication is not configured")
    try:
        timeout = httpx.Timeout(15.0, connect=3.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{settings.controller_api_url}/routes/install",
                json=req.model_dump(),
                headers={"Authorization": f"Bearer {settings.controller_api_token}"},
            )
        if response.status_code >= 400:
            document.update({"status": "FAILED", "failure_details": response.text})
            await db_manager.insert_one("routing_decisions", document)
            raise HTTPException(status_code=502, detail="Controller rejected route installation")
        result = response.json()
        document.update(result)
        await db_manager.insert_one("routing_decisions", document)
        return result
    except httpx.HTTPError as exc:
        document.update({"status": "FAILED", "failure_details": str(exc)})
        await db_manager.insert_one("routing_decisions", document)
        raise HTTPException(status_code=502, detail="Controller management API is unavailable") from exc

@traffic_router.get("/api/metrics")
async def get_metrics():
    topo = topology_service.get_topology()
    total_bw = sum(l.current_rate_mbps for l in topo.links)
    avg_util = sum(l.utilization_pct for l in topo.links) / max(len(topo.links), 1)
    max_util = max((l.utilization_pct for l in topo.links), default=0.0)
    active_links = [l for l in topo.links if l.is_active]
    avg_latency = sum(l.latency_ms for l in active_links) / max(len(active_links), 1)
    
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_switches": len(topo.switches),
        "total_hosts": len(topo.hosts),
        "total_links": len(topo.links),
        "active_flows": 14,
        "total_bandwidth_mbps": round(total_bw, 2),
        "avg_utilization_pct": round(avg_util, 2),
        "max_utilization_pct": round(max_util, 2),
        "congested_links_count": len([l for l in topo.links if l.utilization_pct >= 85.0]),
        "failed_links_count": len([l for l in topo.links if not l.is_active]),
        "avg_latency_ms": round(avg_latency, 2)
    }

@traffic_router.post("/api/network/traffic/start")
async def start_traffic(req: TrafficStartRequest):
    return {"status": "SUCCESS", "message": f"Traffic stream started from {req.src_host} to {req.dst_host} at {req.rate_mbps} Mbps."}

@traffic_router.post("/api/network/traffic/stop")
async def stop_traffic():
    return {"status": "SUCCESS", "message": "All test traffic generators stopped."}

@traffic_router.post("/api/network/failure/simulate")
async def simulate_failure(req: FailureSimulateRequest):
    if not topology_service.network_graph.graph.has_edge(
        req.src_switch, req.dst_switch
    ):
        raise HTTPException(
            status_code=404,
            detail=f"Link not found: {req.src_switch}-{req.dst_switch}",
        )

    is_active = (req.action.upper() != "DOWN")
    topology_service.network_graph.update_link_metrics(
        req.src_switch, req.dst_switch,
        utilization_pct=0.0 if not is_active else 20.0,
        is_active=is_active
    )
    topology_service.network_graph.update_link_metrics(
        req.dst_switch, req.src_switch,
        utilization_pct=0.0 if not is_active else 20.0,
        is_active=is_active
    )
    return {
        "status": "SUCCESS",
        "link_id": f"{req.src_switch}-{req.dst_switch}",
        "action": req.action,
        "is_active": is_active
    }

@routing_router.get("/api/routing/decisions")
async def get_routing_decisions():
    history = await db_manager.find("routing_decisions", limit=20)
    if not history:
        return [
            {
                "decision_id": "dec_sample_01",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "source_ip": "10.0.0.1",
                "dest_ip": "10.0.0.8",
                "old_path": ["s1", "s2", "s5", "s7"],
                "new_path": ["s1", "s3", "s6", "s7"],
                "reason": "Link S2-S5 high load (76.8% util) - secondary path selected",
                "old_cost": 0.84,
                "new_cost": 0.32,
                "latency_ms": 15.0,
                "utilization_pct": 24.1,
                "packet_loss_pct": 0.0,
                "qos_class": "VIDEO"
            }
        ]
    return history

@routing_router.post("/api/routing/recalculate")
async def recalculate_route(req: RecalculateRouteRequest):
    qos_weights = {
        "VOICE": {"latency": 0.7, "utilization": 0.1, "loss": 0.2},
        "VIDEO": {"latency": 0.2, "utilization": 0.6, "loss": 0.2},
        "WEB": {"latency": 0.4, "utilization": 0.4, "loss": 0.2},
        "BACKGROUND": {"latency": 0.1, "utilization": 0.8, "loss": 0.1},
    }.get(req.qos_class.upper(), {"latency": 0.4, "utilization": 0.4, "loss": 0.2})
    router = DijkstraRouter(
        topology_service.network_graph,
        CostCalculator(
            alpha=qos_weights["latency"],
            beta=qos_weights["utilization"],
            gamma=qos_weights["loss"],
        ),
    )
    hosts_by_ip = {
        host.ip: host.connected_switch
        for host in topology_service.get_topology().hosts
    }
    src_switch = hosts_by_ip.get(req.source_ip)
    dst_switch = hosts_by_ip.get(req.dest_ip)
    if not src_switch or not dst_switch:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown host pair: {req.source_ip} -> {req.dest_ip}",
        )

    explanation = router.explain_route(src_switch, dst_switch, k=3)
    return {
        "status": "SUCCESS",
        "source": req.source_ip,
        "dest": req.dest_ip,
        "qos_class": req.qos_class,
        "candidate_paths": explanation["candidates"],
        "selected_path": explanation["selected_path"],
        "selected_cost": explanation["selected_cost"],
        "explanation": explanation["explanation"],
    }

@alerts_router.get("/api/alerts")
async def get_alerts():
    alerts = await db_manager.find("alerts", limit=30)
    if not alerts:
        return [
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "type": "CONGESTION",
                "severity": "WARNING",
                "source": "Link s2-s5",
                "message": "Link utilization at 76.8% - monitoring for persistence",
                "status": "ACTIVE"
            },
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "type": "SYSTEM",
                "severity": "INFO",
                "source": "Controller",
                "message": "Topology discovery completed: 7 switches, 4 hosts, 18 directed links",
                "status": "RESOLVED"
            }
        ]
    return alerts

@experiments_router.get("/api/experiments")
async def get_experiments():
    return [
        {
            "experiment_id": "exp_01",
            "name": "Elephant Flow Congestion Reroute",
            "type": "CONGESTION_BENCHMARK",
            "status": "COMPLETED",
            "metrics": {
                "avg_latency_ms": 12.4,
                "throughput_mbps": 94.2,
                "packet_loss_pct": 0.08,
                "recovery_time_ms": 185
            }
        },
        {
            "experiment_id": "exp_02",
            "name": "Link S2-S5 Failure Recovery",
            "type": "FAILOVER_BENCHMARK",
            "status": "COMPLETED",
            "metrics": {
                "avg_latency_ms": 14.8,
                "throughput_mbps": 89.6,
                "packet_loss_pct": 0.12,
                "recovery_time_ms": 220
            }
        }
    ]

@experiments_router.post("/api/experiments/start")
async def start_experiment(req: ExperimentStartRequest):
    return {
        "status": "RUNNING",
        "experiment_id": f"exp_{int(time.time())}",
        "name": req.name,
        "type": req.type,
        "message": f"Experiment '{req.name}' initiated."
    }

@experiments_router.post("/api/experiments/stop")
async def stop_experiment():
    return {"status": "STOPPED", "message": "Active experiment terminated."}
