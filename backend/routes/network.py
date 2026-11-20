"""Live-network attachment: reconciliation between the model and Mininet."""
from typing import Literal

from fastapi import APIRouter

from backend.services.runtime import orchestrator

network_router = APIRouter(tags=["Network"])


@network_router.get("/api/network/status")
async def network_status():
    """Is a live network agent attached, and does the model match the network?"""
    return await orchestrator.network_status()


@network_router.post("/api/network/reconcile")
async def network_reconcile(mode: Literal["report", "adopt"] = "report"):
    """``report`` lists drift; ``adopt`` makes the running network the new model."""
    return await orchestrator.reconcile(mode)
