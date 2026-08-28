# Troubleshooting Guide

## 1. Common Issues & Resolutions

### Mininet & Open vSwitch
- **Error: `Exception: Error creating interface ... Cannot assign requested address`**
  - Fix: Clean stale Mininet state using `sudo mn -c`.
- **Error: `ovs-vswitchd is not running`**
  - Fix: Start OVS daemon: `sudo service openvswitch-switch start`.
- **Error: OpenFlow 1.3 Handshake Failure**
  - Fix: Ensure switches are configured with `protocols=OpenFlow13` (Mininet topology scripts in `network/topologies/` set this automatically).
- **Issue: `pingall` failing / 100% Packet Loss / `X X` between hosts (Broadcast Storm)**
  - **Root Cause**: In multi-path mesh topologies (e.g., $s1 \rightarrow s2 \rightarrow s4 \rightarrow s3 \rightarrow s1$), ARP broadcasts circle the network loop indefinitely without STP, overwhelming switch CPUs.
  - **Option 1 (Recommended - Persistent Script Fix)**:
    Ensure all switches are initialized with `stp=True`:
    ```python
    self.addSwitch('s1', dpid='0000000000000001', protocols='OpenFlow13', stp=True)
    ```
    *Important*: Wait ~30 seconds after launching Mininet for the STP listening/learning phase to converge before issuing `pingall`.
  - **Option 2 (Emergency Mininet CLI Fix)**:
    Run the following in the active Mininet prompt to enable STP on the fly:
    ```bash
    mininet> sh ovs-vsctl set bridge s1 stp_enable=true
    mininet> sh ovs-vsctl set bridge s2 stp_enable=true
    mininet> sh ovs-vsctl set bridge s3 stp_enable=true
    mininet> sh ovs-vsctl set bridge s4 stp_enable=true
    mininet> sh ovs-vsctl set bridge s5 stp_enable=true
    mininet> sh ovs-vsctl set bridge s6 stp_enable=true
    mininet> sh ovs-vsctl set bridge s7 stp_enable=true
    ```
    Wait 30 seconds, then run `pingall`.

### Controller
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
