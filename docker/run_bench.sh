#!/bin/bash
# Inside the bench container: start OVS, a primary + standby controller, the
# headless Mininet mesh with the network agent, and the backend API.
#   OpenFlow 6653 (primary) / 6654 (standby); management 8080 / 8081; agent 9100; backend 8000.
#   Logs: /root/*.log
set -e
export CONTROLLER_API_TOKEN="${CONTROLLER_API_TOKEN:-bench-token}" PYTHONDONTWRITEBYTECODE=1
cd /work
pgrep ovs-vswitchd >/dev/null || /work/docker/start_ovs.sh
pkill -f "uvicorn backend.main" 2>/dev/null || true
pkill -f "topologies/mesh.py" 2>/dev/null || true
/work/docker/controller_ctl.sh primary stop; /work/docker/controller_ctl.sh standby stop
pkill -9 -f "controller.app" 2>/dev/null || true
(cd /root && mn -c >/dev/null 2>&1 || true)
rm -f /root/*.log
sleep 1
/work/docker/controller_ctl.sh primary start
/work/docker/controller_ctl.sh standby start
sleep 3
cd /root
SDN_CONTROLLERS=127.0.0.1:6653,127.0.0.1:6654 SDN_AGENT_PORT=9100 SDN_OVS_DATAPATH=user SDN_HEADLESS=1 \
  nohup python3 /work/network/topologies/mesh.py > /root/mininet.log 2>&1 &
for _ in $(seq 1 60); do
  curl -sf -H "Authorization: Bearer $CONTROLLER_API_TOKEN" localhost:9100/health >/dev/null 2>&1 && break; sleep 1
done
cd /work
CONTROLLER_API_URL=http://127.0.0.1:8080 CONTROLLER_BACKUP_API_URLS=http://127.0.0.1:8081 \
  NETWORK_AGENT_URL=http://127.0.0.1:9100 CONTROLLER_HEARTBEAT_INTERVAL_SEC=0.5 CONTROLLER_HEARTBEAT_TIMEOUT_SEC=0.8 \
  CONTROLLER_FAILURE_THRESHOLD=2 CONTROLLER_RECOVERY_THRESHOLD=2 \
  nohup python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > /root/backend.log 2>&1 &
for _ in $(seq 1 30); do curl -sf localhost:8000/health >/dev/null 2>&1 && break; sleep 1; done
echo "bench up"
