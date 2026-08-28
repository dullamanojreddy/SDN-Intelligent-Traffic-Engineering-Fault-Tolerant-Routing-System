# Experiments & Performance Benchmarks

## 1. Experiment Scenarios

### Experiment 1: Normal Baseline Traffic
- **Objective**: Measure latency, jitter, throughput, and packet loss in a nominal, uncongested state.
- **Traffic**: 10-30 Mbps constant bit rate between H1 and H8.
- **Expected Metrics**: Latency < 10ms, Packet Loss 0%, Utilization < 30%.

### Experiment 2: Elephant Flow Congestion & Dynamic Dijkstra Rerouting
- **Objective**: Evaluate intelligent rerouting when link utilization crosses the congestion threshold ($>85\%$).
- **Traffic**: Inject 95 Mbps traffic on primary path (`S1-S2-S5-S7`).
- **Trigger**: Utilization exceeds 85% for 3 consecutive monitoring intervals.
- **Expected Outcome**: Flow rerouted to secondary path (`S1-S3-S6-S7`). Latency normalizes, zero sustained packet drops.

### Experiment 3: Link Failure & Sub-Second Failover
- **Objective**: Measure detection latency and recovery time when an active link is abruptly severed.
- **Action**: Disable link `S2-S5` via Mininet `link s2 s5 down`.
- **Expected Outcome**: PortStatus DOWN event received, backup path (`S1-S3-S6-S7`) installed in $< 300\text{ ms}$, packet flow restored.

### Experiment 4: Multi-Link Simultaneous Failure
- **Objective**: Test topological resilience when multiple primary links fail concurrently.
- **Action**: Down `S2-S5` and `S3-S6`.
- **Expected Outcome**: Controller discovers diagonal path `S1-S2-S4-S7` or `S1-S3-S4-S7` and maintains connectivity.

### Experiment 5: Static vs Intelligent SDN Routing Benchmark
- **Objective**: Direct quantitative comparison across variable load steps (10M, 25M, 50M, 75M, 100M).
- **Comparison Dimensions**:
  1. Average Throughput (Mbps)
  2. End-to-End Latency (ms)
  3. Packet Loss (%)
  4. Link Utilization Balance (%)
  5. Recovery Time from Outage (ms)
