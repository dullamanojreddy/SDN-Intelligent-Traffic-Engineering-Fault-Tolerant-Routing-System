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
