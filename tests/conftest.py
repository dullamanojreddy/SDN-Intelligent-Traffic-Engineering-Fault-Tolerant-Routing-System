"""Shared fixtures: a scriptable fake controller and backend state reset."""
import socket
from typing import Any, Dict, List

import httpx
import pytest


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class FakeController:
    """httpx MockTransport handler emulating the controller management API.

    ``up=False`` makes every request fail like a dead process would. Several
    instances can share one transport via ``FakeCluster`` to model standbys.
    """

    def __init__(self, name: str = "primary"):
        self.name = name
        self.up = True
        self.syncs: List[Dict[str, Any]] = []
        self.applied_version = 0
        self.utilization: Dict[str, float] = {}
        self.reject_with: int = 0
        self.flows = 0

    def handle(self, request: httpx.Request) -> httpx.Response:
        if not self.up:
            raise httpx.ConnectError("connection refused", request=request)
        if request.headers.get("authorization") != "Bearer test-token":
            return httpx.Response(401, json={"detail": "Unauthorized"})
        path = request.url.path
        if path == "/health":
            return httpx.Response(200, json={"status": "ok", "connected_switches": 7})
        if path == "/state":
            snap = self.syncs[-1] if self.syncs else {"switches": [], "links": []}
            links = []
            for link in snap["links"]:
                for a, b in ((link["src"], link["dst"]), (link["dst"], link["src"])):
                    links.append({
                        "src": a, "dst": b, "is_active": link["is_active"],
                        "utilization_pct": self.utilization.get(f"{a}-{b}", 0.0),
                        "loss_pct": 0.0, "data_plane_confirmed": True,
                    })
            return httpx.Response(200, json={
                "controller_id": self.name,
                "topology_version": self.applied_version,
                "switches": [{"dpid": s, "connected": True, "active_flows": 2} for s in snap["switches"]],
                "links": links, "flow_count": self.flows,
            })
        if path == "/topology/sync":
            if self.reject_with:
                return httpx.Response(self.reject_with, json={"detail": "rejected"})
            import json
            body = json.loads(request.content)
            if body["version"] < self.applied_version:
                return httpx.Response(409, json={"detail": "stale", "applied_version": self.applied_version})
            self.syncs.append(body)
            self.applied_version = body["version"]
            return httpx.Response(200, json={"status": "APPLIED"})
        return httpx.Response(404, json={"detail": "Not found"})


class FakeCluster:
    """Routes requests to a FakeController by URL port, as separate hosts would."""

    def __init__(self, **controllers: FakeController):
        self.by_port = {}
        self.ports = {}
        for name, controller in controllers.items():
            port = 9000 + len(self.by_port)
            self.by_port[port] = controller
            self.ports[name] = f"http://127.0.0.1:{port}"
        self.transport = httpx.MockTransport(self.handle)

    def handle(self, request: httpx.Request) -> httpx.Response:
        return self.by_port[request.url.port].handle(request)


@pytest.fixture
def token(monkeypatch):
    from backend.config.settings import settings
    monkeypatch.setattr(settings, "controller_api_token", "test-token")
    return "test-token"


@pytest.fixture
def fresh_backend(token):
    """Reset the backend singletons to a clean 7-switch mesh before and after."""
    from backend.database.connection import db_manager
    from backend.services.runtime import controller_monitor, routing_service
    from backend.services.topology_service import topology_service

    def reset():
        topology_service.__init__()
        routing_service.current.clear()
        routing_service.refresh("Initial topology")
        for name in db_manager.in_memory_store:
            db_manager.in_memory_store[name].clear()
        db_manager.is_connected = False
        controller_monitor.status = "UNKNOWN"
        controller_monitor.state = None
        controller_monitor.pending_sync = False
        controller_monitor.synced_version = None
        controller_monitor.transport = None
        controller_monitor.active_index = 0
        controller_monitor.consecutive_failures = 0
        controller_monitor.history.clear()

    reset()
    yield
    reset()


class FakeAgent:
    """Scriptable stand-in for the Mininet network agent (HTTP level)."""

    def __init__(self):
        self.calls = []
        self.fail_next = None          # (status, detail) for the next mutating call
        self.up = True
        self.flows = {}
        self.topology = None

    def handle(self, request):
        import json
        if not self.up:
            raise httpx.ConnectError("agent down", request=request)
        if request.headers.get("authorization") != "Bearer agent-token":
            return httpx.Response(401, json={"detail": "Unauthorized"})
        body = json.loads(request.content) if request.content else None
        path = request.url.path
        if request.method == "GET" and path == "/topology":
            return httpx.Response(200, json=self.topology)
        if request.method == "GET" and path == "/flows":
            return httpx.Response(200, json={"flows": self.flows})
        self.calls.append((request.method, path, body))
        if self.fail_next:
            status, detail = self.fail_next
            self.fail_next = None
            return httpx.Response(status, json={"detail": detail})
        return httpx.Response(200, json={"status": "OK"})


@pytest.fixture
def fake_agent(fresh_backend):
    """Attach a FakeAgent to the backend orchestrator for the test."""
    from backend.services.network_agent import NetworkAgentClient
    from backend.services.runtime import network_agent, orchestrator
    fake = FakeAgent()
    previous = (network_agent.url, network_agent.token, network_agent.transport)
    network_agent.url, network_agent.token = "http://agent.test", "agent-token"
    network_agent.transport = httpx.MockTransport(fake.handle)
    yield fake
    network_agent.url, network_agent.token, network_agent.transport = previous
