# Project Context

## Project
**SDN Intelligent Traffic Engineering & Fault-Tolerant Routing System (SDN-ITE)**

## Objective
Build an SDN-based intelligent traffic engineering platform that centrally monitors network topology and link conditions, computes optimized routes using network-performance metrics (latency, utilization, loss), installs forwarding rules through an OpenFlow 1.3 SDN controller (Ryu), detects congestion and link/switch failures, automatically reroutes affected traffic, and provides real-time visualization and analytics via a FastAPI backend, MongoDB persistence, and a high-performance React/TypeScript dashboard.

## Technology Stack
- **Network Simulation & Data Plane**: Mininet, Open vSwitch (OVS), OpenFlow 1.3, Linux networking utilities, iperf3, ping.
- **SDN Controller**: Python 3, Ryu SDN Framework, NetworkX / custom Graph algorithms.
- **Backend API & Real-time**: Python 3, FastAPI, Uvicorn, WebSockets, Pydantic v2, Motor / PyMongo (MongoDB).
- **Frontend Dashboard**: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, Recharts, React Router.
- **Testing & Quality Assurance**: Pytest, Pytest-asyncio, HTTPX, Jest/Vitest.

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

## Network Architecture
The data plane runs OpenFlow 1.3 enabled Open vSwitch instances connected to hosts. The control plane operates out-of-band via Ryu controller communicating over TCP port 6653/6633.

## Network Topology
- **Basic Redundant Diamond**: S1 connected to S2 and S3; S2 and S3 connected to S4. S1 has H1, S4 has H4.
- **Fault-Tolerant Multi-Path Mesh (Target)**: S1 connected to S2, S3; S2 connected to S4, S5; S3 connected to S4, S6; S5 and S6 connected to S4/destination hosts. Redundant paths allow dynamic rerouting during heavy load and automatic failover during link outages.

## Controller Architecture
Modular architecture consisting of:
- `TopologyManager`: Discovers switches, ports, links (LLDP), and host attachments.
- `FlowManager`: Safe OpenFlow 1.3 flow rule generation, installation, removal, and bidirectional path programming.
- `TrafficMonitor`: Periodic OpenFlow port/flow statistics polling with rate computation.
- `RoutingEngine`: Graph cost calculation & multi-metric Dijkstra path computation.
- `CongestionDetector`: Moving window threshold & persistence evaluation to trigger traffic engineering.
- `FailureDetector` & `RecoveryEngine`: Port status & link down detection triggering sub-second route recalculation.
- `QoSEngine`: Traffic classification (Voice, Video, Web, Background) with prioritized metric weights.
- `EventManager`: Dispatches internal controller events to FastAPI backend / WebSocket clients.

## Routing Algorithm
Multi-metric Dijkstra path optimizer evaluating normalized edge costs:
$$\text{Cost}(e) = \alpha \cdot \text{norm\_latency}(e) + \beta \cdot \text{norm\_utilization}(e) + \gamma \cdot \text{norm\_loss}(e)$$
Where weights $\alpha, \beta, \gamma$ are dynamically configured per QoS class or global policy.

## Traffic Engineering
Monitors link utilization ($U = \text{traffic\_rate} / \text{capacity} \times 100\%$). When $U > \text{threshold}$ (e.g. 85%) persists across $N$ cycles, affected elephant flows are identified and rerouted across lower-cost alternate candidate paths with anti-flapping hysteresis and cooldown timers.

## Congestion Detection
Stateful detector tracking rolling statistics:
- Threshold: 80-90% utilization (configurable)
- Persistence: $N$ consecutive monitoring cycles (prevents transient burst rerouting)
- Cooldown timer: Prevents route oscillation / flapping.

## Fault Detection
Listens for OpenFlow `OFPPortStatus` messages and link loss events in the LLDP topology graph. Instantly flags severed edges.

## Fault Recovery
Identifies all active flows traversing the severed link, removes stale flow entries, computes backup Dijkstra routes avoiding the failed edge, programs new OpenFlow rules, and logs precise detection and recovery durations.

## QoS
4 Traffic Classes with customized cost weights:
1. **VOICE (High Priority)**: $\alpha=0.7, \beta=0.1, \gamma=0.2$ (Ultra-low latency)
2. **VIDEO (High Priority)**: $\alpha=0.2, \beta=0.6, \gamma=0.2$ (High bandwidth)
3. **WEB (Medium Priority)**: $\alpha=0.4, \beta=0.4, \gamma=0.2$ (Balanced)
4. **BACKGROUND (Low Priority)**: $\alpha=0.1, \beta=0.8, \gamma=0.1$ (Best effort)

## Database
MongoDB with collections:
- `experiments`: Test definitions, run history, and result metrics.
- `network_metrics`: Time-series aggregated port and flow rates.
- `routing_decisions`: Historical logs of path changes and reasoning.
- `fault_events`: Link failure and recovery timing records.
- `alerts`: System, congestion, and failure notifications.

## API Architecture
FastAPI REST endpoints:
- `GET /health`
- `GET /api/topology`
- `GET /api/switches`
- `GET /api/links`
- `GET /api/hosts`
- `GET /api/flows`
- `GET /api/metrics`
- `GET /api/alerts`
- `GET /api/routing/decisions`
- `GET /api/experiments`
- `GET /api/system/status`
- `POST /api/experiments/start` & `stop`
- `POST /api/network/traffic/start` & `stop`
- `POST /api/network/failure/simulate`
- `POST /api/routing/recalculate`

## WebSocket Architecture
Endpoint: `/ws/network`
Broadcasts real-time events: `TOPOLOGY_UPDATE`, `METRIC_UPDATE`, `LINK_CONGESTION`, `LINK_FAILURE`, `ROUTE_CHANGE`, `RECOVERY`, `ALERT`, `FLOW_UPDATE`, `EXPERIMENT_UPDATE`.

## Frontend Architecture
Dark Network Operations Dashboard aesthetic with neon/purple cyber accents (glassmorphism):
- Pages: `/dashboard`, `/topology`, `/traffic`, `/flows`, `/routing`, `/alerts`, `/experiments`, `/settings`.
- Dedicated hooks and services: `api.ts`, `websocket.ts`.
- Interactive SVG network topology visualizer with real-time link utilization color codes and node inspector.

## Completed Features
- [x] Foundation & Repository Architecture (Milestone 1)
- [x] Project Context & AI Memory System (`docs/PROJECT_CONTEXT.md`)
- [x] Complete System Documentation (`docs/*.md`, `README.md`)
- [x] Backend Skeleton (FastAPI, WebSocket Manager, Pydantic Schemas, Mongo fallback)
- [x] Controller Skeleton & Routing Core (Dijkstra algorithm, multi-metric cost functions, topology manager)
- [x] Frontend Skeleton (Vite, React 18, TypeScript, Tailwind CSS, Dark Theme layout, 8 operational pages)
- [x] Mininet Topology definitions & generator scripts
- [x] Windows / Linux / WSL startup scripts and configuration templates
- [x] Unit and Integration test harnesses (10/10 tests passing)
- [x] Frontend production build verified (`tsc && vite build` passing)

## Current Status
**Milestone 1 (Foundation) Completed and Fully Verified**.

## Changed Files
- `docs/PROJECT_CONTEXT.md`
- `docs/ARCHITECTURE.md`
- `docs/NETWORK_DESIGN.md`
- `docs/CONTROLLER.md`
- `docs/API.md`
- `docs/DATABASE.md`
- `docs/EXPERIMENTS.md`
- `docs/SETUP.md`
- `docs/TROUBLESHOOTING.md`
- `README.md`
- `.env.example`
- `.gitignore`
- `requirements.txt`
- `controller/*`
- `backend/*`
- `frontend/*`
- `network/*`
- `scripts/*`
- `tests/*`

## Known Bugs
None.

## Technical Decisions
- Implemented environment abstraction so Python controller algorithms and backend tests execute seamlessly in Windows / Linux / CI environments while Mininet/OVS runs in Linux/WSL.
- Implemented in-memory fallback for MongoDB in backend when live MongoDB instance is not connected, preventing runtime crashes while maintaining strict schema validation.
- Standardized REST and WebSocket models via Pydantic to ensure single-source-of-truth between Controller, Backend, and Frontend.

## Environment Requirements
- Controller, Backend, and Frontend run natively on Windows, Linux, and macOS.
- Mininet and Open vSwitch data plane require a Linux environment (Ubuntu native or WSL2 with `openvswitch-switch`).

## Testing Status
- **Pytest test suite**: 10 passed in 0.89s.
- **Controller standalone execution**: Verified (`python controller/app.py` runs Dijkstra over 7-switch mesh).
- **Frontend TypeScript & Vite compilation**: Verified (`tsc && vite build` succeeded in 1m 34s).

## Experiments
Planned experiments:
1. Normal Baseline traffic.
2. Elephant flow congestion & dynamic Dijkstra rerouting.
3. Link failure & sub-second failover recovery.
4. Multi-path resilience test.
5. Static vs SDN intelligent routing benchmark.

## Results
Pending live Mininet test runs in Milestone 2+.

## Pending Tasks
- Milestone 2: Mininet topology deployment, Ryu OpenFlow 1.3 controller integration & live discovery.
- Milestone 3: Live Dijkstra flow installation in Open vSwitch.
- Milestone 4: Traffic monitoring loop & port rate calculation.
- Milestone 5: Stateful congestion and link-failure triggers.
- Milestone 6: Full backend-controller bridge.
- Milestone 7: Interactive topology visualizer and live metrics UI polish.
- Milestone 8: Automated experiment execution and benchmark reporting.

## Roadmap
- **Milestone 1**: Foundation & Scaffolding (Completed)
- **Milestone 2**: Network & Controller Setup (Next)
- **Milestone 3**: Routing & Flow Management
- **Milestone 4**: Monitoring & Metrics
- **Milestone 5**: Congestion, Rerouting & Fault Recovery
- **Milestone 6**: Backend & Real-time WebSocket Integration
- **Milestone 7**: Frontend Dashboard & Operations Console
- **Milestone 8**: Experiments & Performance Measurement
- **Milestone 9**: Integration Testing
- **Milestone 10**: Final Polish & Live Demonstration
