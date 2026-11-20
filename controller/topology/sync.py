"""Controller-side export and application of the user-managed topology model.

The backend owns the *desired* topology (switches, links, link properties and
hosts that the operator edits at runtime). It pushes a versioned snapshot to
the controller, which applies it to the live ``NetworkGraph``. The controller
stays the source of truth for measured state (utilization, loss, port-down).
"""
import ipaddress
import math
from typing import Any, Dict, List, Set, Tuple

from controller.topology.graph import NetworkGraph


class SnapshotError(ValueError):
    """The pushed snapshot is malformed or internally inconsistent."""


def _finite(value: Any, name: str, low: float, high: float, *, exclusive_low: bool = False) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise SnapshotError(f"{name} must be a number") from None
    if not math.isfinite(number) or number > high or number < low or (exclusive_low and number == low):
        raise SnapshotError(f"{name} out of range: {value!r}")
    return number


def validate_snapshot(snapshot: Dict[str, Any]) -> None:
    """Raise SnapshotError unless the snapshot is complete and consistent."""
    if not isinstance(snapshot, dict):
        raise SnapshotError("snapshot must be an object")
    version = snapshot.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 0:
        raise SnapshotError("version must be a non-negative integer")
    switches = snapshot.get("switches")
    if not isinstance(switches, list) or not all(isinstance(s, str) and s for s in switches):
        raise SnapshotError("switches must be a list of names")
    if len(set(switches)) != len(switches):
        raise SnapshotError("duplicate switch names")
    known = set(switches)

    seen: Set[Tuple[str, str]] = set()
    for link in snapshot.get("links", []):
        src, dst = link.get("src"), link.get("dst")
        if src not in known or dst not in known:
            raise SnapshotError(f"link {src}-{dst} references an unknown switch")
        if src == dst:
            raise SnapshotError(f"link {src}-{dst} connects a switch to itself")
        key = tuple(sorted((src, dst)))
        if key in seen:
            raise SnapshotError(f"duplicate link {key[0]}-{key[1]}")
        seen.add(key)
        _finite(link.get("capacity_mbps", 100.0), "capacity_mbps", 0, 1_000_000, exclusive_low=True)
        _finite(link.get("latency_ms", 5.0), "latency_ms", 0, 60_000)
        _finite(link.get("loss_pct", 0.0), "loss_pct", 0, 100)
        for port_name in ("src_port", "dst_port"):
            port = link.get(port_name)
            if not isinstance(port, int) or isinstance(port, bool) or port < 1:
                raise SnapshotError(f"link {src}-{dst}: {port_name} must be a positive integer")

    ips: Set[str] = set()
    for host in snapshot.get("hosts", []):
        try:
            ip = str(ipaddress.IPv4Address(host.get("ip")))
        except (ipaddress.AddressValueError, ValueError):
            raise SnapshotError(f"invalid host IP: {host.get('ip')!r}") from None
        if ip in ips:
            raise SnapshotError(f"duplicate host IP {ip}")
        ips.add(ip)
        if host.get("switch") not in known:
            raise SnapshotError(f"host {ip} attached to unknown switch {host.get('switch')!r}")
        if not isinstance(host.get("port"), int) or host["port"] < 1:
            raise SnapshotError(f"host {ip}: port must be a positive integer")
        if not host.get("mac"):
            raise SnapshotError(f"host {ip}: mac is required")


def export_links(graph: NetworkGraph) -> List[Dict[str, Any]]:
    links = []
    for u, v, d in graph.graph.edges(data=True):
        links.append({
            "link_id": f"{u}-{v}",
            "src": u,
            "dst": v,
            "src_port": d.get("src_port", 1),
            "dst_port": d.get("dst_port", 1),
            "capacity_mbps": d.get("capacity_mbps", 100.0),
            "latency_ms": d.get("latency_ms", 5.0),
            "loss_pct": d.get("loss_pct", 0.0),
            "measured_loss_pct": d.get("measured_loss_pct", 0.0),
            "utilization_pct": d.get("utilization_pct", 0.0),
            "is_active": bool(d.get("is_active", True)),
            "status": getattr(d.get("status"), "value", d.get("status")),
            "data_plane_confirmed": bool(d.get("data_plane_confirmed", True)),
        })
    return links


def apply_snapshot(app: Any, snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a validated snapshot to the controller's graph and host tables.

    Returns a summary of what changed. Route reconciliation is the caller's job
    because it is asynchronous.
    """
    validate_snapshot(snapshot)
    graph = app.network_graph
    summary: Dict[str, Any] = {
        "added_switches": [], "removed_switches": [],
        "added_links": [], "removed_links": [], "updated_links": [],
        "hosts": 0,
    }

    wanted_switches = list(snapshot["switches"])
    for sw in wanted_switches:
        if not graph.graph.has_node(sw):
            graph.add_switch(sw)
            summary["added_switches"].append(sw)
    for sw in [n for n in graph.graph.nodes if n not in set(wanted_switches)]:
        graph.remove_switch(sw)  # its cached rules are deleted by the route reconcile
        summary["removed_switches"].append(sw)

    wanted_pairs: Set[Tuple[str, str]] = set()
    for link in snapshot.get("links", []):
        src, dst = link["src"], link["dst"]
        wanted_pairs.update({(src, dst), (dst, src)})
        props = dict(
            capacity_mbps=float(link.get("capacity_mbps", 100.0)),
            latency_ms=float(link.get("latency_ms", 5.0)),
            loss_pct=float(link.get("loss_pct", 0.0)),
        )
        wants_active = bool(link.get("is_active", True))
        for a, b, pa, pb in ((src, dst, link["src_port"], link["dst_port"]),
                             (dst, src, link["dst_port"], link["src_port"])):
            # A physically observed port-down always wins over the model.
            is_active = wants_active and f"{a}-{b}" not in app.port_down_links and \
                f"{b}-{a}" not in app.port_down_links
            if graph.graph.has_edge(a, b):
                edge = graph.graph[a][b]
                edge["src_port"], edge["dst_port"] = pa, pb
                changed = any(edge.get(k) != v for k, v in props.items()) or \
                    edge.get("is_active", True) != is_active
                graph.update_link_metrics(
                    a, b, utilization_pct=edge.get("utilization_pct", 0.0),
                    latency_ms=props["latency_ms"], loss_pct=props["loss_pct"],
                    is_active=is_active,
                )
                edge["capacity_mbps"] = props["capacity_mbps"]
                if link.get("confirmed"):
                    edge["data_plane_confirmed"] = True
                if changed:
                    summary["updated_links"].append(f"{a}-{b}")
            else:
                graph.add_link(a, b, pa, pb, is_active=is_active, **props)
                # Unconfirmed until the agent/backend vouches for it or LLDP sees it.
                graph.graph[a][b]["data_plane_confirmed"] = bool(link.get("confirmed", False))
                summary["added_links"].append(f"{a}-{b}")
    for u, v in [(u, v) for u, v in graph.graph.edges if (u, v) not in wanted_pairs]:
        graph.remove_link(u, v)
        summary["removed_links"].append(f"{u}-{v}")

    # Hosts: the snapshot is authoritative for host attachment.
    ph = app.packet_handler
    ph.host_ip_table.clear()
    ph.host_mac_table.clear()
    graph.hosts.clear()
    for host in snapshot.get("hosts", []):
        ip, mac, sw, port = host["ip"], host["mac"].lower(), host["switch"], host["port"]
        ph.host_ip_table[ip] = (sw, port, mac)
        ph.host_mac_table[mac] = (sw, port, ip)
        graph.add_host(f"h_{ip}", sw, port, ip, mac)
        summary["hosts"] += 1

    # Host attachment cannot be diffed cheaply, so callers always reconcile routes.
    summary["changed"] = True
    return summary
