"""
Topology Service - operator-managed network model merged with live controller telemetry.

The backend owns the *desired* topology (what the operator edits at runtime) and
bumps ``version`` on every change; the controller owns *measured* state
(utilization, loss, port-down). ``apply_live_state`` merges the latter into the
former so routing explanations use real measurements.
"""
from typing import List, Dict, Optional, Any
import copy
import ipaddress
import re
import threading
import time
from controller.topology.graph import NetworkGraph
from controller.models.topology import SwitchNode, HostNode, LinkEdge, TopologyData, LinkStatus
from controller.topology.state_bridge import get_link_states

_MAC_RE = re.compile(r"^([0-9a-f]{2}:){5}[0-9a-f]{2}$")


class TopologyService:
    def __init__(self):
        self.network_graph = NetworkGraph()
        self.hosts: Dict[str, HostNode] = {}
        self._lock = threading.RLock()
        # Time-based start keeps versions monotonic across backend restarts, so a
        # long-running controller never rejects a fresh backend as "stale".
        self.version = int(time.time() * 1000)
        self.live_state: Optional[Dict[str, Any]] = None
        self._init_mock_or_real_topology()

    def _init_mock_or_real_topology(self):
        """Initializes the baseline 7-switch mesh topology and its four hosts."""
        switches = [
            ("s1", 1, "Switch 1 (Ingress)"),
            ("s2", 2, "Switch 2 (Core Top)"),
            ("s3", 3, "Switch 3 (Core Bottom)"),
            ("s4", 4, "Switch 4 (Core Center)"),
            ("s5", 5, "Switch 5 (Aggregation Top)"),
            ("s6", 6, "Switch 6 (Aggregation Bottom)"),
            ("s7", 7, "Switch 7 (Egress)"),
        ]
        for dpid, dpid_int, name in switches:
            self.network_graph.add_switch(dpid, dpid_int=dpid_int, name=name)

        # (u, v, port_u, port_v, capacity_mbps, latency_ms) - matches mesh.py wiring.
        links = [
            ("s1", "s2", 1, 1, 100.0, 5.0),
            ("s1", "s3", 2, 1, 100.0, 5.0),
            ("s2", "s4", 2, 1, 100.0, 6.0),
            ("s2", "s5", 3, 1, 100.0, 5.0),
            ("s3", "s4", 2, 2, 100.0, 6.0),
            ("s3", "s6", 3, 1, 100.0, 5.0),
            ("s4", "s7", 3, 1, 100.0, 5.0),
            ("s5", "s7", 2, 2, 100.0, 5.0),
            ("s6", "s7", 2, 3, 100.0, 5.0),
        ]
        for u, v, p1, p2, cap, lat in links:
            self._add_edges(u, v, p1, p2, cap, lat)

        for name, ip, mac, sw, port in [
            ("h1", "10.0.0.1", "00:00:00:00:00:01", "s1", 3),
            ("h2", "10.0.0.2", "00:00:00:00:00:02", "s1", 4),
            ("h7", "10.0.0.7", "00:00:00:00:00:07", "s7", 4),
            ("h8", "10.0.0.8", "00:00:00:00:00:08", "s7", 5),
        ]:
            self.hosts[name] = HostNode(mac=mac, ip=ip, connected_switch=sw, connected_port=port, name=name)

    def _add_edges(self, u, v, p1, p2, cap, lat, loss=0.0):
        for a, b, pa, pb in ((u, v, p1, p2), (v, u, p2, p1)):
            self.network_graph.add_link(a, b, pa, pb, capacity_mbps=cap, latency_ms=lat, loss_pct=loss)
            self.network_graph.graph[a][b]["admin_active"] = True

    # ------------------------------------------------- transactions / adoption
    def checkpoint(self) -> Dict[str, Any]:
        """Copy of everything an edit can change, for rollback."""
        with self._lock:
            return {"graph": copy.deepcopy(self.network_graph.graph),
                    "hosts": copy.deepcopy(self.hosts), "version": self.version}

    def restore(self, cp: Dict[str, Any]) -> None:
        with self._lock:
            self.network_graph.graph.clear()
            self.network_graph.graph.update(cp["graph"])          # nodes, edges and graph attrs
            self.hosts.clear()
            self.hosts.update(cp["hosts"])
            self.version = max(self.version, cp["version"]) + 1   # versions never go backwards

    def mark_confirmed(self, src: str, dst: str, confirmed: bool = True) -> None:
        with self._lock:
            for a, b in ((src.lower(), dst.lower()), (dst.lower(), src.lower())):
                if self.network_graph.graph.has_edge(a, b):
                    self.network_graph.graph[a][b]["data_plane_confirmed"] = confirmed

    @staticmethod
    def _ms(value: Any, default: float) -> float:
        if value is None:
            return default
        try:
            return float(str(value).lower().replace("ms", "").strip())
        except ValueError:
            return default

    def adopt(self, real: Dict[str, Any]) -> None:
        """Replace the model with the topology of the running network (the truth)."""
        with self._lock:
            graph = self.network_graph.graph
            admin = {(u, v): d.get("admin_active", True) for u, v, d in graph.edges(data=True)}
            graph.clear()
            self.hosts.clear()
            for sw in real["switches"]:
                self.network_graph.add_switch(sw["name"], dpid_int=sw["dpid"], name=sw["name"])
            for link in real["links"]:
                cap = float(link["bw"]) if link.get("bw") else 100.0
                self._add_edges(link["src"], link["dst"], link["src_port"], link["dst_port"], cap,
                                self._ms(link.get("delay"), 0.0), float(link.get("loss") or 0.0))
                for a, b in ((link["src"], link["dst"]), (link["dst"], link["src"])):
                    edge = graph[a][b]
                    edge["data_plane_confirmed"] = True
                    edge["admin_active"] = bool(link.get("up", True))
                    edge["is_active"] = bool(link.get("up", True))
                    if not edge["admin_active"]:
                        self.network_graph.update_link_metrics(a, b, utilization_pct=0.0, is_active=False)
            for host in real["hosts"]:
                self.hosts[host["name"].lower()] = HostNode(
                    mac=host["mac"], ip=host["ip"], connected_switch=host["switch"],
                    connected_port=host["port"], name=host["name"])
            self._bump()

    def drift(self, real: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Differences between the model and the running network."""
        issues: List[Dict[str, Any]] = []
        with self._lock:
            graph = self.network_graph.graph
            model_sw, real_sw = set(graph.nodes), {s["name"] for s in real["switches"]}
            issues += [{"kind": "switch", "name": n, "problem": "in model, missing from network"} for n in sorted(model_sw - real_sw)]
            issues += [{"kind": "switch", "name": n, "problem": "in network, missing from model"} for n in sorted(real_sw - model_sw)]
            real_links = {tuple(sorted((l["src"], l["dst"]))): l for l in real["links"]}
            model_links = {tuple(sorted((u, v))): d for u, v, d in graph.edges(data=True)}
            for key in sorted(set(model_links) - set(real_links)):
                issues.append({"kind": "link", "name": "-".join(key), "problem": "in model, missing from network"})
            for key in sorted(set(real_links) - set(model_links)):
                issues.append({"kind": "link", "name": "-".join(key), "problem": "in network, missing from model"})
            for key in sorted(set(real_links) & set(model_links)):
                link, d = real_links[key], graph[key[0]][key[1]]
                rp = (link["src_port"], link["dst_port"]) if link["src"] == key[0] else (link["dst_port"], link["src_port"])
                if rp != (d.get("src_port"), d.get("dst_port")):
                    issues.append({"kind": "link", "name": "-".join(key), "problem": f"port mismatch: network {rp}, model {(d.get('src_port'), d.get('dst_port'))}"})
                if bool(link.get("up", True)) != bool(d.get("admin_active", True)):
                    issues.append({"kind": "link", "name": "-".join(key), "problem": f"state mismatch: network up={link.get('up')}, model up={d.get('admin_active', True)}"})
            real_hosts = {h["name"].lower(): h for h in real["hosts"]}
            for name in sorted(set(self.hosts) - set(real_hosts)):
                issues.append({"kind": "host", "name": name, "problem": "in model, missing from network"})
            for name in sorted(set(real_hosts) - set(self.hosts)):
                issues.append({"kind": "host", "name": name, "problem": "in network, missing from model"})
            for name in sorted(set(real_hosts) & set(self.hosts)):
                h, m = real_hosts[name], self.hosts[name]
                if (h["ip"], h["switch"], h["port"]) != (m.ip, m.connected_switch, m.connected_port):
                    issues.append({"kind": "host", "name": name, "problem": f"attachment mismatch: network {(h['ip'], h['switch'], h['port'])}, model {(m.ip, m.connected_switch, m.connected_port)}"})
        return issues

    def ensure_version_above(self, version: int) -> None:
        """Lift the topology version above one a controller already holds."""
        with self._lock:
            self.version = max(self.version, version) + 1

    def _bump(self) -> int:
        self.version += 1
        return self.version

    # ------------------------------------------------------------ live state
    def apply_live_state(self, state: Dict[str, Any]) -> None:
        """Merge controller-measured utilization/loss/port state into the model."""
        with self._lock:
            self.live_state = state
            graph = self.network_graph.graph
            for link in state.get("links", []):
                u, v = link["src"], link["dst"]
                if not graph.has_edge(u, v):
                    continue
                edge = graph[u][v]
                edge["live_active"] = bool(link.get("is_active", True))
                edge["data_plane_confirmed"] = bool(edge.get("data_plane_confirmed", True)) or bool(
                    link.get("data_plane_confirmed"))
                # Measured drops are kept apart from the configured loss the operator set.
                edge["measured_loss_pct"] = float(link.get("measured_loss_pct", 0.0))
                self.network_graph.update_link_metrics(
                    u, v,
                    utilization_pct=float(link.get("utilization_pct", 0.0)),
                    is_active=edge.get("admin_active", True) and edge["live_active"],
                )

    # ------------------------------------------------------------- snapshots
    def snapshot(self) -> Dict[str, Any]:
        """The desired topology in the form the controller's /topology/sync accepts."""
        with self._lock:
            graph = self.network_graph.graph
            links = []
            for u, v, d in graph.edges(data=True):
                if u < v and graph.has_edge(v, u):
                    links.append({
                        "src": u, "dst": v,
                        "src_port": d.get("src_port", 1), "dst_port": d.get("dst_port", 1),
                        "capacity_mbps": d.get("capacity_mbps", 100.0),
                        "latency_ms": d.get("latency_ms", 5.0),
                        "loss_pct": d.get("loss_pct", 0.0),
                        "is_active": d.get("admin_active", True),
                        "confirmed": bool(d.get("data_plane_confirmed", True)),
                    })
            return {
                "version": self.version,
                "switches": list(graph.nodes),
                "links": links,
                "hosts": [
                    {"ip": h.ip, "mac": h.mac, "switch": h.connected_switch, "port": h.connected_port}
                    for h in self.hosts.values()
                ],
            }

    def get_topology(self) -> TopologyData:
        with self._lock:
            live = {s["dpid"]: s for s in (self.live_state or {}).get("switches", [])}
            switches: List[SwitchNode] = []
            for n, d in self.network_graph.graph.nodes(data=True):
                switches.append(SwitchNode(
                    dpid=n,
                    dpid_int=d.get("dpid_int", 1),
                    name=d.get("name", f"Switch {n.upper()}"),
                    connected=bool(live.get(n, {}).get("connected", False)),
                    active_flows=int(live.get(n, {}).get("active_flows", 0)),
                ))

            # The file bridge is only a fallback for deployments that never reached
            # the controller's HTTP API.
            file_states = get_link_states() if self.live_state is None else {}
            links: List[LinkEdge] = []
            for u, v, d in self.network_graph.graph.edges(data=True):
                link_id = f"{u}-{v}"
                is_active = file_states.get(link_id, d.get("is_active", True))
                status = LinkStatus.FAILED if not is_active else d.get("status", LinkStatus.NORMAL)
                links.append(LinkEdge(
                    link_id=link_id,
                    src_dpid=u,
                    src_port=d.get("src_port", 1),
                    dst_dpid=v,
                    dst_port=d.get("dst_port", 1),
                    capacity_mbps=d.get("capacity_mbps", 100.0),
                    current_rate_mbps=round(d.get("utilization_pct", 0.0) * d.get("capacity_mbps", 100.0) / 100.0, 2),
                    utilization_pct=d.get("utilization_pct", 0.0),
                    latency_ms=d.get("latency_ms", 5.0),
                    packet_loss_pct=max(d.get("loss_pct", 0.0), d.get("measured_loss_pct", 0.0)),
                    status=status,
                    is_active=is_active,
                    data_plane_confirmed=d.get("data_plane_confirmed"),
                ))

            return TopologyData(
                switches=switches,
                hosts=list(self.hosts.values()),
                links=links,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

    # ------------------------------------------------------------ validation
    @staticmethod
    def _normalise_name(name: str) -> str:
        return name.strip().lower()

    @staticmethod
    def _validate_ip(ip: str) -> str:
        try:
            addr = ipaddress.IPv4Address(ip.strip())
        except (ipaddress.AddressValueError, ValueError):
            raise ValueError(f"Invalid IPv4 address: {ip}") from None
        if addr.is_multicast or addr.is_unspecified or addr.is_loopback or addr.is_reserved:
            raise ValueError(f"IP address is not a usable host address: {ip}")
        return str(addr)

    # -------------------------------------------------------------- switches
    def add_switch(self, name: str) -> SwitchNode:
        with self._lock:
            node_id = self._normalise_name(name)
            if not re.fullmatch(r"[a-z][a-z0-9_-]*", node_id):
                raise ValueError("Switch name must start with a letter and contain only letters, numbers, _ or -")
            if self.network_graph.graph.has_node(node_id):
                raise ValueError(f"Switch already exists: {name}")
            numeric_ids = [
                data.get("dpid_int", 0)
                for _, data in self.network_graph.graph.nodes(data=True)
            ]
            dpid_int = max(numeric_ids, default=0) + 1
            self.network_graph.add_switch(
                node_id, dpid_int=dpid_int, name=name.strip(), active_flows=0
            )
            self._bump()
            return next(sw for sw in self.get_topology().switches if sw.dpid == node_id)

    def remove_switch(self, name: str) -> List[str]:
        """Remove a switch, its links and attached hosts. Returns removed host names."""
        with self._lock:
            node_id = self._normalise_name(name)
            if not self.network_graph.graph.has_node(node_id):
                raise KeyError(f"Switch not found: {name}")
            self.network_graph.remove_switch(node_id)
            removed_hosts = [
                host_id for host_id, host in self.hosts.items()
                if host.connected_switch == node_id
            ]
            for host_id in removed_hosts:
                del self.hosts[host_id]
            self._bump()
            return removed_hosts

    # ----------------------------------------------------------------- hosts
    def add_host(self, name: str, ip: str, switch: str, mac: Optional[str] = None) -> HostNode:
        with self._lock:
            host_id = self._normalise_name(name)
            switch_id = self._normalise_name(switch)
            ip = self._validate_ip(ip)
            if host_id in self.hosts:
                raise ValueError(f"Host already exists: {name}")
            if not self.network_graph.graph.has_node(switch_id):
                raise KeyError(f"Switch not found: {switch}")
            if any(host.ip == ip for host in self.hosts.values()):
                raise ValueError(f"IP address already exists: {ip}")
            if mac is None:
                octets = ipaddress.IPv4Address(ip).packed
                mac = "02:00:" + ":".join(f"{b:02x}" for b in octets)  # unique per IP
            mac = mac.strip().lower()
            if not _MAC_RE.match(mac):
                raise ValueError(f"Invalid MAC address: {mac}")
            if any(host.mac == mac for host in self.hosts.values()):
                raise ValueError(f"MAC address already exists: {mac}")
            port = self._next_switch_port(switch_id)
            host = HostNode(
                mac=mac, ip=ip, connected_switch=switch_id,
                connected_port=port, name=name.strip(),
            )
            self.hosts[host_id] = host
            self._bump()
            return host

    def remove_host(self, name: str) -> None:
        with self._lock:
            host_id = self._normalise_name(name)
            if host_id not in self.hosts:
                raise KeyError(f"Host not found: {name}")
            del self.hosts[host_id]
            self._bump()

    # ----------------------------------------------------------------- links
    def add_connection(self, src: str, dst: str, capacity_mbps: float, latency_ms: float,
                       loss_pct: float = 0.0) -> None:
        with self._lock:
            src_id, dst_id = self._normalise_name(src), self._normalise_name(dst)
            if src_id == dst_id:
                raise ValueError("A node cannot connect to itself")
            if not self.network_graph.graph.has_node(src_id) or not self.network_graph.graph.has_node(dst_id):
                raise KeyError("Both endpoints must be existing switches")
            if self.network_graph.graph.has_edge(src_id, dst_id):
                raise ValueError(f"Connection already exists: {src}-{dst}")
            src_port = self._next_switch_port(src_id)
            dst_port = self._next_switch_port(dst_id)
            self._add_edges(src_id, dst_id, src_port, dst_port, capacity_mbps, latency_ms, loss_pct)
            for a, b in ((src_id, dst_id), (dst_id, src_id)):
                self.network_graph.graph[a][b]["data_plane_confirmed"] = False
            self._bump()

    def remove_connection(self, src: str, dst: str) -> None:
        with self._lock:
            src_id, dst_id = self._normalise_name(src), self._normalise_name(dst)
            if not self.network_graph.graph.has_edge(src_id, dst_id):
                raise KeyError(f"Connection not found: {src}-{dst}")
            self.network_graph.remove_link(src_id, dst_id)
            self.network_graph.remove_link(dst_id, src_id)
            self._bump()

    def update_connection(self, src: str, dst: str, capacity_mbps: Optional[float] = None,
                          latency_ms: Optional[float] = None, loss_pct: Optional[float] = None) -> Dict[str, float]:
        """Change link properties (both directions). Returns the properties applied."""
        with self._lock:
            src_id, dst_id = self._normalise_name(src), self._normalise_name(dst)
            graph = self.network_graph.graph
            if not graph.has_edge(src_id, dst_id) or not graph.has_edge(dst_id, src_id):
                raise KeyError(f"Connection not found: {src}-{dst}")
            changes = {k: v for k, v in (
                ("capacity_mbps", capacity_mbps), ("latency_ms", latency_ms), ("loss_pct", loss_pct),
            ) if v is not None}
            if not changes:
                raise ValueError("Provide at least one of capacity_mbps, latency_ms, loss_pct")
            for a, b in ((src_id, dst_id), (dst_id, src_id)):
                graph[a][b].update(changes)
            self._bump()
            return changes

    def set_link_state(self, src: str, dst: str, is_active: bool) -> None:
        """Administratively enable/disable a link (both directions)."""
        with self._lock:
            src_id, dst_id = self._normalise_name(src), self._normalise_name(dst)
            graph = self.network_graph.graph
            if not graph.has_edge(src_id, dst_id) or not graph.has_edge(dst_id, src_id):
                raise KeyError(f"Connection not found: {src}-{dst}")
            for a, b in ((src_id, dst_id), (dst_id, src_id)):
                edge = graph[a][b]
                edge["admin_active"] = is_active
                self.network_graph.update_link_metrics(
                    a, b, utilization_pct=0.0 if not is_active else edge.get("utilization_pct", 0.0),
                    is_active=is_active and edge.get("live_active", True),
                )
            self._bump()

    def _next_switch_port(self, switch: str) -> int:
        ports = [
            data.get("src_port", 0)
            for _, _, data in self.network_graph.graph.out_edges(switch, data=True)
        ]
        ports.extend(
            host.connected_port
            for host in self.hosts.values()
            if host.connected_switch == switch
        )
        return max(ports, default=0) + 1

topology_service = TopologyService()
