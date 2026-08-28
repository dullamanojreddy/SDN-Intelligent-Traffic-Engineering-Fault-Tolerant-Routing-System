# Troubleshooting Guide

## 1. Common Issues & Resolutions

### Mininet & Open vSwitch
- **Error: `Exception: Error creating interface ... Cannot assign requested address`**
  - Fix: Clean stale Mininet state using `sudo mn -c`.
- **Error: `ovs-vswitchd is not running`**
  - Fix: Start OVS daemon: `sudo service openvswitch-switch start`.
- **Error: OpenFlow 1.3 Handshake Failure**
  - Fix: Ensure switches are configured with `protocols=OpenFlow13` (Mininet topology scripts in `network/topologies/` set this automatically).

### Controller (Ryu)
- **Error: `Address already in use (Port 6653 / 6633)`**
  - Fix: Terminate zombie controller processes: `sudo fuser -k 6653/tcp` or `sudo fuser -k 6633/tcp`.
- **Error: Eventlet / Python 3.12 compatibility**
  - Fix: Use Python 3.10 / 3.11 environment with compatible `eventlet` and `ryu` packages.

### Backend (FastAPI) & Database (MongoDB)
- **Warning: `MongoDB connection failed. Operating in in-memory fallback mode`**
  - Fix: This is a built-in resiliency feature. If MongoDB is not active on `localhost:27017`, the system falls back to an in-memory document store so all APIs continue to function normally. Start MongoDB if persistence across restarts is required.
- **WebSocket connection failed**
  - Fix: Verify that port `8000` is open and reachable from the frontend browser.

### Frontend
- **Blank page or API 404**
  - Fix: Verify Vite proxy in `vite.config.ts` or set `VITE_API_URL=http://localhost:8000` in `frontend/.env`.
