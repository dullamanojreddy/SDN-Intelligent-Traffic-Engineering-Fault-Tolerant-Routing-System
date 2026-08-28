#!/usr/bin/env bash
# Start Mininet Multi-Path Network
echo "Starting Mininet Multi-Path Network Simulation..."
sudo mn -c
sudo python network/topologies/mesh.py
