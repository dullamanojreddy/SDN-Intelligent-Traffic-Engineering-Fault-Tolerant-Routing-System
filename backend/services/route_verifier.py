"""Verify calculated routes against the flow tables actually installed in OVS.

``verify_route`` is pure: give it the calculated path, the model's port map and an
``ovs-ofctl dump-flows`` snapshot, and it replays the forwarding the switches would
do for the destination IP. Any difference from the calculated route is reported.
"""
from typing import Any, Dict, List, Optional, Tuple

IPV4_RULE_PRIORITY = 100  # priority the controller uses for destination rules


def _rule_for(flows: List[Dict[str, Any]], dst_ip: str) -> Optional[Dict[str, Any]]:
    """Highest-priority IPv4 rule that matches ``dst_ip`` (what OVS would pick)."""
    best = None
    for flow in flows:
        if "error" in flow or "ip" not in flow.get("protocols", []):
            continue
        nw_dst = flow["match"].get("nw_dst")
        if nw_dst is not None and nw_dst.split("/")[0] != dst_ip:
            continue
        if nw_dst is None and flow["match"]:        # some other, more specific rule
            continue
        if best is None or flow["priority"] > best["priority"]:
            best = flow
    if best is None:  # fall back to the table-miss rule
        misses = [f for f in flows if "error" not in f and f.get("priority") == 0]
        best = misses[0] if misses else None
    return best


def verify_route(
    expected_path: Optional[List[str]],
    src_switch: str,
    dst_switch: str,
    dst_host_port: int,
    dst_ip: str,
    flows_by_switch: Dict[str, List[Dict[str, Any]]],
    port_to_neighbor: Dict[Tuple[str, int], str],
    expected_ports: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """Replay installed forwarding from ``src_switch`` and compare with ``expected_path``."""
    hops: List[Dict[str, Any]] = []
    discrepancies: List[str] = []
    walked: List[str] = []
    current, delivered = src_switch, False
    visited = set()
    for _ in range(len(flows_by_switch) + 2):
        if current in visited:
            discrepancies.append(f"forwarding loop at {current}")
            break
        visited.add(current)
        walked.append(current)
        flows = flows_by_switch.get(current)
        exp_port = (expected_ports or {}).get(current)
        hop: Dict[str, Any] = {"switch": current, "expected_out_port": exp_port,
                               "installed_out_port": None, "priority": None, "packets": None}
        hops.append(hop)
        if flows is None:
            hop["status"] = "SWITCH_UNKNOWN"
            discrepancies.append(f"no flow table available for {current}")
            break
        rule = _rule_for(flows, dst_ip)
        if rule is None or rule["to_controller"] or rule["drop"] or not rule["out_ports"]:
            hop["status"] = "MISSING"
            what = "only the table-miss rule (traffic goes to the controller)" if rule and rule["to_controller"] \
                else "a drop rule" if rule and rule["drop"] else "no matching rule"
            discrepancies.append(f"{current}: no forwarding rule for {dst_ip} ({what})")
            break
        port = rule["out_ports"][0]
        hop.update(installed_out_port=port, priority=rule["priority"], packets=rule.get("n_packets"))
        if current == dst_switch and port == dst_host_port:
            hop["status"] = "DELIVERS_TO_HOST"
            delivered = True
            break
        nxt = port_to_neighbor.get((current, port))
        if nxt is None:
            hop["status"] = "BLACKHOLE"
            discrepancies.append(f"{current}: rule sends {dst_ip} out port {port}, which is not a known link"
                                 f"{' (destination host port is ' + str(dst_host_port) + ')' if current == dst_switch else ''}")
            break
        hop["status"] = "FORWARDS"
        hop["next_switch"] = nxt
        current = nxt

    if not delivered and not discrepancies:
        discrepancies.append("forwarding did not reach the destination host")
    if expected_path:
        for hop in hops:
            if hop.get("expected_out_port") is not None and hop["installed_out_port"] is not None \
                    and hop["expected_out_port"] != hop["installed_out_port"]:
                hop["status"] = "MISMATCH"
        if delivered and walked != expected_path:
            discrepancies.append(
                f"traffic is delivered via {' -> '.join(walked)} but the calculated route is {' -> '.join(expected_path)}")
        missing = [s for s in expected_path if s not in walked and not delivered]
        if missing and not delivered:
            discrepancies.append(f"calculated route switches not programmed: {', '.join(missing)}")
    if delivered and not discrepancies:
        status = "VERIFIED"
    elif delivered:
        status = "DIFFERENT_PATH"
    elif any(h["status"] == "MISSING" for h in hops):
        status = "MISSING_RULES"
    else:
        status = "BROKEN"
    return {
        "status": status,
        "verified": status == "VERIFIED",
        "delivered": delivered,
        "expected_path": expected_path,
        "installed_path": walked if delivered else walked,
        "hops": hops,
        "discrepancies": discrepancies,
    }
