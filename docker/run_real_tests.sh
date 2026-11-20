#!/bin/bash
# Run the real Mininet/OVS test-suite. From the repo root on a Docker host:
#   docker build -f docker/Dockerfile.mininet -t sdn-ite-bench .
#   docker run --rm --privileged -v "$PWD":/work sdn-ite-bench /work/docker/run_real_tests.sh
set -e
/work/docker/run_bench.sh
sleep 8   # let OpenFlow roles settle and proactive routes install
cd /work
SDN_REAL_BENCH=1 CONTROLLER_API_TOKEN="${CONTROLLER_API_TOKEN:-bench-token}" PYTHONDONTWRITEBYTECODE=1 \
  python3 -m pytest tests/real -v -p no:cacheprovider "$@"
