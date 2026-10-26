#!/usr/bin/env python3
"""Display the currently installed OpenFlow path from H1 to H7.

This script is read-only. It queries OVS flow tables and follows the
destination-based IPv4 rule installed for H7. Run it from the Mininet
repository root while the Mininet network is running:

    sh python3 scripts/show_path.py
"""

import re
import subprocess
import sys
from typing import Dict, Optional, Tuple


DESTINATION_IP = "10.0.0.7"
SOURCE_SWITCH = "s1"
DESTINATION_SWITCH = "s7"
DESTINATION_HOST_PORT = 4
FLOW_PRIORITY = 100
MAX_HOPS = 8

# The map describes the Mininet mesh wiring. The forwarding decision itself
# always comes from the installed OpenFlow rule.
LINKS: Dict[Tuple[str, int], str] = {
    ("s1", 1): "s2",
    ("s1", 2): "s3",
    ("s2", 1): "s1",
    ("s2", 2): "s4",
    ("s2", 3): "s5",
    ("s3", 1): "s1",
    ("s3", 2): "s4",
    ("s3", 3): "s6",
    ("s4", 1): "s2",
    ("s4", 2): "s3",
    ("s4", 3): "s7",
    ("s5", 1): "s2",
    ("s5", 2): "s7",
    ("s6", 1): "s3",
    ("s6", 2): "s7",
    ("s7", 1): "s4",
    ("s7", 2): "s5",
    ("s7", 3): "s6",
}


def _flow_output_port(switch: str) -> Optional[int]:
    """Return the installed destination rule's output port for a switch."""
    command = [
        "ovs-ofctl",
        "-O",
        "OpenFlow13",
        "dump-flows",
        switch,
    ]
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print("ovs-ofctl was not found; run this inside the Mininet environment.")
        return None
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or str(error)
        print(f"Unable to read flows from {switch}: {detail}")
        return None

    for line in result.stdout.splitlines():
        if (
            f"priority={FLOW_PRIORITY}," not in line
            or f"nw_dst={DESTINATION_IP}" not in line
            or "actions=" not in line
        ):
            continue

        action = line.split("actions=", 1)[1]
        match = re.search(r"(?:^|,)output:(\d+)(?:,|$)", action)
        if match:
            return int(match.group(1))

    return None


def show_path() -> int:
    """Follow installed forwarding rules and print the active path."""
    current = SOURCE_SWITCH
    path = ["H1", SOURCE_SWITCH.upper()]
    visited = set()

    for _ in range(MAX_HOPS):
        if current in visited:
            print("Routing loop detected:", " → ".join(path))
            return 1
        visited.add(current)

        port = _flow_output_port(current)
        if port is None:
            print(f"No installed route at {current} for {DESTINATION_IP}")
            return 1

        if current == DESTINATION_SWITCH and port == DESTINATION_HOST_PORT:
            path.append("H7")
            print("ACTIVE PATH:", " → ".join(path))
            return 0

        next_switch = LINKS.get((current, port))
        if next_switch is None:
            print(f"Unknown next hop: {current} port {port}")
            return 1

        path.append(next_switch.upper())
        current = next_switch

    print("Path incomplete:", " → ".join(path))
    return 1


if __name__ == "__main__":
    sys.exit(show_path())
