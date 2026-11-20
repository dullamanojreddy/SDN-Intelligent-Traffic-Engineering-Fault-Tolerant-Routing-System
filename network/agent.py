"""Network agent: lets the backend edit the *running* Mininet network.

It runs inside the Mininet process (see ``topologies/mesh.py``) and exposes a
small token-protected HTTP API (stdlib only). Every mutation is applied to the
real Mininet/OVS objects, verified (e.g. the OpenFlow port number OVS really
assigned) and rolled back if it fails, so the backend only records a topology
change after the network has actually changed.

Run under Mininet's Python; do NOT put the repo root on ``sys.path`` ahead of the
real ``mininet`` package (the repo contains an IDE stub package with that name).
"""
import hmac
import json
import os
import re
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, List, Optional, Tuple

import ovs_flows

MAC_RE = re.compile(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,14}$")   # Linux interface names are short
IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def _num(value: Any, name: str, low: float, high: float, allow_none: bool = True) -> Optional[float]:
    """Coerce a JSON value to a bounded float; values end up in shell/tc commands, so
    strings or odd types are rejected rather than formatted into them."""
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AgentError(f"{name} must be a number")
    if not (low <= float(value) <= high):
        raise AgentError(f"{name} out of range")
    return float(value)


def _valid_ip(ip: str) -> str:
    import ipaddress
    try:
        return str(ipaddress.IPv4Address(ip.split("/")[0]))
    except ValueError:
        raise AgentError("invalid ip address") from None


class AgentError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


class NetworkAgent:
    def __init__(self, net: Any, datapath: str = "kernel", protocols: str = "OpenFlow13",
                 fail_mode: str = "secure"):
        from mininet.link import TCLink
        from mininet.node import OVSSwitch
        self.net, self.TCLink, self.OVSSwitch = net, TCLink, OVSSwitch
        self.datapath, self.protocols, self.fail_mode = datapath, protocols, fail_mode
        self.lock = threading.RLock()
        self.pings: Dict[str, Dict[str, Any]] = {}
        self.traffic: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------- helpers
    def _node(self, name: str) -> Any:
        if name not in self.net.nameToNode:
            raise AgentError(f"unknown node {name}", 404)
        return self.net.nameToNode[name]

    def _is_switch(self, node: Any) -> bool:
        return node in self.net.switches

    def _links_between(self, a: Any, b: Any) -> List[Any]:
        return [l for l in self.net.links
                if {l.intf1.node, l.intf2.node} == {a, b}]

    @staticmethod
    def _port(node: Any, intf: Any) -> int:
        return node.ports[intf]

    def _sh(self, *args: str) -> str:
        return subprocess.run(args, capture_output=True, text=True, timeout=10).stdout.strip()

    def _ofport(self, switch: Any, intf: Any) -> int:
        out = self._sh("ovs-vsctl", "get", "Interface", str(intf), "ofport")
        return int(out) if out.lstrip("-").isdigit() else -1

    def _attach(self, switch: Any, intf: Any, port: int) -> None:
        """Add an interface to an OVS bridge asking for a specific OpenFlow port."""
        switch.cmd(f"ovs-vsctl add-port {switch} {intf} -- set Interface {intf} ofport_request={port}")
        switch.cmd("ifconfig", str(intf), "up")
        actual = self._ofport(switch, intf)
        if actual != port:
            switch.cmd(f"ovs-vsctl --if-exists del-port {switch} {intf}")
            raise AgentError(f"OVS assigned OpenFlow port {actual} instead of {port} on {switch}", 409)

    def _detach(self, switch: Any, intf: Any) -> None:
        switch.cmd(f"ovs-vsctl --if-exists del-port {switch} {intf}")

    def _tc(self, link: Any, bw: Optional[float], delay_ms: Optional[float], loss: Optional[float]) -> None:
        bw, delay_ms, loss = (_num(bw, "bw", 0.001, 100000), _num(delay_ms, "delay_ms", 0, 60000),
                              _num(loss, "loss", 0, 100))
        params: Dict[str, Any] = {}
        if bw is not None:
            params["bw"] = bw
        if delay_ms is not None:
            params["delay"] = f"{delay_ms}ms"
        if loss is not None:
            params["loss"] = loss
        if params:
            for intf in (link.intf1, link.intf2):
                intf.config(**params)
                intf.params.update(params)    # Mininet does not record live tc changes itself

    # ------------------------------------------------------------ topology
    def topology(self) -> Dict[str, Any]:
        with self.lock:
            switches = [{"name": s.name, "dpid": int(s.dpid, 16)} for s in self.net.switches]
            hosts, links = [], []
            for link in self.net.links:
                n1, n2 = link.intf1.node, link.intf2.node
                up = bool(link.intf1.isUp() and link.intf2.isUp())
                if self._is_switch(n1) and self._is_switch(n2):
                    links.append({"src": n1.name, "dst": n2.name,
                                  "src_port": self._port(n1, link.intf1), "dst_port": self._port(n2, link.intf2),
                                  "up": up, **self._link_params(link)})
                else:
                    host, sw, hif, sif = (n1, n2, link.intf1, link.intf2) if not self._is_switch(n1) \
                        else (n2, n1, link.intf2, link.intf1)
                    hosts.append({"name": host.name, "ip": host.IP(hif), "mac": host.MAC(hif),
                                  "switch": sw.name, "port": self._port(sw, sif), "up": up})
            return {"switches": switches, "hosts": hosts, "links": links}

    @staticmethod
    def _link_params(link: Any) -> Dict[str, Any]:
        p = getattr(link.intf1, "params", {}) or {}
        return {"bw": p.get("bw"), "delay": p.get("delay"), "loss": p.get("loss")}

    # ----------------------------------------------------------- mutations
    def add_switch(self, name: str, dpid: int) -> Dict[str, Any]:
        if not NAME_RE.match(name):
            raise AgentError("invalid switch name")
        with self.lock:
            if name in self.net.nameToNode:
                raise AgentError(f"{name} already exists", 409)
            sw = self.net.addSwitch(name, cls=self.OVSSwitch, dpid=f"{dpid:016x}",
                                    protocols=self.protocols, failMode=self.fail_mode,
                                    datapath=self.datapath)
            try:
                sw.start(self.net.controllers)
            except Exception as exc:
                self.net.switches.remove(sw)
                self.net.nameToNode.pop(name, None)
                raise AgentError(f"could not start {name}: {exc}", 500)
            return {"name": name, "dpid": dpid}

    def add_host(self, name: str, ip: str, mac: Optional[str], switch: str, port: int) -> Dict[str, Any]:
        if not NAME_RE.match(name):
            raise AgentError("invalid host name")
        ip = _valid_ip(ip)
        if mac is not None and not MAC_RE.match(mac):
            raise AgentError("invalid mac address")
        with self.lock:
            sw = self._node(switch)
            if not self._is_switch(sw):
                raise AgentError(f"{switch} is not a switch")
            if name in self.net.nameToNode:
                raise AgentError(f"{name} already exists", 409)
            host = self.net.addHost(name)
            link = None
            try:
                link = self.net.addLink(host, sw, port2=port)
                self._attach(sw, link.intf2, port)
                host.setIP(ip.split("/")[0], 24, link.intf1)
                if mac:
                    host.setMAC(mac, link.intf1)
                host.cmd("ip link set lo up")
            except Exception as exc:
                self._rollback_host(host, sw, link)
                raise exc if isinstance(exc, AgentError) else AgentError(str(exc), 500)
            return {"name": name, "ip": host.IP(link.intf1), "mac": host.MAC(link.intf1),
                    "switch": switch, "port": port}

    def _rollback_host(self, host: Any, sw: Any, link: Any) -> None:
        if link is not None:
            self._detach(sw, link.intf2)
            try:
                self.net.delLink(link)
            except Exception:
                pass
        try:
            host.stop()
        finally:
            if host in self.net.hosts:
                self.net.hosts.remove(host)
            self.net.nameToNode.pop(host.name, None)

    def add_link(self, src: str, dst: str, src_port: int, dst_port: int,
                 bw: Optional[float] = None, delay_ms: Optional[float] = None,
                 loss: Optional[float] = None) -> Dict[str, Any]:
        with self.lock:
            a, b = self._node(src), self._node(dst)
            bw, delay_ms, loss = (_num(bw, "bw", 0.001, 100000), _num(delay_ms, "delay_ms", 0, 60000),
                                  _num(loss, "loss", 0, 100))
            if not (self._is_switch(a) and self._is_switch(b)):
                raise AgentError("links must connect two switches")
            if self._links_between(a, b):
                raise AgentError(f"link {src}-{dst} already exists", 409)
            link = self.net.addLink(a, b, port1=src_port, port2=dst_port, cls=self.TCLink,
                                    bw=bw, delay=f"{delay_ms}ms" if delay_ms is not None else None, loss=loss)
            attached: List[Tuple[Any, Any]] = []
            try:
                self._attach(a, link.intf1, src_port); attached.append((a, link.intf1))
                self._attach(b, link.intf2, dst_port); attached.append((b, link.intf2))
            except Exception as exc:
                for node, intf in attached:
                    self._detach(node, intf)
                try:
                    self.net.delLink(link)
                except Exception:
                    pass
                raise exc if isinstance(exc, AgentError) else AgentError(str(exc), 500)
            return {"src": src, "dst": dst, "src_port": src_port, "dst_port": dst_port}

    def delete_link(self, src: str, dst: str) -> Dict[str, Any]:
        with self.lock:
            a, b = self._node(src), self._node(dst)
            links = self._links_between(a, b)
            if not links:
                raise AgentError(f"link {src}-{dst} not found", 404)
            for link in links:
                for node, intf in ((link.intf1.node, link.intf1), (link.intf2.node, link.intf2)):
                    if self._is_switch(node):
                        self._detach(node, intf)
                self.net.delLink(link)
            return {"src": src, "dst": dst}

    def delete_host(self, name: str) -> Dict[str, Any]:
        with self.lock:
            host = self._node(name)
            if host not in self.net.hosts:
                raise AgentError(f"{name} is not a host", 404)
            for link in [l for l in self.net.links if host in (l.intf1.node, l.intf2.node)]:
                for node, intf in ((link.intf1.node, link.intf1), (link.intf2.node, link.intf2)):
                    if self._is_switch(node):
                        self._detach(node, intf)
                self.net.delLink(link)
            host.stop()
            self.net.hosts.remove(host)
            self.net.nameToNode.pop(name, None)
            return {"name": name}

    def delete_switch(self, name: str) -> Dict[str, Any]:
        with self.lock:
            sw = self._node(name)
            if not self._is_switch(sw):
                raise AgentError(f"{name} is not a switch", 404)
            removed_hosts = []
            for link in [l for l in self.net.links if sw in (l.intf1.node, l.intf2.node)]:
                other = link.intf2.node if link.intf1.node is sw else link.intf1.node
                if other in self.net.hosts:
                    removed_hosts.append(other.name)
                if self._is_switch(other):
                    self.delete_link(sw.name, other.name)
            for host_name in removed_hosts:
                self.delete_host(host_name)
            sw.stop(deleteIntfs=True)
            self.net.switches.remove(sw)
            self.net.nameToNode.pop(name, None)
            return {"name": name, "removed_hosts": removed_hosts}

    def update_link(self, src: str, dst: str, bw: Optional[float], delay_ms: Optional[float],
                    loss: Optional[float]) -> Dict[str, Any]:
        with self.lock:
            links = self._links_between(self._node(src), self._node(dst))
            if not links:
                raise AgentError(f"link {src}-{dst} not found", 404)
            self._tc(links[0], bw, delay_ms, loss)
            return {"src": src, "dst": dst}

    def set_link_state(self, src: str, dst: str, up: bool) -> Dict[str, Any]:
        with self.lock:
            links = self._links_between(self._node(src), self._node(dst))
            if not links:
                raise AgentError(f"link {src}-{dst} not found", 404)
            for intf in (links[0].intf1, links[0].intf2):
                intf.node.cmd("ip", "link", "set", str(intf), "up" if up else "down")
            return {"src": src, "dst": dst, "up": up}

    # ------------------------------------------------------- observability
    def flows(self) -> Dict[str, List[Dict[str, Any]]]:
        with self.lock:
            names = [s.name for s in self.net.switches]
        result = {}
        for name in names:
            try:
                result[name] = ovs_flows.dump_flows(name)
            except (subprocess.SubprocessError, OSError) as exc:
                result[name] = [{"error": str(exc)}]
        return result

    def switch_roles(self) -> Dict[str, Any]:
        """OVS's view of each controller connection (target, role, connected)."""
        controllers = json.loads(self._sh("ovs-vsctl", "-f", "json", "list", "Controller") or '{"data":[],"headings":[]}')
        heads = controllers["headings"]
        rows = {r[heads.index("_uuid")][1]: dict(zip(heads, r)) for r in controllers["data"]}
        bridges = json.loads(self._sh("ovs-vsctl", "-f", "json", "list", "Bridge") or '{"data":[],"headings":[]}')
        bh = bridges["headings"]
        out: Dict[str, Any] = {}
        for row in bridges["data"]:
            record = dict(zip(bh, row))
            ctrl = record.get("controller")
            uuids = [ctrl[1]] if ctrl and ctrl[0] == "uuid" else \
                [u[1] for u in (ctrl[1] if ctrl else [])]
            out[record["name"]] = [
                {"target": rows[u]["target"], "role": rows[u].get("role") if isinstance(rows[u].get("role"), str) and rows[u].get("role") else "other",
                 "connected": bool(rows[u].get("is_connected"))} for u in uuids if u in rows]
        return out

    def traffic_start(self, src: str, dst: str, rate_mbps: float, duration_sec: int, protocol: str) -> Dict[str, Any]:
        """Generate real iperf3 traffic between two Mininet hosts."""
        rate_mbps = _num(rate_mbps, "rate_mbps", 0.001, 10000, allow_none=False)
        duration_sec = int(_num(duration_sec, "duration_sec", 1, 3600, allow_none=False))
        if protocol.upper() not in ("TCP", "UDP"):
            raise AgentError("invalid traffic parameters")
        with self.lock:
            client, server = self._node(src), self._node(dst)
            if client not in self.net.hosts or server not in self.net.hosts:
                raise AgentError("traffic endpoints must be hosts")
            traffic_id = f"t{int(time.time() * 1000)}"
            log = f"/var/tmp/sdnite_{traffic_id}.log"
            server.cmd(f"iperf3 -s -1 -D -p 5201 --logfile /var/tmp/sdnite_{traffic_id}_srv.log")
            time.sleep(0.3)
            udp = "-u" if protocol.upper() == "UDP" else ""
            pid = client.cmd(f"iperf3 -c {server.IP()} -p 5201 -t {int(duration_sec)} -b {rate_mbps}M {udp} "
                             f"> {log} 2>&1 & echo $!").strip().splitlines()[-1]
            self.traffic[traffic_id] = {"client": src, "pid": pid, "log": log, "dst": dst}
            return {"id": traffic_id, "src": src, "dst": dst, "rate_mbps": rate_mbps, "duration_sec": duration_sec}

    def traffic_stop(self, traffic_id: Optional[str] = None) -> Dict[str, Any]:
        """Stop one (or all) traffic generators; report what iperf3 measured."""
        with self.lock:
            ids = [traffic_id] if traffic_id else list(self.traffic)
            stopped = []
            for tid in ids:
                info = self.traffic.pop(tid, None)
                if not info:
                    raise AgentError("unknown traffic id", 404)
                self._node(info["client"]).cmd(f"kill -INT {info['pid']} 2>/dev/null; sleep 0.2")
                try:
                    tail = open(info["log"]).read()[-300:]
                except OSError:
                    tail = ""
                stopped.append({"id": tid, "output_tail": tail})
            for host in self.net.hosts:
                host.cmd("pkill iperf3 2>/dev/null")
            return {"stopped": stopped}

    def ping(self, src: str, dst_ip: str, count: int = 3, timeout: int = 2) -> Dict[str, Any]:
        dst_ip = _valid_ip(dst_ip)
        host = self._node(src)
        out = host.cmd(f"ping -c {max(1, min(int(count), 100))} -W {max(1, min(int(timeout), 10))} {dst_ip}")
        m = re.search(r"(\d+) packets transmitted, (\d+) (?:packets )?received", out)
        sent, got = (int(m.group(1)), int(m.group(2))) if m else (int(count), 0)
        return {"src": src, "dst": dst_ip, "sent": sent, "received": got, "ok": got > 0, "output": out[-400:]}

    def ping_start(self, src: str, dst_ip: str, interval: float = 0.2) -> Dict[str, Any]:
        dst_ip = _valid_ip(dst_ip)
        interval = _num(interval, "interval", 0.01, 5, allow_none=False)
        host = self._node(src)
        pid_id = f"p{int(time.time() * 1000)}"
        log = f"/var/tmp/sdnite_{pid_id}.log"
        pid = host.cmd(f"ping -i {float(interval)} -D {dst_ip} > {log} 2>&1 & echo $!").strip().splitlines()[-1]
        self.pings[pid_id] = {"host": src, "pid": pid, "log": log, "dst": dst_ip}
        return {"id": pid_id}

    def ping_stop(self, ping_id: str) -> Dict[str, Any]:
        info = self.pings.pop(ping_id, None)
        if not info:
            raise AgentError("unknown ping id", 404)
        host = self._node(info["host"])
        host.cmd(f"kill -INT {info['pid']}; sleep 0.3")
        text = open(info["log"]).read()
        seqs = sorted(int(s) for s in re.findall(r"icmp_seq=(\d+)", text))
        m = re.search(r"(\d+) packets transmitted, (\d+) (?:packets )?received", text)
        sent = int(m.group(1)) if m else (seqs[-1] if seqs else 0)
        got = int(m.group(2)) if m else len(seqs)
        gap = max((b - a for a, b in zip(seqs, seqs[1:])), default=1) - 1
        return {"sent": sent, "received": got, "lost": sent - got, "max_consecutive_gap": gap}


class _Handler(BaseHTTPRequestHandler):
    agent: NetworkAgent
    token: str

    def log_message(self, *args: Any) -> None:  # keep Mininet CLI output clean
        pass

    def _send(self, status: int, payload: Any) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _route(self, method: str) -> None:
        if not hmac.compare_digest(self.headers.get("Authorization", ""), f"Bearer {self.token}"):
            return self._send(401, {"detail": "Unauthorized"})
        parts = [p for p in self.path.split("?")[0].split("/") if p]
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}") if length else {}
            self._send(200, self._dispatch(method, parts, body))
        except AgentError as exc:
            self._send(exc.status, {"detail": str(exc)})
        except (KeyError, TypeError, ValueError) as exc:
            self._send(400, {"detail": f"bad request: {exc}"})
        except Exception as exc:
            self._send(500, {"detail": f"{exc.__class__.__name__}: {exc}"})

    def _dispatch(self, method: str, parts: List[str], b: Dict[str, Any]) -> Any:
        a = self.agent
        key = (method, parts[0] if parts else "")
        if key == ("GET", "health"):
            return {"status": "ok"}
        if key == ("GET", "topology"):
            return a.topology()
        if key == ("GET", "flows"):
            return {"flows": a.flows()}
        if key == ("GET", "switch-roles"):
            return a.switch_roles()
        if key == ("POST", "switches"):
            return a.add_switch(b["name"], int(b["dpid"]))
        if key == ("DELETE", "switches"):
            return a.delete_switch(parts[1])
        if key == ("POST", "hosts"):
            return a.add_host(b["name"], b["ip"], b.get("mac"), b["switch"], int(b["port"]))
        if key == ("DELETE", "hosts"):
            return a.delete_host(parts[1])
        if key == ("POST", "links"):
            return a.add_link(b["src"], b["dst"], int(b["src_port"]), int(b["dst_port"]),
                              b.get("bw"), b.get("delay_ms"), b.get("loss"))
        if key == ("DELETE", "links"):
            return a.delete_link(parts[1], parts[2])
        if key == ("PATCH", "links"):
            return a.update_link(parts[1], parts[2], b.get("bw"), b.get("delay_ms"), b.get("loss"))
        if key == ("POST", "link-state"):
            return a.set_link_state(b["src"], b["dst"], bool(b["up"]))
        if key == ("POST", "ping"):
            return a.ping(b["src"], b["dst_ip"], int(b.get("count", 3)))
        if key == ("POST", "traffic-start"):
            return a.traffic_start(b["src"], b["dst"], float(b["rate_mbps"]), int(b["duration_sec"]), b.get("protocol", "TCP"))
        if key == ("POST", "traffic-stop"):
            return a.traffic_stop(b.get("id"))
        if key == ("POST", "ping-start"):
            return a.ping_start(b["src"], b["dst_ip"], float(b.get("interval", 0.2)))
        if key == ("POST", "ping-stop"):
            return a.ping_stop(b["id"])
        raise AgentError("not found", 404)

    def do_GET(self): self._route("GET")
    def do_POST(self): self._route("POST")
    def do_DELETE(self): self._route("DELETE")
    def do_PATCH(self): self._route("PATCH")


def serve(agent: NetworkAgent, host: str, port: int, token: str) -> ThreadingHTTPServer:
    """Start the agent API in a daemon thread and return the server."""
    if not token:
        raise RuntimeError("NETWORK_AGENT_TOKEN (or CONTROLLER_API_TOKEN) must be set")
    handler = type("AgentHandler", (_Handler,), {"agent": agent, "token": token})
    server = ThreadingHTTPServer((host, port), handler)
    threading.Thread(target=server.serve_forever, daemon=True, name="network-agent").start()
    return server
