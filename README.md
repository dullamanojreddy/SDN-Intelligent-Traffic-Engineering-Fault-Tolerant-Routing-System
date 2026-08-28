# 🌐 SDN Intelligent Traffic Engineering System

# Intelligent Software-Defined Networking Platform for Real-Time Traffic Engineering & Automated Routing

### **OpenFlow 1.3 • Mininet/OVS • Multi-Metric Dijkstra • Real-Time Telemetry • Dynamic Routing • Link-Failure Recovery • Interactive Network Visualization**

<div align="center">

![Python](https://img.shields.io/badge/PYTHON-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![OpenFlow](https://img.shields.io/badge/OPENFLOW-1.3-00599C?style=for-the-badge&logo=opennetworking&logoColor=white)
![Mininet](https://img.shields.io/badge/MININET-SIMULATION-E95420?style=for-the-badge&logo=linux&logoColor=white)
![Open vSwitch](https://img.shields.io/badge/OPEN_vSWITCH-OVS-1885D5?style=for-the-badge&logo=gnubash&logoColor=white)

![FastAPI](https://img.shields.io/badge/FASTAPI-0.110-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![WebSockets](https://img.shields.io/badge/WEBSOCKETS-REALTIME-010101?style=for-the-badge&logo=socketdotio&logoColor=white)
![MongoDB](https://img.shields.io/badge/MONGODB-DATABASE-47A248?style=for-the-badge&logo=mongodb&logoColor=white)
![NetworkX](https://img.shields.io/badge/NETWORKX-DIJKSTRA-008080?style=for-the-badge&logo=scipy&logoColor=white)

![React](https://img.shields.io/badge/REACT-18.2-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TYPESCRIPT-5.X-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/VITE-5.X-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/TAILWINDCSS-3.4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)
![Pytest](https://img.shields.io/badge/PYTEST-36_TESTS_PASSING-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)

</div>

**A production-oriented Software-Defined Networking platform that dynamically monitors network conditions, computes optimized forwarding paths, programs OpenFlow switches, detects failures, and visualizes the entire network in real time.**

---

# 🚀 Overview & Problem Statement

Traditional networks rely on distributed routing protocols where switches make localized, uncoordinated forwarding decisions without global network visibility. This introduces significant operational challenges:

* **Static Routing Inefficiencies**: Traffic follows static shortest-path routes, causing hot-spot link saturation while alternate paths remain idle.
* **Lack of Real-Time Visibility**: Network congestion and localized packet drops develop invisibly without centralized observability.
* **Slow Failure Convergence**: Link outages disrupt communications until distributed protocols slowly recalculate spanning trees.
* **Manual & Error-Prone Rule Management**: Configuring QoS, ACLs, and routing across distributed switches manually is complex and slow.

### The SDN Solution
The **SDN Intelligent Traffic Engineering System (SDN-ITE)** solves this by decoupling the control plane from the underlying data plane:
1. **Centralized Intelligence**: An asynchronous OpenFlow 1.3 controller acts as the central brain, maintaining a live network graph and monitoring link-level statistics.
2. **Multi-Metric Optimization**: Calculates global optimal paths factoring latency, utilization, and packet drops rather than naive hop count.
3. **Automated Data-Plane Programming**: Dynamically installs bidirectional flow rules on Open vSwitches, handles ARP/IPv4 traffic, and automatically reroutes around failures.
4. **Real-Time Operations UI**: Streams live telemetry, topology graphs, and flow tables to a reactive web dashboard via WebSockets.

---

# 🏗️ System Architecture

```text
                           ┌───────────────────────────┐
                           │   React Operations UI     │
                           │                           │
                           │ • Animated Topology Graph │
                           │ • Live Metrics & KPIs     │
                           │ • Flow Table Inspection   │
                           │ • Dynamic Routing Paths   │
                           │ • Failure Simulation NOC  │
                           └─────────────┬─────────────┘
                                         │
                              REST API + WebSocket
                                         │
                                         ▼
                           ┌───────────────────────────┐
                           │      FastAPI Backend      │
                           │                           │
                           │ • REST Endpoints (/api/*) │
                           │ • WebSocket Hub (/ws)     │
                           │ • Topology & Metrics Svc  │
                           │ • Resilient DB / Cache    │
                           └─────────────┬─────────────┘
                                         │
                                Controller State & Events
                                         │
                                         ▼
                           ┌───────────────────────────┐
                           │       SDN Controller      │
                           │                           │
                           │ • OpenFlow 1.3 Protocol   │
                           │ • Multi-Metric Dijkstra   │
                           │ • Network Graph & LLDP    │
                           │ • Flow & Packet Manager   │
                           │ • Fast Failover Engine    │
                           │ • Port Stats Telemetry    │
                           └─────────────┬─────────────┘
                                         │
                              OpenFlow 1.3 (TCP :6653)
                                         │
                                         ▼
                  ┌─────────────────────────────────────────┐
                  │          Mininet + Open vSwitch         │
                  │                                         │
                  │   s1 ─── s2 ─── s5                      │
                  │    │      │      │                      │
                  │    │     s4      │                      │
                  │    │      │      │                      │
                  │   s3 ─── s6 ─── s7                      │
                  │                                         │
                  │        h1 h2 h7 h8                      │
                  └─────────────────────────────────────────┘
```

---

# 🧩 Core Modules Breakdown

| Module | Location | Primary Responsibilities |
| :--- | :--- | :--- |
| **OpenFlow Protocol** | `controller/openflow/protocol.py` | Binary serialization & parsing of OpenFlow 1.3 messages, match structures, actions, and stats replies. |
| **Switch Manager** | `controller/openflow/switch_manager.py` | Manages active switch datapath connections, handshakes, echo heartbeats, and port status tracking. |
| **Packet Handler** | `controller/openflow/packet_handler.py` | Dispatches Packet-In messages, performs true origin resolution, Proxy ARP resolution, and packet forwarding. |
| **Flow Manager** | `controller/openflow/flow_manager.py` | Installs, modifies, and clears proactive and reactive bidirectional OpenFlow forwarding rules. |
| **Network Graph** | `controller/topology/graph.py` | Graph representation of switches, ports, hosts, and dynamic inter-switch links with metrics. |
| **Topology Discovery**| `controller/topology/discovery.py` | Discovers inter-switch links dynamically using bidirectional LLDP probe injection. |
| **Routing Engine** | `controller/routing/dijkstra.py` | Computes multi-metric shortest paths factoring latency, utilization, and packet drops. |
| **Failure Detector** | `controller/failure/detector.py` | Detects link/port down events and triggers immediate path recalculation and flow migration. |
| **Stats Manager** | `controller/openflow/stats_manager.py` | Polls port statistics periodically to compute real-time bandwidth utilization and congestion. |
| **FastAPI Backend** | `backend/main.py` | Exposes REST APIs, manages database persistence (with in-memory fallback), and hosts WebSockets. |
| **WebSocket Hub** | `backend/websocket/manager.py` | Streams real-time topology updates, metrics, and failure alerts to connected UI clients. |
| **Operations UI** | `frontend/src/` | Interactive React + TypeScript + Vite web application with animated SVG topology and telemetry charts. |

---

# 🗺️ Topology & Intelligent Multi-Metric Routing

### 7-Switch Multi-Path Mesh Topology

```text
                 S2 (100M) ─────── S5 (100M)
                /   \             /   \
               /     \           /     \
H1, H2 ── S1 (100M)    S4 (100M)        S7 ── H7, H8
               \     /           \     /
                \   /             \   /
                 S3 (100M) ─────── S6 (100M)
```

### Multi-Metric Cost Model
Instead of naive hop-count, the routing engine calculates edge weights dynamically:

$$\text{Path Cost} = \alpha \cdot \text{Latency}_{\text{norm}} + \beta \cdot \text{Utilization}_{\text{pct}} + \gamma \cdot \text{Loss}_{\text{pct}}$$

* **Default Weights**: $\alpha = 0.4$ (Latency), $\beta = 0.4$ (Utilization), $\gamma = 0.2$ (Packet Loss).
* **QoS Adaptive Weights**:
  * **Voice / Real-Time**: $\alpha=0.7, \beta=0.1, \gamma=0.2$ (Prioritizes ultra-low latency).
  * **Bulk / Video**: $\alpha=0.2, \beta=0.6, \gamma=0.2$ (Avoids congested links to maximize throughput).
  * **Web / Default**: $\alpha=0.4, \beta=0.4, \gamma=0.2$ (Balanced multi-objective routing).

---

# 🔄 Real Data-Plane Forwarding Engine

```text
1. Host h1 generates packet (e.g., ICMP to h7)
         │
         ▼
2. Open vSwitch s1 receives packet
         │
         ▼
3. Switch checks OpenFlow Table (Table 0)
   ├── Match Found ──► Line-rate hardware forwarding out designated port
   └── Table Miss  ──► OpenFlow Packet-In sent to Controller (TCP 6653)
                            │
                            ▼
4. Controller resolves true origin endpoint via Host IP Table
         │
         ▼
5. Controller queries live Network Graph and calculates Dijkstra path
         │ (e.g., s1 -> s2 -> s5 -> s7)
         ▼
6. FlowManager installs bidirectional flow rules on all intermediate switches
   ├── s1: match(dst=h7) -> output: port_to_s2
   ├── s2: match(dst=h7) -> output: port_to_s5
   ├── s5: match(dst=h7) -> output: port_to_s7
   └── s7: match(dst=h7) -> output: port_to_h7 (and reverse rules for h7 -> h1)
         │
         ▼
7. Controller emits Packet-Out with OFP_NO_BUFFER to forward initial packet
         │
         ▼
8. Destination host h7 receives packet; subsequent packets forwarded at line-rate
```

---

# 🧠 Core Engineering Challenges Solved

### 1. OpenFlow Match Structure 8-Byte Alignment
OpenFlow 1.3 `OFPT_PACKET_IN` messages contain variable-length `ofp_match` structs. In compliant OVS implementations, matches must be padded with zeroes to align on an 8-byte boundary. The custom protocol parser computes exact padding offsets so that packet headers are parsed with zero byte corruption.

### 2. Intermediate-Switch Packet-In & True Origin Resolution
When a packet enters an intermediate switch without a pre-installed rule, the switch sends a Packet-In. If a controller naively assumes `source_switch = datapath_id`, it computes a broken sub-path. SDN-ITE resolves the true origin switch and port from the `host_ip_table`, enabling accurate end-to-end path derivation from any hop in the network.

### 3. Loop Storm Prevention & Spanning Tree Convergence
Multi-path mesh topologies create broadcast loops for ARP and IPv6 multicast discovery packets. The system addresses this on three levels:
* **Spanning Tree Protocol (STP)**: Mininet topology scripts configure switches with `stp=True, failMode='standalone'` to detect and block redundant broadcast loops.
* **Proxy ARP Engine**: The controller intercepts ARP requests at the network edge and responds directly with known host MACs, preventing ARP flooding across mesh switches.
* **Proactive Baseline Provisioning**: Pre-installs baseline shortest-path routes at startup, guaranteeing 0% packet drops without waiting for initial table misses.

### 4. Reliable `OFP_NO_BUFFER` Packet-Out Execution
Switch buffers (`buffer_id`) in Open vSwitch can expire or get overwritten during high traffic. SDN-ITE uses `OFP_NO_BUFFER = 0xffffffff` and sends the complete raw frame payload in `OFPT_PACKET_OUT`, guaranteeing reliable initial packet transmission.

---

# 🚨 Fast Failover & Dynamic Link Recovery

```text
Normal Network Active
         │
         ▼
Link Failure Occurs (e.g., s2 - s5 link down)
         │
         ▼
OpenFlow Port Status Event (OFPPR_DELETE / OFPPR_MODIFY)
         │
         ▼
FailureDetector marks link inactive in NetworkGraph
         │
         ▼
Routing Engine triggers Dijkstra recalculation
         │
         ▼
FlowManager updates switch flow tables to alternate path (e.g., s1 -> s3 -> s6 -> s7)
         │
         ▼
Sub-second traffic restoration with zero human intervention
```

---

# 🖥️ Real-Time Web Operations Dashboard

The React web application provides an intuitive control interface:

* **Interactive Network Topology Graph**: Dynamic SVG canvas rendering all 7 switches, hosts, active links, and real-time port states.
* **Live Telemetry & KPIs**: Real-time counters for active switches, connected hosts, total bandwidth throughput, and average network utilization.
* **Flow Table Inspection**: Searchable OpenFlow 1.3 tables displaying switch DPID, match fields, applied actions, packet counters, and flow age.
* **Routing Path Tracing**: Visualizes calculated shortest paths and highlights selected routes across the graph.
* **Failure Simulation NOC**: Trigger live link up/down outages with a single click to observe automatic rerouting and failover alerts.

---

# 🚀 Getting Started & Installation

### Prerequisites
* Linux / Ubuntu 22.04+ (or WSL2 on Windows)
* Python 3.10+
* Node.js 18+ & npm
* Mininet & Open vSwitch

### 1. Clone & Setup Python Virtual Environment
```bash
git clone https://github.com/dullamanojreddy/SDN-Intelligent-Traffic-Engineering-Fault-Tolerant-Routing-System.git
cd SDN-Intelligent-Traffic-Engineering-Fault-Tolerant-Routing-System

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Launch Controller & Services
Run each component in a separate terminal:

```bash
# Terminal 1: SDN OpenFlow 1.3 Controller (Port 6653)
python controller/app.py

# Terminal 2: FastAPI Backend Server (Port 8000)
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 3: React Web Dashboard (Port 5173)
cd frontend
npm install
npm run dev

# Terminal 4: Mininet Mesh Simulation (Linux / WSL2)
sudo python3 network/topologies/mesh.py
```

---

# 🧪 Testing & Validation Summary

### Automated Regression Suite
Run the test suite from the repository root:
```bash
py -m pytest tests/ -v
```

```text
============================= test session starts =============================
collected 36 items

tests/test_backend_api.py ................                               [ 11%]
tests/test_congestion.py ........                                        [ 16%]
tests/test_controller_integration.py ............                        [ 30%]
tests/test_dijkstra.py ................                                  [ 41%]
tests/test_openflow_protocol.py ................................         [ 63%]
tests/test_port_hops_regression.py ............................          [ 83%]
tests/test_real_dataplane_regression.py ........................         [100%]

============================= 36 passed in 1.25s ==============================
```

### Real Mininet Data-Plane Validation
Inside the Mininet console:
```text
mininet> pingall
*** Ping: testing ping reachability
h1 -> h2 h7 h8 
h2 -> h1 h7 h8 
h7 -> h1 h2 h8 
h8 -> h1 h2 h7 
*** Results: 0% dropped (12/12 received)
```

Targeted bidirectional reachability checks:
```text
mininet> h1 ping -c 4 h7
4 packets transmitted, 4 received, 0% packet loss

mininet> h7 ping -c 4 h1
4 packets transmitted, 4 received, 0% packet loss
```

---

# 🔍 OpenFlow Verification Commands

```bash
# Check connected Open vSwitches
sudo ovs-vsctl show

# Inspect installed OpenFlow 1.3 flows
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
sudo ovs-ofctl -O OpenFlow13 dump-flows s7

# Inspect live port statistics
sudo ovs-ofctl -O OpenFlow13 dump-ports s1
sudo ovs-ofctl -O OpenFlow13 dump-ports s7
```

---

# 📡 REST API & WebSocket Reference

### Core REST Endpoints
* `GET /api/topology` — Full switch, host, and link topology graph.
* `GET /api/switches` — List of connected OpenFlow 1.3 switches.
* `GET /api/links` — Detailed link metrics (capacity, utilization, latency, loss, state).
* `GET /api/metrics` — Aggregate network telemetry (bandwidth, flow count, status).
* `GET /api/flows` — Active OpenFlow rules across all datapaths.
* `GET /api/routing/decisions` — Current Dijkstra routing decisions and calculated paths.
* `POST /api/routing/recalculate` — Manually trigger route re-optimization for an endpoint pair.
* `POST /api/network/failure/simulate` — Simulate a link outage (`DOWN`) or recovery (`UP`).

### Real-Time WebSocket Channel
* `ws://localhost:8000/ws/network` — Streams real-time topology changes, congestion alerts, and telemetry events to connected clients.

---

# 👨‍💻 Developer

## Dulla Manoj Reddy

**Information Technology Engineer | AI/ML Enthusiast | Full-Stack & Networking Developer**

* 🌐 **GitHub**: [@dullamanojreddy](https://github.com/dullamanojreddy)
* 💼 **Project**: [SDN-Intelligent-Traffic-Engineering-Fault-Tolerant-Routing-System](https://github.com/dullamanojreddy/SDN-Intelligent-Traffic-Engineering-Fault-Tolerant-Routing-System)

---

# ⭐ Support

If you find this project useful or interesting, consider giving the repository a ⭐ on GitHub!
