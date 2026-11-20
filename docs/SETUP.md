# Environment Setup & Prerequisites

## 1. Operating Environment
- **Controller, Backend, Frontend**: Can run on Linux, macOS, or Windows (Node.js 18+, Python 3.10+).
- **Mininet & Open vSwitch Data Plane**: Requires a Linux kernel.
  - **Linux (Ubuntu 20.04/22.04 LTS)**: Native support.
  - **Windows**: Use Windows Subsystem for Linux (WSL2 Ubuntu 22.04) or a Linux Virtual Machine (VirtualBox / VMware).

---

## 2. Dependencies Installation

### A. Python Backend & Controller
```bash
# Create virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/WSL:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### B. Mininet & Open vSwitch (Linux / WSL2)
```bash
sudo apt update
sudo apt install -y mininet openvswitch-switch openvswitch-testcontroller iperf3 net-tools
sudo service openvswitch-switch start
sudo mn --test pingall  # Verify Mininet installation
```

### C. Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```

### D. MongoDB (Optional / Recommended)
- Native: `sudo apt install -y mongodb` or install MongoDB Community Server for Windows.
- Docker: `docker run -d -p 27017:27017 --name sdn-mongo mongo:latest`
- In-Memory Fallback: If MongoDB is not running, the FastAPI backend automatically operates with an in-memory database store so that all APIs, algorithms, and visualization work out-of-the-box.

---

## 3. Starting the System
1. **Start Ryu Controller**:
   ```bash
   python controller/app.py
   # Or using Ryu CLI: ryu-manager controller/app.py --verbose
   ```
2. **Start Backend Server**:
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```
3. **Start Frontend Dashboard**:
   ```bash
   cd frontend && npm run dev
   ```
4. **Launch Mininet Network (in Linux/WSL)**:
   ```bash
   sudo python network/topologies/mesh.py
   ```

---

## 4. Controller High Availability and Live Topology Editing

The backend heartbeats the controller management API and keeps the operator's
topology model in sync with it.

| Variable | Default | Meaning |
| :--- | :--- | :--- |
| `CONTROLLER_API_URL` | `http://127.0.0.1:8080` | Primary controller management API |
| `CONTROLLER_BACKUP_API_URLS` | _(empty)_ | Comma-separated standby controller management URLs, tried in order |
| `CONTROLLER_HEARTBEAT_INTERVAL_SEC` / `_TIMEOUT_SEC` | `2.0` / `1.5` | Heartbeat period and per-request timeout |
| `CONTROLLER_FAILURE_THRESHOLD` | `3` | Consecutive missed heartbeats before a controller is declared DOWN |
| `CONTROLLER_RECOVERY_THRESHOLD` | `2` | Consecutive good heartbeats before a controller is trusted again / fail-back |
| `CONTROLLER_OF_PORT`, `CONTROLLER_REST_PORT`, `CONTROLLER_ID` | `6653`, `8080`, `primary` | Per-instance ports and name (set different values for a standby) |

A standby is a second instance of `python -m controller.app` on different
ports. Point Mininet at both controllers (OVS keeps both connections); the
backend decides which management API to drive and pushes the full topology
snapshot to whichever becomes active. Status: `GET /api/controller/status`.

Topology edits (`POST/DELETE /api/switches|hosts|links`, `PATCH /api/links/{src}/{dst}`,
`POST /api/network/failure/simulate`) update the backend model, push a versioned
snapshot to the controller, re-evaluate every host-pair route and record a routing
decision per changed path. While no controller is reachable the edit is accepted
and reported as `PENDING_CONTROLLER_UNAVAILABLE`, then pushed on recovery.

Limitation: the controller cannot rewire Mininet. Switches/links added through the
API exist in the controller's routing model but are flagged
`data_plane_confirmed=false` until LLDP discovers them in the real network.
