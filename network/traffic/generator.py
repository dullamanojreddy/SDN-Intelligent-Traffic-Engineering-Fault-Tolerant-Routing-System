#!/usr/bin/env python3
"""
Traffic Generator Utility using iperf3 and ping
"""
import subprocess
import time
import argparse
from typing import Optional

def run_iperf_server(port: int = 5201):
    """Runs iperf3 server daemon."""
    print(f"Starting iperf3 server on port {port}...")
    subprocess.Popen(["iperf3", "-s", "-p", str(port)])

def run_iperf_client(
    target_ip: str,
    rate_mbps: float = 50.0,
    duration_sec: int = 30,
    port: int = 5201,
    protocol: str = "TCP"
):
    """Generates synthetic traffic to target IP."""
    print(f"Generating {protocol} traffic to {target_ip}:{port} at {rate_mbps} Mbps for {duration_sec}s...")
    cmd = ["iperf3", "-c", target_ip, "-p", str(port), "-t", str(duration_sec), "-b", f"{rate_mbps}M"]
    if protocol.upper() == "UDP":
        cmd.append("-u")
        
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    return res.returncode

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SDN-ITE Traffic Generator")
    parser.add_argument("--mode", choices=["server", "client"], default="client")
    parser.add_argument("--target", default="10.0.0.8")
    parser.add_argument("--rate", type=float, default=50.0)
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--proto", default="TCP")
    args = parser.parse_args()

    if args.mode == "server":
        run_iperf_server()
    else:
        run_iperf_client(args.target, rate_mbps=args.rate, duration_sec=args.duration, protocol=args.proto)
