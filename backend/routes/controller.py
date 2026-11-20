"""Controller health, failover status and manual resynchronisation endpoints."""
from fastapi import APIRouter

from backend.services.runtime import controller_monitor

controller_router = APIRouter(tags=["Controller"])


@controller_router.get("/api/controller/status")
async def controller_status():
    """Heartbeat state, active endpoint, failover history and pending sync."""
    return controller_monitor.describe()


@controller_router.post("/api/controller/check")
async def controller_check():
    """Run one heartbeat cycle immediately and return the resulting status."""
    await controller_monitor.check_once()
    return controller_monitor.describe()


@controller_router.post("/api/controller/resync")
async def controller_resync():
    """Push the current topology snapshot to the active controller."""
    sync_status = await controller_monitor.sync_now()
    return {"sync_status": sync_status, **controller_monitor.describe()}
