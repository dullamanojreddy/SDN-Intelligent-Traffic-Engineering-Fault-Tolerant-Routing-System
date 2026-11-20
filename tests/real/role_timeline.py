#!/usr/bin/env python3
"""Print how OVS's per-switch controller roles evolve after the primary is killed.

Run inside the bench container:  python3 /work/tests/real/role_timeline.py
Roles are shown as <controller port>:<m|s|o>, an 'x' marks a lost connection.
"""
import subprocess
import time

import httpx

H = {"Authorization": "Bearer bench-token"}


def roles():
    data = httpx.get("http://127.0.0.1:9100/switch-roles", headers=H, timeout=10).json()
    out = {}
    for sw, cs in sorted(data.items()):
        parts = []
        for c in sorted(cs, key=lambda c: c["target"]):
            lost = "" if c["connected"] else "x"
            parts.append(c["target"][-4:] + ":" + c["role"][0] + lost)
        out[sw] = ",".join(parts)
    return out


def summary(r):
    values = list(r.values())
    return " | ".join(f"{v} x{values.count(v)}" for v in sorted(set(values)))


t = time.time()
while time.time() - t < 60 and {v.split(",")[0] for v in roles().values()} != {"6653:m"}:
    time.sleep(0.5)
print("start:", summary(roles()))
t0 = time.time()
subprocess.run(["/work/docker/controller_ctl.sh", "primary", "stop"], check=True)
last = None
while time.time() - t0 < 9:
    s = summary(roles())
    if s != last:
        print(f"{time.time() - t0:5.2f}s {s}")
        last = s
    time.sleep(0.05)
subprocess.run(["/work/docker/controller_ctl.sh", "primary", "start"], check=True)
