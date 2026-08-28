#!/usr/bin/env bash
# Start SDN Controller
echo "Starting SDN-ITE Ryu OpenFlow 1.3 Controller..."
if command -v ryu-manager &> /dev/null; then
    ryu-manager controller/app.py --verbose --ofp-tcp-listen-port 6653
else
    python controller/app.py
fi
