#!/usr/bin/env bash
# One-command demo: real Mininet/OVS network + 2 controllers + backend in Docker,
# dashboard on http://localhost:5173. Requires Docker Desktop (running) and Node 18+.
set -e
cd "$(dirname "$0")/.."
docker info >/dev/null 2>&1 || { echo "Docker is not running - start Docker Desktop first."; exit 1; }
docker image inspect sdn-ite-bench >/dev/null 2>&1 || docker build -f docker/Dockerfile.mininet -t sdn-ite-bench .
docker rm -f sdnbench >/dev/null 2>&1 || true
docker run -d --name sdnbench --privileged -p 8000:8000 -v "$PWD":/work sdn-ite-bench sleep infinity >/dev/null
docker exec sdnbench /work/docker/run_bench.sh
echo "Backend + network up. Starting the dashboard (Ctrl-C stops the UI; run scripts/stop_demo.sh to stop the network)."
cd frontend
[ -d node_modules ] || npm install
npm run dev -- --port 5173
