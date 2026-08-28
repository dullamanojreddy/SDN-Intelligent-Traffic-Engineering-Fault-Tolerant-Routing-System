# System Architecture

## Overview
The SDN Intelligent Traffic Engineering & Fault-Tolerant Routing System (SDN-ITE) is organized into four distinct, decoupled layers:

```
[ Mininet Data Plane (OVS) ] <---OpenFlow 1.3---> [ Ryu SDN Controller ]
                                                           │
                                                      REST / IPC
                                                           │
                                                           ▼
[ React 18 / Vite / TS UI ] <---REST / WebSockets---> [ FastAPI Backend ]
                                                           │
                                                    Motor / PyMongo
                                                           ▼
                                                    [ MongoDB Server ]
```

---

## 1. Data Plane (Network Simulation)
- **Mininet**: Simulates software-defined network topologies with host endpoints and virtual Open vSwitches.
- **Open vSwitch (OVS)**: Handles OpenFlow 1.3 packet processing, matches against flow tables, applies output actions, and collects statistical telemetry (TX/RX bytes, drops, errors).
- **Traffic Tools**: `iperf3` for continuous high-rate TCP/UDP bandwidth generation; `ping` for RTT and jitter calculation.

---

## 2. Control Plane (SDN Controller)
Built on Python with the Ryu OpenFlow framework:
- **Topology Manager**: Listens to `EventSwitchEnter`, `EventLinkAdd`, and LLDP packet events to construct a live `NetworkX` graph.
- **Traffic Monitor**: Emits periodic `OFPPortStatsRequest` and `OFPFlowStatsRequest` packets (default interval: 2 seconds) and calculates instantaneous bandwidth utilization:
  $$\text{Utilization} = \frac{\Delta \text{Bytes} \times 8}{\Delta t \times \text{Capacity}} \times 100\%$$
- **Routing Engine**: Evaluates edge weights using the multi-metric cost function and calculates shortest paths using Dijkstra's algorithm.
- **Congestion Detector**: Implements a sliding window detector to detect persistent congestion ($\ge 85\%$ for $N$ consecutive intervals) and triggers traffic engineering rerouting.
- **Fault Recovery Engine**: Traps port status down notifications, flags broken links, and dynamically installs backup paths within sub-second intervals.
- **QoS Engine**: Adjusts cost function parameters based on flow classification headers (Voice, Video, Web, Background).

---

## 3. Backend Layer (FastAPI & Persistence)
- **FastAPI Core**: Provides high-throughput async REST endpoints for network topology, telemetry, flows, routing decisions, and experiment controls.
- **WebSocket Gateway**: Broadcaster pushing real-time network events (`TOPOLOGY_UPDATE`, `METRIC_UPDATE`, `LINK_CONGESTION`, `LINK_FAILURE`, `ROUTE_CHANGE`, `RECOVERY`) to connected dashboard clients.
- **MongoDB Connector**: Persists aggregated performance metrics, experiment results, routing histories, and system alerts.

---

## 4. Presentation Layer (Frontend Operations Dashboard)
- **React 18 + TypeScript + Vite**: Fast, typed single-page application.
- **Tailwind CSS + Lucide Icons**: Futuristic cyberpunk / dark glassmorphism network operations center (NOC) aesthetic.
- **Interactive Topology Visualizer**: Renders dynamic switch and host nodes, with edge colors reflecting real-time link health and bandwidth utilization (Green < 60%, Yellow 60-80%, Orange 80-90%, Red 90-100%, Dashed Red for Failed).
- **Recharts Analytics**: High-density time-series charts for bandwidth, latency, loss, and recovery time comparisons.
