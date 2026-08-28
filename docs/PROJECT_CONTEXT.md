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
**Milestone 2 & 3 Completed**: Live OpenFlow 1.3 multi-hop forwarding, Proxy ARP, dynamic bidirectional flow installation, and topology-aware port hop generation implemented and verified across 30 automated test suites.

## Latest Bug Resolution & Debugging Summary

### 1. Problem Discovered
In live Mininet data plane, `h1 ping h7` was dropping packets (100% loss) and switch packet counters were ballooning to millions of packets hitting table-miss:
- Asymmetric LLDP link discovery in NetworkX directed graph.
- ARP matching in OpenFlow flows was matching on `eth_dst` instead of `arp_tpa` (Target IP).
- Hardcoded ingress/egress ports (`3` and `4`) in `_install_rerouted_path()`.
- Multi-hop port hop generation lacked unified accessors from `NetworkGraph`.

### 2. Root Cause
1. Directed NetworkX graph (`DiGraph`) requires edges in both directions (`u -> v` and `v -> u`). LLDP packet handler was only inserting one direction dynamically.
2. Broadcast ARP requests have `eth_dst = ff:ff:ff:ff:ff:ff`, failing to match rules keyed on unicast MAC; matching `arp_tpa` accurately matches both ARP requests and replies.
3. Reroute path installer assumed fixed ports 3 and 4 rather than looking up source and destination host attachments in `host_ip_table` and querying edge switch links.

### 3. Files Changed
- `controller/topology/graph.py`: Added authoritative `get_link_ports()`, `get_link_output_port()`, `get_link_input_port()`.
- `controller/topology/discovery.py`: Ensured bidirectional link insertion in `handle_lldp_packet()`.
- `controller/openflow/flow_manager.py`: Updated `match_arp` to match on `arp_tpa: dst_ip`.
- `controller/openflow/packet_handler.py`: Rebuilt `_build_port_hops()` to use topology graph accessors; clarified Ethernet header ordering in proxy ARP reply.
- `controller/app.py`: Updated `_on_congestion_alert`, `_install_rerouted_flow`, and `_trigger_failover_recovery` to dynamically derive endpoints from flow metadata and `host_ip_table`.
- `tests/test_controller_integration.py`: Added full 7-switch mesh simulation and all-pairs `pingall` tests.
- `tests/test_port_hops_regression.py`: Added regression test suite verifying forward and reverse port hops across all mesh paths.

### 4. Implementation Decisions
- Unified port lookup into `NetworkGraph` as the single authoritative source of truth.
- Preserved sub-millisecond Proxy ARP with direct unicast reply generation to prevent mesh broadcast loops.
- Maintained OpenFlow 1.3 compliance with priority-100 primary flows and priority-200 dynamic reroute overrides.

### 5. Tests Performed
- **Automated Test Suite**: 30 / 30 tests passing (`pytest tests/ -v`).
- **Full Mesh End-to-End Simulation**: 7 switches simultaneously completing OpenFlow 1.3 handshakes, proxy ARP, Dijkstra flow installation, congestion reroute, and link-down failover.
- **Port Hop Regression**: All 4 forward paths (`s1-s2-s5-s7`, `s1-s3-s6-s7`, `s1-s2-s4-s7`, `s1-s3-s4-s7`) and return paths verified against topology edge definitions.

### 6. Remaining Verification
- Live Mininet validation in Ubuntu/WSL environment (`pingall`, `iperf3`, link teardown failover).
