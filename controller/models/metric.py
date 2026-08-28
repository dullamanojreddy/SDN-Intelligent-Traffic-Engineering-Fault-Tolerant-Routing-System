"""
Metrics and Telemetry Data Models
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class PortMetric(BaseModel):
    dpid: str
    port_no: int
    rx_packets: int = 0
    tx_packets: int = 0
    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_dropped: int = 0
    tx_dropped: int = 0
    rx_errors: int = 0
    tx_errors: int = 0
    duration_sec: int = 0
    rx_rate_mbps: float = 0.0
    tx_rate_mbps: float = 0.0
    utilization_pct: float = 0.0

class NetworkSummaryMetrics(BaseModel):
    timestamp: str
    total_switches: int = 0
    total_hosts: int = 0
    total_links: int = 0
    active_flows: int = 0
    total_bandwidth_mbps: float = 0.0
    avg_utilization_pct: float = 0.0
    max_utilization_pct: float = 0.0
    congested_links_count: int = 0
    failed_links_count: int = 0
    avg_latency_ms: float = 0.0
