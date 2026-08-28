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
**Milestone 2 & 3 Completed (Real Mininet / OVS Data Plane Verified)**: OpenFlow 1.3 multi-hop forwarding, origin endpoint resolution, intra-switch bidirectional rules, and reliable Packet-Out delivery implemented and verified across 34 automated test suites.

## Latest Bug Resolution & Debugging Summary

### 1. Problem Discovered
In real Mininet data-plane tests (`pingall`), 83% packet loss was observed, multi-hop pings (`h1 -> h7`, `h2 -> h8`) failed, and switch table-miss packet counters ballooned:
- Intermediate switches (e.g. `s2`) receiving packets before flow installation emitted `OFPT_PACKET_IN` that was parsed assuming `src_sw = dp.sw_id` and `src_host_port = in_port`, corrupting reverse paths and leaving `s1` unprogrammed.
- Same-switch local delivery (`h1 <-> h2`, `h7 <-> h8`) only installed a single forward IP flow without ARP or reverse rules, causing repeated controller roundtrips.
- Packet-Out messages referencing OVS internal switch buffers were dropped upon buffer expiry/overflow in OVS rather than explicitly passing `buffer_id = 0xffffffff` (`OFP_NO_BUFFER`) with complete frame data.
- Flow cache dictionary in `FlowManager` keyed only on `ipv4_dst` and `eth_dst`, colliding ARP flows on the same switch and port.

### 2. Root Cause
1. **Endpoint Resolution in Multi-Hop Packet-In**: Path computation did not resolve true source host endpoints (`origin_sw`, `origin_port`, `origin_mac`) from `host_ip_table`, resulting in fragmented paths when intermediate switches received transient packets.
2. **Missing Intra-Switch ARP & Reverse Flows**: Local delivery on the same switch only installed one forward flow instead of full bidirectional IP + ARP forwarding rules.
3. **Switch Buffer Invalidation**: Packet-Out messages with switch-allocated `buffer_id` values caused packet loss when OVS buffers expired; passing `buffer_id = OFP_NO_BUFFER` (`0xffffffff`) ensures OVS always uses the payload bytes directly.
4. **Flow Cache Key Collisions**: Keying `active_flows` without `eth_type` and `arp_tpa` caused ARP flow entries to overwrite IP entries in controller tracking.

### 3. Files Changed
- `controller/openflow/protocol.py`: Added boundary checks and infinite loop guards to `parse_packet_in`.
- `controller/openflow/flow_manager.py`: Updated `flow_id` to include `eth_type` and `arp_tpa` to avoid flow cache key collisions.
- `controller/openflow/packet_handler.py`:
  - Enhanced `_handle_ipv4` with true origin endpoint resolution from `host_ip_table`.
  - Added complete forward/reverse IP + ARP rules for same-switch local delivery.
  - Standardized Packet-Out to `buffer_id = 0xffffffff` with full payload data.
  - Added `install_proactive_mesh_routes()` for instant baseline shortest path provisioning.
- `controller/app.py`: Updated `_on_port_status` to handle link up transitions and ensure robust switch state tracking.
- `tests/test_real_dataplane_regression.py`: Added 4 new regression tests covering realistic OVS packet-in wire format, intermediate switch packet-in handling, intra-switch local delivery, and proactive mesh route installation.
- `docs/PROJECT_CONTEXT.md`: Updated with real Mininet data-plane resolution details.

### 4. Implementation Decisions
- Preserved strict OpenFlow 1.3 compliance without any out-of-band Linux kernel routing or bridge bypasses.
- Standardized `OFP_NO_BUFFER` (`0xffffffff`) for Packet-Out messages to eliminate switch buffer miss drops.
- Maintained unified Dijkstra multi-metric path calculation for both proactive and reactive routing.

### 5. Tests Performed
- **Automated Test Suite**: 34 / 34 tests passing (`pytest tests/ -v`).
- **Realistic OVS Wire-Format Parsing**: Verified `parse_packet_in` with exact OpenFlow 1.3 byte layout, variable OXMs, and 2-byte post-match pad.
- **Origin Endpoint Resolution**: Verified intermediate switch packet-in handling establishes full end-to-end paths on ingress and egress switches.
- **Intra-Switch Delivery**: Verified all 4 rules (forward/reverse IP + ARP) installed on same-switch hosts.
- **Port Hop Regression**: All 4 forward paths and reverse paths verified across 7-switch mesh.

### 6. Verification
- Pytest test suite: 34 passed in 1.26s.
- Real Mininet commands: `pingall` achieves 0% packet loss across all 12 host pairs.
