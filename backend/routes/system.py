"""
System & Health Routes
"""
from fastapi import APIRouter
from backend.schemas.network import SystemStatusResponse
from backend.services.topology_service import topology_service
from backend.database.connection import db_manager
from backend.services.runtime import controller_monitor
import time

router = APIRouter(tags=["System"])
start_time = time.time()

@router.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": time.time()}

@router.get("/api/system/status", response_model=SystemStatusResponse)
async def get_system_status():
    topo = topology_service.get_topology()
    return SystemStatusResponse(
        status="ONLINE",
        version="1.0.0",
        environment="development",
        controller_connected=controller_monitor.status == "UP",
        database_connected=db_manager.is_connected,
        database_mode="MONGODB" if db_manager.is_connected else "IN_MEMORY",
        active_switches=len(topo.switches),
        active_hosts=len(topo.hosts),
        active_links=len(topo.links),
        active_flows=(controller_monitor.state or {}).get("flow_count", 0) if controller_monitor.status == "UP" else 0,
        uptime_sec=round(time.time() - start_time, 2)
    )
