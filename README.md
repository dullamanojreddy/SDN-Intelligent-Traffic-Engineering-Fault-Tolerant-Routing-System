# SDN Intelligent Traffic Engineering & Fault-Tolerant Routing System (SDN-ITE)

[![Status](https://img.shields.io/badge/Status-Final_Draft_Complete-emerald.svg)](https://github.com/dullamanojreddy/SDN-Intelligent-Traffic-Engineering-Fault-Tolerant-Routing-System)
[![OpenFlow](https://img.shields.io/badge/OpenFlow-1.3-blue.svg)](https://opennetworking.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.110-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React_18_Vite-61DAFB.svg)](https://react.dev)

> An SDN-based intelligent traffic engineering platform that centrally monitors network topology and link conditions, computes optimized routes using network-performance metrics, installs forwarding rules through the SDN controller, detects congestion and failures, automatically reroutes affected traffic, and evaluates improvements using latency, throughput, packet loss, link utilization, and recovery-time metrics through a real-time visualization dashboard.

---

## System Architecture
```
                         ┌─────────────────────────────┐
                         │   React Operations UI       │
                         │ (Dashboard, Topology, Flows,│
                         │  Routing, Alerts, Exps)     │
                         └──────────────┬──────────────┘
                                        │ REST + WebSocket
                         ┌──────────────▼──────────────┐
                         │       FastAPI Backend       │
                         │ (Services, DB, WS Gateway,  │
                         │  Controller REST Interface) │
                         └──────────────┬──────────────┘
                                        │ IPC / REST / Events
                         ┌──────────────▼──────────────┐
                         │       SDN Controller        │
                         │ (Ryu, TopologyMgr, Routing, │
                         │  Monitor, Congestion, Fault)│
                         └──────────────┬──────────────┘
                                        │ OpenFlow 1.3
                  ┌─────────────────────┼──────────────────────┐
                  │                     │                      │
               Open vSwitch          Open vSwitch           Open vSwitch
                  │                     │                      │
                 S1                    S2                     S3
                  │                     │                      │
                  └─────────────────────┼──────────────────────┘
                                        │
                                 Mininet Hosts
```

---

## Features
- **Dynamic Topology Discovery**: Real-time switch, port, host, and link mapping via OpenFlow 1.3 & LLDP.
- **Multi-Metric Dijkstra Routing**: Graph routing factoring in normalized latency, link utilization, and packet drops:
  $$\text{Cost} = \alpha \cdot \text{latency} + \beta \cdot \text{utilization} + \gamma \cdot \text{loss}$$
- **Stateful Congestion Detection**: Hysteresis-aware persistence monitoring ($U \ge 85\%$ for $N$ cycles) to avoid unnecessary route flapping.
- **Dynamic Rerouting**: Automatic migration of elephant flows to under-utilized alternate paths.
- **Sub-Second Fault Recovery**: Fast failover upon link/port status down detection.
- **QoS Class Prioritization**: Adaptive weights for Voice, Video, Web, and Background traffic.
- **High-Density Cyberpunk UI**: Sleek dark network operations center dashboard with real-time SVG topology visualization and Recharts telemetry.
- **In-Memory & MongoDB Resilience**: Automatic graceful fallback to in-memory storage if MongoDB is offline.

---

## Quick Start

### 1. Requirements & Setup
- Python 3.10+
- Node.js 18+ & npm
- Mininet & Open vSwitch (on Linux or WSL2)

```bash
# Python Backend & Controller dependencies
pip install -r requirements.txt

# Frontend dependencies
cd frontend
npm install
```

### 2. Running the System
```bash
# Terminal 1: SDN Controller
python controller/app.py

# Terminal 2: FastAPI Backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 3: Frontend Dashboard
cd frontend
npm run dev

# Terminal 4: Mininet Network (in Linux/WSL)
sudo python network/topologies/mesh.py
```

---

## Documentation
- [Project Context & AI Memory](docs/PROJECT_CONTEXT.md)
- [System Architecture](docs/ARCHITECTURE.md)
- [Network Design](docs/NETWORK_DESIGN.md)
- [Controller Architecture](docs/CONTROLLER.md)
- [API & WebSocket Specification](docs/API.md)
- [Database Schema](docs/DATABASE.md)
- [Experiments Guide](docs/EXPERIMENTS.md)
- [Environment Setup](docs/SETUP.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
