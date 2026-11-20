#!/usr/bin/env python3
"""Measure controller failover/failback timing and packet loss on the live bench.

Run inside the bench container after docker/run_bench.sh:
    python3 /work/tests/real/measure_failover.py [cycles]
Reports, per cycle: time until OVS shows the standby as MASTER on every switch,
time until the backend fails over, packet loss of a steady 20 pps ping flow across
the transition, and (the worst case) recovery time of a flow that needs the
controller because a link on its path fails right when the primary dies.
"""
import os
import statistics
import subprocess
import sys
import time

import httpx

TOKEN = os.environ.get("CONTROLLER_API_TOKEN", "bench-token")
H = {"Authorization": f"Bearer {TOKEN}"}
BE, AG = "http://127.0.0.1:8000", "http://127.0.0.1:9100"
INTERVAL = 0.05


def be(m, p, **k): return httpx.request(m, BE + p, timeout=60, **k)
def ag(m, p, b=None): return httpx.request(m, AG + p, json=b, headers=H, timeout=60).json()
def ctl(who, action): subprocess.run(["/work/docker/controller_ctl.sh", who, action], check=True)


def masters():
    r = ag("GET", "/switch-roles")
    return {sw: next((c["target"].rsplit(":", 1)[1] for c in cs if c["role"] == "master" and c["connected"]), None)
            for sw, cs in r.items()}


def wait(pred, timeout=90, step=0.05):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if pred():
                return time.time() - t0
        except Exception:
            pass
        time.sleep(step)
    raise SystemExit("timeout waiting for condition")


def ping_start(src="h2", dst="10.0.0.7"):
    return ag("POST", "/ping-start", {"src": src, "dst_ip": dst, "interval": INTERVAL})["id"]


def ping_stop(pid):
    r = ag("POST", "/ping-stop", {"id": pid})
    r["outage_s"] = round(r["lost"] * INTERVAL, 2)
    return r


def stable_primary(samples=8, gap=0.25):
    """True once the primary has led every switch, with the standby a connected
    SLAVE, for several consecutive samples (role churn after a failback is real)."""
    for _ in range(samples):
        roles = ag("GET", "/switch-roles")
        ok = set(masters().values()) == {"6653"} and all(
            any(c["target"].endswith("6654") and c["role"] == "slave" and c["connected"] for c in cs)
            for cs in roles.values())
        if not ok:
            return False
        time.sleep(gap)
    return True


def settle():
    wait(stable_primary, timeout=120, step=0.2)
    wait(lambda: be("GET", "/api/controller/status").json()["active_role"] == "primary")
    wait(lambda: all(ag("POST", "/ping", {"src": s, "dst_ip": d, "count": 1})["ok"]
                     for s, d in (("h1", "10.0.0.7"), ("h2", "10.0.0.8"))))
    time.sleep(3)


def main(cycles):
    rows = []
    for i in range(1, cycles + 1):
        settle()
        # --- A: steady traffic (flows already installed) across failover and failback
        pid = ping_start()
        time.sleep(1)
        assert stable_primary(2), "bench not in a stable primary-master state before the kill"
        t_kill = time.time()
        ctl("primary", "stop")
        wait(lambda: set(masters().values()) == {"6654"})
        t_master = time.time() - t_kill
        wait(lambda: be("GET", "/api/controller/status").json()["active_role"] == "standby-1")
        t_backend = time.time() - t_kill
        time.sleep(1)
        failover_stats = ping_stop(pid)

        pid = ping_start()
        time.sleep(1)
        t_start = time.time()
        ctl("primary", "start")
        wait(lambda: set(masters().values()) == {"6653"})
        t_back = time.time() - t_start
        wait(lambda: be("GET", "/api/controller/status").json()["active_role"] == "primary")
        t_back_backend = time.time() - t_start
        time.sleep(1)
        failback_stats = ping_stop(pid)
        settle()

        # --- B: worst case - a link on the active path dies at the same moment the primary dies
        path = be("POST", "/api/routing/recalculate", json={"source_ip": "10.0.0.2", "dest_ip": "10.0.0.7"}).json()["selected_path"]
        a, b = path[0], path[1]
        pid = ping_start()
        time.sleep(1)
        t0 = time.time()
        ctl("primary", "stop")
        be("POST", "/api/network/failure/simulate", json={"src_switch": a, "dst_switch": b, "action": "DOWN"})
        wait(lambda: ag("POST", "/ping", {"src": "h2", "dst_ip": "10.0.0.7", "count": 1})["ok"], timeout=60, step=0.1)
        t_recover = time.time() - t0
        time.sleep(1)
        worst = ping_stop(pid)
        be("POST", "/api/network/failure/simulate", json={"src_switch": a, "dst_switch": b, "action": "UP"})
        ctl("primary", "start")
        rows.append(dict(cycle=i, standby_master_s=round(t_master, 2), backend_failover_s=round(t_backend, 2),
                         failover_lost=failover_stats["lost"], failover_outage_s=failover_stats["outage_s"],
                         primary_master_s=round(t_back, 2), backend_failback_s=round(t_back_backend, 2),
                         failback_lost=failback_stats["lost"], failback_outage_s=failback_stats["outage_s"],
                         worst_case_recover_s=round(t_recover, 2), worst_lost=worst["lost"]))
        print(rows[-1], flush=True)
    keys = [k for k in rows[0] if k != "cycle"]
    print("\nsummary over", cycles, "cycles (min / median / max):")
    for k in keys:
        v = [r[k] for r in rows]
        print(f"  {k:24s} {min(v):7.2f} {statistics.median(v):7.2f} {max(v):7.2f}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
