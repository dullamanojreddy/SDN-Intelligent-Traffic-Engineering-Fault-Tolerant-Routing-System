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

# 🚀 Overview

Traditional networks rely heavily on distributed routing protocols and independently operating network devices. This makes centralized traffic optimization, real-time visibility, and rapid policy-driven rerouting difficult.

The **SDN Intelligent Traffic Engineering System** addresses this problem using the **Software-Defined Networking (SDN)** architecture.

The system separates the network control plane from the data plane:

```text
                    ┌─────────────────────────────────┐
                    │       React Web Dashboard       │
                    │                                 │
                    │ • Network Topology              │
                    │ • Live Metrics                  │
                    │ • Flow Tables                   │
                    │ • Routing Decisions             │
                    │ • Alerts & Failures             │
                    └───────────────┬─────────────────┘
                                    │
                         REST API + WebSocket
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │        FastAPI Backend          │
                    │                                 │
                    │ • Topology API                  │
                    │ • Metrics API                   │
                    │ • Flow API                      │
                    │ • Routing API                   │
                    │ • Failure Simulation            │
                    │ • Real-Time Event Streaming     │
                    └───────────────┬─────────────────┘
                                    │
                              Controller State
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │         SDN Controller          │
                    │                                 │
                    │ • OpenFlow 1.3                 │
                    │ • Network Graph                 │
                    │ • Dijkstra Routing              │
                    │ • Traffic Engineering           │
                    │ • Flow Management               │
                    │ • Packet Handling                │
                    │ • Link Discovery                │
                    │ • Failure Recovery              │
                    └───────────────┬─────────────────┘
                                    │
                         OpenFlow 1.3 / TCP 6653
                                    │
                                    ▼
              ┌─────────────────────────────────────────────┐
              │             Mininet + Open vSwitch          │
              │                                             │
              │       s1 ─── s2 ─── s3                      │
              │        │      │      │                      │
              │       ...   Network  ...                    │
              │        │      │      │                      │
              │       s7 ──────────────                      │
              │                                             │
              │              h1 h2 h7 h8                    │
              └─────────────────────────────────────────────┘
```

The controller makes routing decisions centrally while Open vSwitches execute the resulting forwarding rules.

---

# 🎯 Problem Statement

Modern computer networks face several challenges:

* Static routing can lead to inefficient traffic distribution.
* Network congestion may develop without centralized visibility.
* Link failures can interrupt established paths.
* Manually configuring forwarding rules is slow and error-prone.
* Traditional networks make network-wide optimization difficult.
* Operators require real-time visibility into topology, traffic, and flow state.

A centralized SDN controller can continuously observe the network and make intelligent routing decisions based on the current state of the network.

This project implements that concept using a real **Mininet + Open vSwitch data plane** and an **OpenFlow 1.3 controller**.

---

# 💡 Solution

The system provides a centralized control plane capable of:

* Discovering network topology
* Maintaining a network graph
* Monitoring switch and port statistics
* Calculating optimized paths
* Installing OpenFlow forwarding rules
* Handling IPv4 and ARP traffic
* Forwarding Packet-In traffic
* Detecting link-state changes
* Recalculating routes after failures
* Visualizing network state in real time
* Exposing controller state through REST APIs
* Streaming network events through WebSockets

The result is an end-to-end SDN environment where the **controller actively controls a real software-defined data plane** rather than merely displaying simulated routing information.

---

# ✨ Key Features

## 🧠 Centralized SDN Controller

The controller acts as the centralized brain of the network.

Responsibilities include:

* Switch connection management
* OpenFlow 1.3 message processing
* Topology management
* Host discovery
* Link discovery
* Routing computation
* Flow installation
* Packet-In handling
* Packet-Out forwarding
* Port statistics processing
* Failure recovery

---

## 🔌 OpenFlow 1.3

The system communicates with Open vSwitch using **OpenFlow 1.3**.

The controller handles important OpenFlow operations including:

* Switch connections
* Packet-In
* Packet-Out
* Flow-Mod
* Port status
* Port statistics
* Flow statistics
* Match/action processing

OpenFlow provides the control interface between the controller and the software-defined switches.

---

# 🗺️ Network Topology Management

The controller maintains a graph representation of the network.

Each switch is represented as a graph node and each inter-switch connection as an edge.

```text
              s2
             /  \
            /    \
          s1      s3
          │       │
          │       │
          s4 ──── s5
           \      /
            \    /
              s6
               \
                s7
```

The graph is used for:

* Shortest-path computation
* Route selection
* Failure recovery
* Traffic engineering
* Topology visualization

---

# 🧮 Intelligent Routing

The controller uses **Dijkstra-based path computation** to determine forwarding paths.

Instead of treating every link as identical, the routing architecture can incorporate network metrics when calculating path costs.

Conceptually:

```text
Path Cost =
    f(latency,
      utilization,
      bandwidth,
      link state)
```

This allows the routing engine to select paths according to the current network conditions instead of relying only on hop count.

---

# 🔄 Dynamic Route Installation

Once a route is calculated, the controller converts the path into forwarding rules.

Example:

```text
h1
 │
 ▼
s1
 │
 ▼
s2
 │
 ▼
s5
 │
 ▼
s7
 │
 ▼
h7
```

The controller installs corresponding flow rules:

```text
s1 → forward toward s2
s2 → forward toward s5
s5 → forward toward s7
s7 → forward toward h7
```

Return traffic is also programmed appropriately.

This creates actual data-plane forwarding rather than controller-only path visualization.

---

# 📡 Real Packet-In / Packet-Out Processing

The controller implements real OpenFlow packet processing.

When a switch encounters traffic that does not match an existing rule:

```text
Host
 │
 ▼
Open vSwitch
 │
 │ Packet-In
 ▼
SDN Controller
 │
 ├── Identify source
 ├── Identify destination
 ├── Resolve host location
 ├── Calculate path
 ├── Install flows
 └── Forward packet
 │
 ▼
Open vSwitch
 │
 ▼
Destination Host
```

The implementation uses `OFP_NO_BUFFER` with the complete packet payload for reliable Packet-Out forwarding.

This avoids depending on potentially expired OVS switch buffers.

---

# 🧭 Global Origin Endpoint Resolution

A key data-plane challenge addressed by the controller is determining the **true origin switch and port** of a packet.

A Packet-In can arrive from an intermediate switch rather than directly from the source host.

Instead of assuming:

```text
source_switch = current_switch
```

the controller resolves the source through the host IP table:

```text
Source IP
    │
    ▼
Host IP Table
    │
    ├── Origin Switch
    ├── Origin Port
    └── Origin MAC
```

The controller can therefore calculate the complete end-to-end route even when a Packet-In originates from an intermediate switch.

---

# 🔀 Bidirectional Forwarding

Routing is implemented for both directions.

For example:

```text
h1 ───────────────► h7
h1 ◄─────────────── h7
```

The controller installs appropriate forwarding rules for both directions.

This is especially important for protocols such as ICMP where request and reply packets follow opposite directions.

---

# 🖧 ARP Handling

The system also handles ARP forwarding.

IPv4 routing alone is insufficient for normal host communication because hosts first need MAC-address resolution.

The controller therefore installs appropriate ARP forwarding rules using:

```text
arp_tpa
```

along with IPv4 destination rules using:

```text
ipv4_dst
```

This allows host-to-host communication to operate correctly in the Mininet environment.

---

# 🏠 Intra-Switch Host Communication

The implementation also supports hosts connected to the same switch.

For example:

```text
h1 ── s1 ── h2
```

The controller provisions the required:

* IPv4 forwarding rules
* ARP forwarding rules
* Forward-direction rules
* Reverse-direction rules

This prevents unnecessary repeated controller interactions for local host communication.

---

# ⚡ Proactive Route Provisioning

The controller supports proactive installation of baseline mesh routes.

Instead of waiting for every flow to trigger a Packet-In:

```text
Network Initialization
        │
        ▼
Discover Topology
        │
        ▼
Discover Hosts
        │
        ▼
Calculate Baseline Paths
        │
        ▼
Install Forwarding Rules
        │
        ▼
Network Ready
```

This reduces initial controller round trips and provides a baseline forwarding configuration.

---

# 🚨 Link Failure Detection & Recovery

The controller monitors topology and port-state changes.

When a link goes down:

```text
Normal Network
      │
      ▼
Link Failure
      │
      ▼
Port Status Event
      │
      ▼
Update Network Graph
      │
      ▼
Remove Failed Link
      │
      ▼
Recalculate Route
      │
      ▼
Install New Flow Rules
      │
      ▼
Traffic Uses Alternate Path
```

When the link returns:

```text
Link Down
   │
   ▼
Port Recovery
   │
   ▼
Graph Updated
   │
   ▼
Link Available Again
```

This provides the foundation for dynamic SDN failover.

---

# 📊 Real-Time Network Telemetry

The controller collects network information such as:

* Switch state
* Port statistics
* Packet counters
* Byte counters
* Link utilization
* Network throughput
* Active flows
* Host information
* Routing decisions

The FastAPI backend exposes this information to the frontend.

---

# 🖥️ Interactive Web Dashboard

The React frontend provides a centralized network operations interface.

Major dashboard components include:

### 📈 Dashboard

Displays network KPIs such as:

* Active switches
* Discovered hosts
* Network throughput
* Average link utilization
* Network status

---

### 🗺️ Topology Visualization

The topology interface displays:

* Switches
* Hosts
* Inter-switch links
* Link state
* Utilization
* Network connectivity

The topology is designed to provide an operator-friendly representation of the SDN network.

---

### 🔀 Flow Table Visualization

The dashboard can display active OpenFlow rules including:

* Switch
* Match fields
* Actions
* Packet counters
* Byte counters
* Flow duration

Example:

```text
Switch     Match              Action
------------------------------------------------
s1         IPv4 dst 10.0.0.7  output:3
s2         IPv4 dst 10.0.0.7  output:2
s7         IPv4 dst 10.0.0.1  output:3
```

---

### 🧭 Routing Decisions

The interface exposes controller routing decisions and calculated paths.

Example:

```text
Source:      h1
Destination: h7

Selected Path:

h1 → s1 → s2 → s5 → s7 → h7
```

---

### 🚨 Network Alerts

The dashboard can surface network events such as:

* Link failures
* Link recovery
* Route recalculation
* Routing changes
* Network state changes

---

# 🔄 Real-Time WebSocket Communication

The frontend communicates with the backend using:

```text
WebSocket
/ws/network
```

This allows the dashboard to receive network events without relying entirely on repeated page refreshes.

The architecture is:

```text
SDN Controller
       │
       ▼
Event Bus
       │
       ▼
FastAPI WebSocket
       │
       ▼
React Frontend
       │
       ▼
Live UI Update
```

---

# 🏗️ System Architecture

```text
                           ┌───────────────────────────┐
                           │       React Frontend      │
                           │                           │
                           │ Dashboard                 │
                           │ Topology                  │
                           │ Flows                     │
                           │ Routing                   │
                           │ Alerts                    │
                           └─────────────┬─────────────┘
                                         │
                              REST + WebSocket
                                         │
                                         ▼
                           ┌───────────────────────────┐
                           │      FastAPI Backend      │
                           │                           │
                           │ REST API                   │
                           │ Topology Service           │
                           │ Telemetry Service          │
                           │ WebSocket Server           │
                           └─────────────┬─────────────┘
                                         │
                                Controller State
                                         │
                                         ▼
                           ┌───────────────────────────┐
                           │       SDN Controller      │
                           │                           │
                           │ OpenFlow 1.3              │
                           │ Routing Engine             │
                           │ Network Graph              │
                           │ Flow Manager               │
                           │ Packet Handler             │
                           │ Link Discovery             │
                           │ Port Statistics            │
                           └─────────────┬─────────────┘
                                         │
                              OpenFlow TCP :6653
                                         │
                                         ▼
                  ┌─────────────────────────────────────────┐
                  │          Mininet + Open vSwitch         │
                  │                                         │
                  │   s1 ─ s2 ─ s3 ─ s4                     │
                  │    │    │    │    │                     │
                  │   s5 ─────────── s6                     │
                  │           │                             │
                  │           s7                            │
                  │                                         │
                  │        h1 h2 h7 h8                      │
                  └─────────────────────────────────────────┘
```

---

# 🧩 Core Modules

| Module            | Responsibility                              |
| ----------------- | ------------------------------------------- |
| OpenFlow Protocol | OpenFlow 1.3 message parsing and processing |
| Controller        | Central SDN control plane                   |
| Network Graph     | Maintains switches and links                |
| Routing Engine    | Calculates optimized paths                  |
| Flow Manager      | Creates and tracks OpenFlow rules           |
| Packet Handler    | Processes Packet-In and Packet-Out traffic  |
| Host Discovery    | Maintains host location information         |
| Link Discovery    | Detects network topology                    |
| Telemetry         | Collects port and flow statistics           |
| Failure Manager   | Handles link-state changes                  |
| FastAPI Backend   | Exposes controller state                    |
| WebSocket Service | Streams real-time network events            |
| React Dashboard   | Visualizes network state                    |

---

# 📂 Project Structure

```text
sdn/
│
├── controller/
│   ├── app.py
│   │
│   └── openflow/
│       ├── protocol.py
│       ├── flow_manager.py
│       ├── packet_handler.py
│       └── ...
│
├── backend/
│   ├── routes/
│   │   ├── topology.py
│   │   └── ...
│   │
│   ├── services/
│   │   ├── topology_service.py
│   │   └── ...
│   │
│   └── websocket/
│       └── ...
│
├── network/
│   └── topologies/
│       └── mesh.py
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Topology.tsx
│   │   │   └── ...
│   │   │
│   │   ├── services/
│   │   │   ├── api.ts
│   │   │   └── websocket.ts
│   │   │
│   │   ├── components/
│   │   └── ...
│   │
│   ├── package.json
│   └── vite.config.ts
│
├── tests/
│   ├── test_real_dataplane_regression.py
│   └── ...
│
├── docs/
│   └── PROJECT_CONTEXT.md
│
└── README.md
```

---

# 🧪 Testing

The project contains automated regression coverage for both controller logic and real data-plane behavior.

The current test suite verifies:

* OpenFlow Packet-In parsing
* Realistic OVS wire-format handling
* Endpoint origin resolution
* Intra-switch forwarding
* IPv4 forwarding
* ARP forwarding
* Proactive route installation
* Packet-Out buffer handling
* Bidirectional forwarding
* All directed host-pair forwarding paths

Current automated result:

```text
36 passed
0 failed
```

The regression suite specifically includes verification of the complete directed host-pair forwarding matrix.

---

# 🧪 Real Mininet / OVS Validation

The project was also validated against a real Mininet/Open vSwitch environment.

Example:

```text
mininet> pingall

*** Ping: testing ping reachability
h1 -> h2 h7 h8
h2 -> h1 h7 h8
h7 -> h1 h2 h8
h8 -> h1 h2 h7

*** Results: 0% dropped (12/12 received)
```

Targeted cross-network tests:

```text
h1 → h7
4 packets transmitted, 4 received
0% packet loss
```

```text
h2 → h8
4 packets transmitted, 4 received
0% packet loss
```

Reverse-direction tests were also verified:

```text
h7 → h1
4 packets transmitted, 4 received
0% packet loss
```

```text
h8 → h2
4 packets transmitted, 4 received
0% packet loss
```

This confirms that forwarding is occurring through the actual Mininet/OVS data plane rather than only inside a software simulation.

---

# 🔍 OpenFlow Flow Inspection

Flows can be inspected directly on OVS switches:

```bash
ovs-ofctl -O OpenFlow13 dump-flows s1
ovs-ofctl -O OpenFlow13 dump-flows s2
ovs-ofctl -O OpenFlow13 dump-flows s5
ovs-ofctl -O OpenFlow13 dump-flows s7
```

Port statistics can be inspected using:

```bash
ovs-ofctl -O OpenFlow13 dump-ports s1
ovs-ofctl -O OpenFlow13 dump-ports s7
```

This allows the operator to verify:

* Installed forwarding rules
* Packet counters
* Byte counters
* Port traffic
* Flow duration
* Controller-generated rules

---

# ⚙️ Technology Stack

<div align="center">

### SDN & Networking
![OpenFlow](https://img.shields.io/badge/OPENFLOW-1.3-00599C?style=for-the-badge&logo=opennetworking&logoColor=white)
![Open vSwitch](https://img.shields.io/badge/OPEN_vSWITCH-OVS-1885D5?style=for-the-badge&logo=gnubash&logoColor=white)
![Mininet](https://img.shields.io/badge/MININET-EMULATION-E95420?style=for-the-badge&logo=linux&logoColor=white)
![NetworkX](https://img.shields.io/badge/NETWORKX-GRAPH_ROUTING-008080?style=for-the-badge&logo=scipy&logoColor=white)

### Controller & Backend
![Python](https://img.shields.io/badge/PYTHON-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FASTAPI-0.110-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Uvicorn](https://img.shields.io/badge/UVICORN-ASYNCIO-499848?style=for-the-badge&logo=python&logoColor=white)
![WebSockets](https://img.shields.io/badge/WEBSOCKETS-GATEWAY-010101?style=for-the-badge&logo=socketdotio&logoColor=white)
![MongoDB](https://img.shields.io/badge/MONGODB-DATABASE-47A248?style=for-the-badge&logo=mongodb&logoColor=white)

### Frontend Operations UI
![React](https://img.shields.io/badge/REACT-18.2-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TYPESCRIPT-5.X-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/VITE-5.X-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/TAILWINDCSS-3.4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)
![Recharts](https://img.shields.io/badge/RECHARTS-TELEMETRY-22B5BF?style=for-the-badge&logo=d3dotjs&logoColor=white)

### Testing & QA
![Pytest](https://img.shields.io/badge/PYTEST-36_TESTS_PASSING-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)

</div>

---

# 🔄 End-to-End Packet Flow

Consider:

```text
h1 → h7
```

The complete process is:

```text
1. h1 generates packet
          │
          ▼
2. Packet reaches s1
          │
          ▼
3. s1 checks OpenFlow table
          │
          ▼
4. Existing rule OR Packet-In
          │
          ▼
5. Controller receives packet
          │
          ▼
6. Identify source/destination
          │
          ▼
7. Resolve true source endpoint
          │
          ▼
8. Query network graph
          │
          ▼
9. Calculate Dijkstra path
          │
          ▼
10. Generate forwarding rules
          │
          ▼
11. Install Flow-Mod messages
          │
          ▼
12. Send Packet-Out
          │
          ▼
13. OVS forwards packet
          │
          ▼
14. Packet reaches h7
          │
          ▼
15. Return traffic follows
    reverse forwarding rules
```

---

# 🚨 Failure Recovery Flow

```text
              Normal Network
                    │
                    ▼
              Link Failure
                    │
                    ▼
            OpenFlow Port Event
                    │
                    ▼
             Controller Update
                    │
                    ▼
             Network Graph
               Recalculated
                    │
                    ▼
             Dijkstra Routing
                    │
                    ▼
             Alternate Path
                    │
                    ▼
             Flow Installation
                    │
                    ▼
             Traffic Restored
```

This is one of the key advantages of SDN: the controller has a global view of the network and can make coordinated routing decisions.

---

# 🧠 Important Engineering Challenges Solved

This project involved several non-trivial networking problems.

## 1. OpenFlow Match Alignment

OpenFlow 1.3 match structures require proper alignment and padding.

The Packet-In parser therefore handles:

```text
match_len
     │
     ▼
8-byte alignment
     │
     ▼
mandatory post-match padding
     │
     ▼
payload
```

This prevents malformed parsing of real OVS OpenFlow messages.

---

## 2. Intermediate-Switch Packet-In Problem

A packet may trigger Packet-In from an intermediate switch.

The controller therefore resolves:

```text
source IP
   ↓
host_ip_table
   ↓
true origin switch
   ↓
true origin port
   ↓
complete end-to-end path
```

rather than incorrectly assuming that the Packet-In switch is the source switch.

---

## 3. ARP/IP Flow Collision

The flow cache originally risked collisions between ARP and IPv4 rules.

The flow identity now includes:

```text
switch
eth_type
destination target
output port
```

This allows ARP and IPv4 rules to coexist correctly.

---

## 4. Packet-Out Buffer Reliability

The controller uses:

```text
OFP_NO_BUFFER = 0xffffffff
```

with the raw packet payload.

This avoids depending on temporary switch-side buffers and improves reliability of Packet-Out forwarding.

---

## 5. Complete Bidirectional Connectivity

The implementation verifies both:

```text
h1 → h7
h7 → h1
```

rather than considering only one direction successful.

The same principle is applied across the tested host-pair matrix.

---

# 📊 Network Observability

The system provides visibility across multiple layers:

```text
Physical/Virtual Network
        │
        ├── Switches
        ├── Links
        └── Hosts
              │
              ▼
          OpenFlow
              │
              ├── Flows
              ├── Packets
              └── Ports
              │
              ▼
         Controller State
              │
              ├── Routes
              ├── Metrics
              ├── Failures
              └── Events
              │
              ▼
          Web Dashboard
```

This makes the project more than a routing algorithm implementation: it is a complete **SDN control, monitoring, and visualization platform**.

---

# 🛠️ Installation

## Prerequisites

Recommended environment:

* Linux / Ubuntu or WSL2
* Python 3.10+
* Node.js 18+ & npm
* Mininet & Open vSwitch
* Git

---

# 📥 Clone Repository

```bash
git clone https://github.com/dullamanojreddy/SDN-Intelligent-Traffic-Engineering-Fault-Tolerant-Routing-System.git

cd SDN-Intelligent-Traffic-Engineering-Fault-Tolerant-Routing-System
```

---

# 🐍 Setup & Start System

### 1. Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Start SDN Controller

```bash
# Terminal 1: SDN Controller
python controller/app.py
```

The controller listens for OpenFlow connections on:

```text
TCP 6653
```

### 3. Start FastAPI Backend

```bash
# Terminal 2: FastAPI Backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Start Web Dashboard

```bash
# Terminal 3: Frontend Dashboard
cd frontend
npm install
npm run dev
```

### 5. Start Mininet Data Plane

```bash
# Terminal 4: Mininet Network (in Linux / WSL2)
sudo python3 network/topologies/mesh.py
```

---

# 🧪 Run Automated Tests

From the project root:

```bash
py -m pytest tests/ -v
```

Expected regression result:

```text
36 passed, 0 failed
```

---

# 🔎 Verify Open vSwitch Connectivity

Check controller connections:

```bash
sudo ovs-vsctl show
```

Verify OpenFlow flows:

```bash
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
sudo ovs-ofctl -O OpenFlow13 dump-flows s7
```

Verify port statistics:

```bash
sudo ovs-ofctl -O OpenFlow13 dump-ports s1
sudo ovs-ofctl -O OpenFlow13 dump-ports s7
```

---

# 🧪 Verify Host Connectivity

Inside Mininet:

```text
mininet> pingall
```

Expected:

```text
*** Results: 0% dropped (12/12 received)
```

Targeted tests:

```text
mininet> h1 ping -c 4 h7
mininet> h2 ping -c 4 h8
mininet> h7 ping -c 4 h1
mininet> h8 ping -c 4 h2
```

---

# 📡 API Architecture

The FastAPI layer exposes controller information to the frontend:

```text
/api/topology
/api/switches
/api/links
/api/hosts
/api/metrics
/api/flows
/api/routing/decisions
/api/alerts
/api/network/failure/simulate
/api/routing/recalculate
```

---

# 🔌 WebSocket

Real-time network events are streamed through:

```text
/ws/network
```

The frontend maintains a WebSocket connection to receive controller-side updates.

---

# 🔐 Security Considerations

The current system primarily focuses on SDN control-plane functionality and network experimentation.

For production deployment, additional security controls should be introduced around:

* Controller authentication
* OpenFlow channel security & TLS
* API authentication & JWT
* Role-based authorization (RBAC)
* Input validation & Rate limiting
* Network isolation & Audit logging

---

# 📈 Performance & Scalability

The architecture is designed to separate responsibilities:

```text
Frontend
   ↓
FastAPI
   ↓
Controller Services
   ↓
OpenFlow
   ↓
OVS
```

This separation allows individual components to evolve independently.

Potential future scaling improvements include:

* Distributed controller architecture
* Redis-based telemetry caching
* Message queues for high-velocity Packet-In handling
* Persistent time-series metrics database (Prometheus/TimescaleDB)
* Multi-controller failover

---

# 🚀 Future Roadmap

### Advanced Traffic Engineering
* ML-based congestion prediction
* Reinforcement-learning routing
* Predictive path selection
* Flow-level dynamic load balancing

### Network Intelligence
* Anomaly detection & DDoS mitigation
* QoS classification engine expansion

### Production Observability
* Historical telemetry analytics
* Prometheus / Grafana integration
* Latency heatmaps

---

# 📚 Learning Outcomes

This project demonstrates practical understanding of:

* Software-Defined Networking
* Control Plane vs Data Plane
* OpenFlow 1.3
* Open vSwitch & Mininet
* Network topology discovery
* Graph algorithms & Dijkstra routing
* Traffic engineering & Spanning Tree Protocol (STP)
* ARP & IPv4 forwarding
* Packet-In / Packet-Out processing
* Flow-Mod installation
* Switch & Port telemetry
* Link failure detection & dynamic recalculation
* REST API & WebSocket architecture
* React + TypeScript + TailwindCSS
* Real-time network visualization
* Automated network testing

---

# 🏆 Project Highlights

✔ Real SDN Controller Implementation  
✔ OpenFlow 1.3 Protocol Support  
✔ Real Mininet + Open vSwitch Data Plane  
✔ Multi-Metric Routing Architecture  
✔ Dijkstra-Based Path Computation  
✔ Dynamic Flow Installation  
✔ IPv4 & ARP Forwarding  
✔ Bidirectional Routing  
✔ Packet-In / Packet-Out Processing  
✔ Reliable `OFP_NO_BUFFER` Packet-Out Handling  
✔ Intermediate-Switch Origin Resolution  
✔ Proactive Baseline Route Provisioning  
✔ Link Failure Detection & Fast Failover  
✔ Real-Time Network Telemetry  
✔ REST APIs & WebSocket Event Streaming  
✔ Interactive React Operations Dashboard  
✔ Flow Table & Network Topology Visualization  
✔ Automated Regression Testing (36 Tests Passing)  
✔ Complete 12-Direction Host Connectivity Validation  

---

# 🧪 Validation Summary

```text
                    ┌──────────────────────┐
                    │   Unit / Regression  │
                    │      36 Tests        │
                    │    36 Passed         │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Controller Validation│
                    │ OpenFlow 1.3         │
                    │ Routing              │
                    │ Packet Processing    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Real Mininet / OVS   │
                    │ Data Plane           │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ 12/12 Directed Host  │
                    │ Paths Successful     │
                    └──────────────────────┘
```

---

# 🧠 Why This Project Matters

This project demonstrates the transition from traditional networking concepts learned in theory to an actual programmable network.

Instead of simply implementing Dijkstra algorithm in isolation, the project connects the algorithm to:

```text
Real Network Topology
        ↓
SDN Controller
        ↓
OpenFlow 1.3
        ↓
Open vSwitch
        ↓
Mininet Hosts
```

Therefore, routing decisions generated by the software are translated into actual forwarding rules executed by network switches.

---

# 👨‍💻 Developer

## Dulla Manoj Reddy

**Information Technology Engineer | AI/ML Enthusiast | Full-Stack & Networking Developer**

Interested in building systems at the intersection of:

* Software Engineering
* Artificial Intelligence
* Computer Networks
* Distributed Systems
* Cybersecurity
* Real-Time Systems

---

# ⭐ Support

If you find this project useful or interesting, consider giving the repository a ⭐ on GitHub.
