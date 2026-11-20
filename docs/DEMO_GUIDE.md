# Demonstration Guide

**What the demo shows:** you describe a network in the UI → the *real* Mininet/Open vSwitch network is
changed → the controller and backend process it → routes, explanations and controller status update.

## 1. Start everything (one command)

Prerequisites: **Docker Desktop running**, **Node 18+**, this repository. No other setup, no `.env` file.

```bash
./scripts/start_demo.sh        # first run builds the Mininet/OVS image (a few minutes), later runs take ~1 min
```
It starts, inside one container: Open vSwitch, a **primary** and a **standby** controller, the Mininet
network (7 switches, 4 hosts) with its control agent, and the backend API; then starts the dashboard.
Open **http://localhost:5173**. Stop the network with `./scripts/stop_demo.sh` (Ctrl-C stops only the UI).

Everything is configured by the scripts (token `bench-token`, ports 6653/6654 OpenFlow, 8080/8081 controller
management, 9100 network agent, 8000 backend, 5173 UI). To change settings see `.env.example`.

Optional checks: `docker logs`-style output is in `/root/*.log` inside the container
(`docker exec sdnbench tail -f /root/backend.log`).

## 2. Demonstration script (≈10 minutes)

1. **Dashboard** (`/`) – 7 switches, 4 hosts, live topology map, **Controllers** panel: Primary *healthy / MASTER*,
   Standby *healthy / SLAVE*. Say: the switches are connected to both controllers; only the master programs them.
2. **Build the network** (`Topology Editor`):
   - *Add switch* `s8` → message "created (synced to controller)".
   - *Connect switches* `s1`–`s8`, then `s8`–`s7`.
   - *Add host* `h9`, IP `10.0.0.9`, switch `s8`.
   - Show invalid input handling: add another host with IP `10.0.0.9` (rejected: already exists) or `999.1.1.1`
     (rejected: invalid IPv4). The banner "Model matches the running Mininet network" stays green.
3. **Routing** (`Routing Decisions`): pick source `h1`, destination `h9`, tier *WEB*, click **Evaluate Dijkstra Paths**.
   - The route is **highlighted in gold** on the map (click a candidate card to highlight an alternative).
   - Read the explanation: weights, formula, total cost, per-link breakdown ("Show per-link breakdown"),
     and why each alternative was rejected (e.g. "0.0600 higher: latency +0.0600").
   - Click **Verify against OVS flow tables**: the flows really installed in the switches match the route.
4. **Change a link** (`Topology Editor` → click link `s1-s8` on the map): set *Latency* `80` and *Loss* `2`, **Apply**.
   Re-evaluate on the Routing page: the route moves to `s1→s2→s5→s7→s8`; the explanation shows the new costs.
5. **Disable a link**: select `s7-s8` → **Fail link** (red dashed on the map). Re-evaluate: route becomes `s1→s8`.
   If you also fail `s1-s8`, h9 is unreachable and the page shows **"No route exists"** with the reason
   (which switches are still reachable and which links are unusable).
6. **Restore** the link(s) → **Restore link**. Route returns; "Verify" shows *VERIFIED*.
7. **Controller failover** (second terminal): `docker exec sdnbench /work/docker/controller_ctl.sh primary stop`.
   Within ~1–3 s the navbar badge changes to *UP (standby-1)*, the Controllers panel shows the standby as ACTIVE
   with OpenFlow role MASTER, and an alert is recorded. Connectivity continues.
   Restore: `docker exec sdnbench /work/docker/controller_ctl.sh primary start` → fail-back to the primary after ~3 s.
   Optional: `controller_ctl.sh standby stop` as well to show the red "Controller unavailable" banner;
   topology edits made then are **queued** and applied automatically when a controller returns.

## 3. Reliable features (tested end to end, including on real Mininet/OVS)
- Add/remove switches, hosts, links; change latency/bandwidth/loss; fail/restore links — applied to the real network.
- Invalid input handling (duplicates, bad IP/MAC, unknown nodes, out-of-range values) with clear messages.
- Topology map with failed links shown red/dashed; new nodes placed without overlap; live link inspector.
- Multi-metric Dijkstra routing, ranked candidates, per-link cost breakdown, rejection reasons, unreachable diagnosis.
- Route highlighting; OVS flow-table verification; real flow counters on the Flow Tables page.
- Primary/standby status, OpenFlow roles, switch-level failover and fail-back, queued edits during an outage.

## 4. Avoid demonstrating (known limitations)
- **Experiments** page: no experiment runner exists (it shows an empty list; "start" returns "not implemented").
- **Traffic start/stop API** works (iperf3 in Mininet) but has no UI page; show real traffic via the Flow Tables counters
  only if you start it with `curl`.
- Failover is **not zero-downtime**: typically 1–3 s to a new master; flows that need the controller during that
  window (e.g. a link fails at the same time) can lose ~1 s of packets. Existing flows keep forwarding.
- Don't run `Add link` between *existing* linked switches (rejected by design) or names longer than 15 chars.
- Don't rapidly click edits (each one waits for the real network); wait for the green message between edits.
- Running **without Docker** (`uvicorn` + a controller only) is *model-only*: links you add are marked unconfirmed and are
  never used for routing, and verification/real traffic are unavailable. Use `start_demo.sh` for the demo.
- Backend API has no user login (demo setting). The `Settings` page is not wired up; it is not linked in the menu.
- Docker Desktop uses OVS's userspace datapath (slower than kernel OVS, fine for this scale).
