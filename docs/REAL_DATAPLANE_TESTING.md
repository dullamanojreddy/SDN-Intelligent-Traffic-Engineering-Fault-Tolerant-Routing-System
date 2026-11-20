# Real Data-Plane Setup, Failover and Verification

This covers what runs against **real Mininet + Open vSwitch**: switch-level controller
failover, live topology edits, and flow-table verification.

## Components

| Piece | Where | Role |
| :--- | :--- | :--- |
| Controllers | `python -m controller.app` (primary `6653`/`8080`, standby `6654`/`8081`) | OpenFlow 1.3; roles arbitrated per switch |
| Mininet mesh | `network/topologies/mesh.py` | Switches connect to **every** controller in `SDN_CONTROLLERS` |
| Network agent | `network/agent.py` (inside the Mininet process, `SDN_AGENT_PORT`) | Applies add/remove node/link/host, link properties, link up/down; dumps OVS flows; reports OVS roles |
| Backend | `uvicorn backend.main:app` | Applies edits to the network **first**, rolls back on failure, syncs controllers, verifies flows |

### Controller roles (OpenFlow MASTER/SLAVE)
* Every controller sends `OFPT_ROLE_REQUEST` with an epoch-millisecond `generation_id`; the **switch**
  rejects stale requests, so two controllers can never both program one switch.
* A SLAVE cannot send FLOW_MOD/PACKET_OUT (`Datapath.write_guard`), so a standby never writes.
* Standby (`CONTROLLER_ROLE=standby`, `CONTROLLER_PEER_API_URL=<primary mgmt url>`) promotes itself after
  `CONTROLLER_HA_FAILURE_THRESHOLD` missed peer heartbeats, rebuilds routes, and yields to the primary after
  `CONTROLLER_HA_RECOVERY_THRESHOLD` healthy beats. The backend monitor can also assign roles (`POST /role`).
* The backend keeps standbys warm (pushes every topology snapshot to all healthy controllers) and resyncs a
  recovered controller before/while it takes mastership back (stale-state protection by snapshot version).
* Clocks must be roughly synchronised if controllers run on different hosts (generation ids are wall-clock ms).

### Live edits
`POST/DELETE /api/switches|hosts|links`, `PATCH /api/links/{src}/{dst}`, `POST /api/network/failure/simulate`
call the agent first (real `ovs-vsctl`/`ip link`/`tc`), verify the OpenFlow port number OVS really assigned,
and only then change the model. If the agent fails the model is restored (`topology unchanged`).
`GET /api/network/status` reports model-vs-network drift; `POST /api/network/reconcile?mode=adopt` makes the
running network the model. At startup the backend adopts the real topology when `NETWORK_AGENT_URL` is set.
Without an agent, links added through the API are **unconfirmed** and the router refuses to use them.

### Verification
`GET /api/routing/verify?source_ip=&dest_ip=` and `/api/routing/verify/all` replay the destination-IP rules from
`ovs-ofctl -O OpenFlow13 dump-flows` hop by hop and compare with the calculated route
(`VERIFIED`, `DIFFERENT_PATH`, `MISSING_RULES`, `BROKEN`, `UNAVAILABLE`). `POST /api/routing/install` now
reports the datapath result in `verification_status`.

## Running it

### Docker (macOS/Windows/Linux; verified on Docker Desktop)
```bash
docker build -f docker/Dockerfile.mininet -t sdn-ite-bench .
docker run --rm --privileged -v "$PWD":/work sdn-ite-bench /work/docker/run_real_tests.sh
```
Docker Desktop's VM has no OVS kernel module, so the bench uses OVS's **userspace datapath**
(`SDN_OVS_DATAPATH=user`, started by `docker/start_ovs.sh`). On a Linux host with the module, omit it.

Interactive bench (UI at the host):
```bash
docker run -d --name sdnbench --privileged -p 8000:8000 -v "$PWD":/work sdn-ite-bench sleep infinity
docker exec sdnbench /work/docker/run_bench.sh
cd frontend && npm run dev          # vite proxies /api to localhost:8000
```
Then try: kill the primary (`docker exec sdnbench /work/docker/controller_ctl.sh primary stop`), watch
`curl -H "Authorization: Bearer bench-token" localhost:9100/switch-roles` (inside the container) show the standby
as `master`, add/remove links in the Topology page, and press **Verify against OVS flow tables** on Routing.

### Native Linux
```bash
sudo apt install mininet openvswitch-switch iperf3
export CONTROLLER_API_TOKEN=secret
CONTROLLER_OF_PORT=6653 CONTROLLER_REST_PORT=8080 CONTROLLER_ROLE=primary CONTROLLER_PEER_API_URL=http://127.0.0.1:8081 python3 -m controller.app &
CONTROLLER_OF_PORT=6654 CONTROLLER_REST_PORT=8081 CONTROLLER_ID=standby CONTROLLER_ROLE=standby CONTROLLER_PEER_API_URL=http://127.0.0.1:8080 python3 -m controller.app &
sudo -E SDN_CONTROLLERS=127.0.0.1:6653,127.0.0.1:6654 SDN_AGENT_PORT=9100 python3 network/topologies/mesh.py
CONTROLLER_BACKUP_API_URLS=http://127.0.0.1:8081 NETWORK_AGENT_URL=http://127.0.0.1:9100 uvicorn backend.main:app
```
Do not run Mininet scripts with the repo root first on `sys.path`: the repo contains an IDE stub package named
`mininet` that would shadow the real one.

## Capacity in the cost function
`cost += delta * (1 - min(capacity, REFERENCE_CAPACITY_MBPS)/REFERENCE_CAPACITY_MBPS)`. `delta` is 0 by default
(and for VOICE/WEB/BACKGROUND), `0.15` for VIDEO, so idle thin links stop looking as good as fat ones for video
traffic without changing other routes. Override the default with `CAPACITY_WEIGHT`.
