"""
Integration tests for FastAPI backend endpoints
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

def test_system_status():
    res = client.get("/api/system/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ONLINE"
    assert data["active_switches"] >= 4

def test_topology_discovery():
    res = client.get("/api/topology")
    assert res.status_code == 200
    topo = res.json()
    assert "switches" in topo
    assert "links" in topo
    assert len(topo["switches"]) >= 4

def test_recalculate_route():
    res = client.post("/api/routing/recalculate", json={
        "source_ip": "10.0.0.1",
        "dest_ip": "10.0.0.8",
        "qos_class": "VIDEO"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert len(data["candidate_paths"]) > 0
