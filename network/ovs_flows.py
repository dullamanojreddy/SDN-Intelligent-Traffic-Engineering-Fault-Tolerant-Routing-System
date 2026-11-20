"""Parse ``ovs-ofctl dump-flows`` output (stdlib only, shared by agent and backend)."""
import re
import subprocess
from typing import Any, Dict, List, Optional

_KV = re.compile(r"^([A-Za-z_0-9]+)=(.*)$")


def _port_number(token: str) -> Optional[int]:
    token = token.strip().strip('"')
    if token.isdigit():
        return int(token)
    named = re.search(r"-eth(\d+)$", token)
    return int(named.group(1)) if named else None


def parse_flow_line(line: str, switch: str = "") -> Optional[Dict[str, Any]]:
    """Parse one dump-flows line into a structured flow, or None for non-flow lines."""
    line = line.strip()
    if " actions=" not in line or "priority=" not in line and "table=" not in line:
        return None
    head, actions = line.split(" actions=", 1)
    flow: Dict[str, Any] = {"switch": switch, "match": {}, "protocols": []}
    for token in head.split(","):
        token = token.strip()
        if not token:
            continue
        kv = _KV.match(token)
        if not kv:
            flow["protocols"].append(token)           # bare words: ip, arp, ipv6, tcp ...
            continue
        key, value = kv.groups()
        if key in ("cookie", "duration", "table", "n_packets", "n_bytes",
                   "idle_timeout", "hard_timeout", "idle_age", "hard_age", "priority"):
            if key == "duration":
                flow[key] = float(value.rstrip("s"))
            elif key == "cookie":
                flow[key] = int(value, 16)
            else:
                flow[key] = int(value)
        else:
            flow["match"][key] = value
    flow.setdefault("priority", 32768)
    flow["actions"] = actions.strip()
    out_ports: List[int] = []
    for action in actions.split(","):
        action = action.strip()
        if action.lower().startswith("output:"):
            port = _port_number(action.split(":", 1)[1])
            if port is not None:
                out_ports.append(port)
    flow["out_ports"] = out_ports
    flow["to_controller"] = "controller" in actions.lower()
    flow["drop"] = actions.strip().lower() in ("drop", "")
    return flow


def parse_dump_flows(text: str, switch: str = "") -> List[Dict[str, Any]]:
    flows = []
    for line in text.splitlines():
        parsed = parse_flow_line(line, switch)
        if parsed:
            flows.append(parsed)
    return flows


def dump_flows(switch: str, timeout: float = 5.0) -> List[Dict[str, Any]]:
    """Run ovs-ofctl against a local bridge and parse its flow table."""
    result = subprocess.run(
        ["ovs-ofctl", "-O", "OpenFlow13", "--no-names", "dump-flows", switch],
        capture_output=True, text=True, timeout=timeout, check=True,
    )
    return parse_dump_flows(result.stdout, switch)
