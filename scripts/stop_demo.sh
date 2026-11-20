#!/usr/bin/env bash
# Stop the demo network/controllers/backend container.
docker rm -f sdnbench >/dev/null 2>&1 && echo "demo container stopped" || echo "demo container was not running"
