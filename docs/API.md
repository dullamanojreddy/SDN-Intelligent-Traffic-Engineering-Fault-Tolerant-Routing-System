# Backend API & WebSocket Specification

## 1. REST Endpoints

### System & Health
- `GET /health` : Returns system health status and active component connectivity.
- `GET /api/system/status` : Detailed telemetry including controller connection, database connectivity, active switches, and memory metrics.

### Topology & Telemetry
- `GET /api/topology` : Full network graph containing switches, hosts, and active links with metrics.
- `GET /api/switches` : List of connected switches and their port configurations.
- `GET /api/links` : List of links with real-time utilization, latency, capacity, and failure state.
- `GET /api/hosts` : Discovered hosts, MACs, IP addresses, and switch attachment points.
- `GET /api/flows` : Active OpenFlow flow entries installed across switches.
- `GET /api/metrics` : Aggregated network metrics and time-series utilization.

### Intelligence & Decisions
- `GET /api/alerts` : Recent network alerts (Congestion, Link Failure, Route Change, Recovery).
- `GET /api/routing/decisions` : History of intelligent routing computations with cost comparisons.
- `POST /api/routing/recalculate` : Trigger manual or forced route recalculation.

### Experiments & Control
- `GET /api/experiments` : List past and running experiments.
- `POST /api/experiments/start` : Start an automated experiment scenario.
- `POST /api/experiments/stop` : Abort active experiment.
- `POST /api/network/traffic/start` : Initiate test traffic flows (iperf3).
- `POST /api/network/traffic/stop` : Terminate test traffic.
- `POST /api/network/failure/simulate` : Simulate link or switch failure.

---

## 2. WebSocket Protocol (`/ws/network`)

Clients connect via `ws://<host>:<port>/ws/network` to receive streaming JSON events:
```json
{
  "type": "METRIC_UPDATE",
  "timestamp": "2026-08-28T22:30:00Z",
  "data": {
    "total_bandwidth_mbps": 78.4,
    "avg_utilization_pct": 42.1,
    "active_flows": 14,
    "link_metrics": [
      { "link_id": "s1-s2", "utilization": 86.2, "status": "CONGESTED" }
    ]
  }
}
```

Supported Event Types:
- `TOPOLOGY_UPDATE`
- `METRIC_UPDATE`
- `LINK_CONGESTION`
- `LINK_FAILURE`
- `ROUTE_CHANGE`
- `RECOVERY`
- `ALERT`
- `FLOW_UPDATE`
- `EXPERIMENT_UPDATE`
