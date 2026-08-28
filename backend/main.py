"""
FastAPI Backend Application Entrypoint (Final Draft Production Release)
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from backend.config.settings import settings
from backend.database.connection import db_manager
from backend.websocket.manager import ws_manager
from backend.routes.system import router as system_router
from backend.routes.topology import (
    topology_router,
    switches_router,
    links_router,
    hosts_router,
    flows_router,
    traffic_router,
    routing_router,
    alerts_router,
    experiments_router
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing SDN-ITE FastAPI Backend...")
    await db_manager.connect()
    yield
    # Shutdown
    logger.info("Shutting down SDN-ITE FastAPI Backend...")
    await db_manager.close()

app = FastAPI(
    title="SDN Intelligent Traffic Engineering API",
    description="FastAPI Backend for SDN-ITE Platform (Mininet + OVS + Ryu + MongoDB + React)",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list if settings.cors_list else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST Routers
app.include_router(system_router)
app.include_router(topology_router)
app.include_router(switches_router)
app.include_router(links_router)
app.include_router(hosts_router)
app.include_router(flows_router)
app.include_router(traffic_router)
app.include_router(routing_router)
app.include_router(alerts_router)
app.include_router(experiments_router)

# WebSocket Endpoint
@app.websocket("/ws/network")
async def websocket_network_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo or process incoming command messages
            await websocket.send_json({"status": "ACK", "received": data})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.backend_host, port=settings.backend_port, reload=True)
