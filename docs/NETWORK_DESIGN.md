# Network Design & Topologies

## 1. Topologies

### Topology A: Basic Redundant Diamond Topology
Used for initial testing and baseline verification.
```
             S2 (Port 1<->S1, Port 2<->S4)
            /  \
           /    \
H1 ── S1 ─        ─ S4 ── H4
           \    /
            \  /
             S3 (Port 1<->S1, Port 2<->S4)
```
- **Hosts**: H1 (10.0.0.1/24), H4 (10.0.0.4/24)
- **Switches**: S1, S2, S3, S4
- **Default Path**: `H1 -> S1 -> S2 -> S4 -> H4`
- **Alternate Path**: `H1 -> S1 -> S3 -> S4 -> H4`

---

### Topology B: Multi-Path Mesh Topology (Production Demo)
Used for multi-class traffic engineering, simultaneous failure tests, and performance comparison.
```
                 S2 (100M) ─────── S5 (100M)
                /   \             /   \
               /     \           /     \
H1 ── S1 (100M)        S4 (100M)        S7 ── H8
 (10.0.0.1)    \     /           \     /      (10.0.0.8)
                \   /             \   /
                 S3 (100M) ─────── S6 (100M)
```
- **Redundant Disjoint Paths**:
  - Path 1: `S1 -> S2 -> S5 -> S7`
  - Path 2: `S1 -> S3 -> S6 -> S7`
  - Path 3: `S1 -> S2 -> S4 -> S7`
  - Path 4: `S1 -> S3 -> S4 -> S7`
  - Path 5: `S1 -> S2 -> S4 -> S6 -> S7`

---

## 2. Link Configuration
- Default Link Bandwidth: 100 Mbps (simulated using Mininet TCLink `bw=100`)
- Default Link Latency: 5ms - 15ms (`delay='5ms'`)
- Max Queue Size: 100 packets (`max_queue_size=100`)
- Loss Rate: 0% nominal (`loss=0`)

---

## 3. Addressing Scheme
| Node | Interface | IP Address | MAC Address | Connected Switch / Port |
| :--- | :--- | :--- | :--- | :--- |
| H1 | h1-eth0 | 10.0.0.1/24 | 00:00:00:00:00:01 | S1 / Port 1 |
| H2 | h2-eth0 | 10.0.0.2/24 | 00:00:00:00:00:02 | S1 / Port 2 |
| H3 | h3-eth0 | 10.0.0.3/24 | 00:00:00:00:00:03 | S3 / Port 1 |
| H4 | h4-eth0 | 10.0.0.4/24 | 00:00:00:00:00:04 | S4 / Port 1 |
| H7 | h7-eth0 | 10.0.0.7/24 | 00:00:00:00:00:07 | S7 / Port 1 |
| H8 | h8-eth0 | 10.0.0.8/24 | 00:00:00:00:00:08 | S7 / Port 2 |
