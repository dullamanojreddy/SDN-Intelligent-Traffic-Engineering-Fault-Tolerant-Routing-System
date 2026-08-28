# SDN Controller Architecture & Routing Engine

## 1. Overview
The controller is built in Python on top of the **Ryu SDN Framework** (OpenFlow 1.3). It controls all forwarding decisions in the network.

## 2. Core Modules
- **`topology.topology_manager`**: Listens for topology events, LLDP frame exchanges, and maintains active vertices (switches, hosts) and edges (links).
- **`routing.dijkstra`**: Implements standard and $K$-shortest path Dijkstra algorithms over weighted directed graphs.
- **`routing.cost_function`**: Computes normalized link costs based on dynamic metrics:
  $$\text{Cost}(u, v) = \alpha \cdot \frac{\text{latency}(u, v)}{\text{max\_latency}} + \beta \cdot \frac{\text{utilization}(u, v)}{100} + \gamma \cdot \frac{\text{loss\_rate}(u, v)}{100}$$
- **`traffic.monitor`**: Periodically queries switch port stats and calculates flow rates and link utilization.
- **`congestion.detector`**: Evaluates threshold breaches and confirms persistence over $N$ measurement cycles before initiating rerouting.
- **`failure.detector` & `failure.recovery`**: Handles `OFPPortStatus` changes and initiates sub-second route recalculations.
- **`qos.qos_engine`**: Provides traffic class prioritization and weight tuning.
- **`events.event_manager`**: Broadcasts controller notifications to the backend REST/WebSocket service.

## 3. OpenFlow 1.3 Rules
- Table-miss Flow Entry (Priority 0): Sends unhandled packets to Controller (`OFPActionOutput(OFPP_CONTROLLER)`).
- ARP Handling (Priority 10): Resolves host locations and installs bidirectional forwarding.
- Data Flow Entries (Priority 20-30): Explicit IP matching rules (`eth_type=0x0800`, `ipv4_src`, `ipv4_dst`, `ip_proto`) routing traffic along the optimal path calculated by Dijkstra.
- QoS Priority Rules (Priority 40-50): Priority treatment based on DSCP / ToS / IP Protocol fields.
