# Database Specification (MongoDB)

## 1. Overview
The platform uses MongoDB to persist aggregated performance records, experiment results, route decisions, fault events, and system alerts.

## 2. Collections & Schema

### `experiments`
Stores experiment runs, parameters, and evaluated results.
```json
{
  "_id": "ObjectId(...)",
  "experiment_id": "exp_20260828_01",
  "name": "Congestion Dynamic Rerouting Benchmark",
  "type": "CONGESTION_TEST",
  "start_time": "2026-08-28T22:00:00Z",
  "end_time": "2026-08-28T22:05:00Z",
  "topology": "mesh_topo",
  "traffic_profile": { "rate_mbps": 90, "duration_sec": 60 },
  "metrics": {
    "avg_latency_ms": 12.4,
    "throughput_mbps": 88.5,
    "packet_loss_pct": 0.12,
    "recovery_time_ms": 180
  },
  "result": "PASSED",
  "status": "COMPLETED"
}
```

### `network_metrics`
Time-series port and flow statistics aggregated per monitor interval.
```json
{
  "timestamp": "2026-08-28T22:01:00Z",
  "switch_id": "s1",
  "port": 2,
  "tx_bytes": 104857600,
  "rx_bytes": 104857600,
  "tx_packets": 70000,
  "rx_packets": 70000,
  "utilization": 84.5,
  "packet_loss_pct": 0.05,
  "errors": 0
}
```

### `routing_decisions`
Audit trail of path computations and intelligent reroutes.
```json
{
  "timestamp": "2026-08-28T22:01:10Z",
  "source_ip": "10.0.0.1",
  "dest_ip": "10.0.0.8",
  "old_path": ["s1", "s2", "s5", "s7"],
  "new_path": ["s1", "s3", "s6", "s7"],
  "reason": "Link S2-S5 utilization exceeded threshold (92.4%)",
  "old_cost": 84.2,
  "new_cost": 31.5,
  "qos_class": "VIDEO"
}
```

### `fault_events`
Records of link and switch outages and recovery timings.
```json
{
  "timestamp": "2026-08-28T22:02:00Z",
  "device": "s2",
  "link": "s2-s5",
  "failure_type": "LINK_DOWN",
  "detection_time_ms": 140,
  "recovery_time_ms": 230,
  "affected_flows": 3,
  "old_path": ["s1", "s2", "s5", "s7"],
  "new_path": ["s1", "s3", "s6", "s7"]
}
```

### `alerts`
System alerts for real-time notification.
```json
{
  "timestamp": "2026-08-28T22:01:10Z",
  "type": "CONGESTION",
  "severity": "WARNING",
  "source": "Link s2-s5",
  "message": "Link utilization at 92.4% - dynamic reroute triggered",
  "status": "RESOLVED"
}
```
