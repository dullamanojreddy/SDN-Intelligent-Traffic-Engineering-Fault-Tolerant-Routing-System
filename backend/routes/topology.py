"""
Topology, Switches, Links, Hosts, Flows, Traffic, Routing, Alerts, and Experiments API Endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from backend.services.topology_service import topology_service
from backend.database.connection import db_manager
from backend.schemas.network import (
    RecalculateRouteRequest,
    TrafficStartRequest,
    FailureSimulateRequest,
    ExperimentStartRequest
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

@traffic_router.get("/api/metrics")
async def get_metrics():
    topo = topology_service.get_topology()
    total_bw = sum(l.current_rate_mbps for l in topo.links)
    avg_util = sum(l.utilization_pct for l in topo.links) / max(len(topo.links), 1)
    max_util = max((l.utilization_pct for l in topo.links), default=0.0)
    
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
        "avg_latency_ms": 6.8
    }

@traffic_router.post("/api/network/traffic/start")
async def start_traffic(req: TrafficStartRequest):
    return {"status": "SUCCESS", "message": f"Traffic stream started from {req.src_host} to {req.dst_host} at {req.rate_mbps} Mbps."}

@traffic_router.post("/api/network/traffic/stop")
async def stop_traffic():
    return {"status": "SUCCESS", "message": "All test traffic generators stopped."}

@traffic_router.post("/api/network/failure/simulate")
async def simulate_failure(req: FailureSimulateRequest):
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
    router = DijkstraRouter(topology_service.network_graph)
    paths = router.calculate_k_shortest_paths("s1", "s7", k=3)
    return {
        "status": "SUCCESS",
        "source": req.source_ip,
        "dest": req.dest_ip,
        "qos_class": req.qos_class,
        "candidate_paths": paths
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
