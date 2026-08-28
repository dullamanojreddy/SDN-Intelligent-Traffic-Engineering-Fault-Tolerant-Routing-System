#!/usr/bin/env bash
# Terminate all running SDN-ITE processes
echo "Stopping all SDN-ITE components..."
pkill -f "controller/app.py"
pkill -f "ryu-manager"
pkill -f "uvicorn"
pkill -f "vite"
sudo mn -c 2>/dev/null
echo "All processes stopped."
