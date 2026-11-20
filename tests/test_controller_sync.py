"""Controller-side topology sync, flow-cache fixes, switch liveness, and a real
backend <-> controller failure/recovery round trip over TCP."""
import asyncio
import json
import struct

import httpx
import pytest

from backend.services.controller_monitor import ControllerMonitor, DOWN, UP
from backend.services.topology_service import TopologyService
from controller.app import SDNTrafficEngineApp
from controller.management_api import ControllerManagementAPI
from controller.openflow.protocol import (
    OFP_VERSION, OFPT_ECHO_REQUEST, OFPT_ECHO_REPLY, OFPT_ERROR, OFPT_FEATURES_REPLY,
    OFPT_FLOW_MOD, build_hello, parse_header,
)
from controller.openflow.switch_manager import SwitchManager
from controller.topology.sync import SnapshotError, validate_snapshot
from tests.conftest import free_port

TOKEN = "integration-token"


class MockDatapath:
    def __init__(self, sw_id):
        self.sw_id, self.dpid, self.messages = sw_id, int(sw_id[1:]), []

    async def send_msg(self, message):
        self.messages.append(message)
        return True


def new_app():
    app = SDNTrafficEngineApp()
    app.initialize_mesh_topology()
    for n in range(1, 8):
        app.switch_manager.datapaths[n] = MockDatapath(f"s{n}")
    return app


async def start_api(app, port):
    app.management_api = ControllerManagementAPI(app, "127.0.0.1", port, TOKEN)
    await app.management_api.start()


async def call(port, method, path, body=None, token=TOKEN):
    async with httpx.AsyncClient(timeout=3) as client:
        return await client.request(method, f"http://127.0.0.1:{port}{path}", json=body,
                                    headers={"Authorization": f"Bearer {token}"})


def snapshot_from(service):
    return service.snapshot()


# ----------------------------------------------------------- snapshot rules
def test_snapshot_validation_rejects_inconsistent_models():
    ok = TopologyService().snapshot()
    validate_snapshot(ok)
    bad_cases = [
        {**ok, "version": -1},
        {**ok, "switches": ["s1", "s1"]},
        {**ok, "links": [{**ok["links"][0], "dst": "nope"}]},
        {**ok, "links": [{**ok["links"][0], "dst": ok["links"][0]["src"]}]},
        {**ok, "links": [ok["links"][0], ok["links"][0]]},
        {**ok, "links": [{**ok["links"][0], "capacity_mbps": 0}]},
        {**ok, "links": [{**ok["links"][0], "latency_ms": float("nan")}]},
        {**ok, "links": [{**ok["links"][0], "loss_pct": 101}]},
        {**ok, "hosts": [{"ip": "x", "mac": "m", "switch": "s1", "port": 3}]},
        {**ok, "hosts": [{"ip": "10.0.0.1", "mac": "m", "switch": "zz", "port": 3}]},
    ]
    for case in bad_cases:
        with pytest.raises(SnapshotError):
            validate_snapshot(case)


def test_apply_snapshot_edits_graph_routes_and_removes_stale_rules():
    async def run():
        app = new_app()
        await app._recover_host_routes("baseline")
        baseline_flows = set(app.flow_manager.active_flows)
        assert any(k.startswith("s2_") for k in baseline_flows)

        service = TopologyService()
        service.remove_switch("s2")                       # the user deletes s2
        service.update_connection("s1", "s3", latency_ms=33)
        summary = await app.apply_topology_snapshot(snapshot_from(service))

        assert summary["removed_switches"] == ["s2"]
        assert not app.network_graph.graph.has_node("s2")
        assert app.network_graph.graph["s1"]["s3"]["latency_ms"] == 33
        assert app.topology_version == service.version
        assert not any(k.startswith("s2_") for k in app.flow_manager.active_flows)
        # rules on s2 were deleted from the switch, not only forgotten
        deletes = [m for m in app.switch_manager.datapaths[2].messages
                   if parse_header(m[:8]).msg_type == OFPT_FLOW_MOD and m[25] in (3, 4)]
        assert deletes
        # surviving host pairs still have a path via s3
        assert app.router.calculate_shortest_path("s1", "s7")[0][1] == "s3"
    asyncio.run(run())


def test_snapshot_applies_admin_down_and_respects_physical_port_down():
    async def run():
        app = new_app()
        service = TopologyService()
        service.set_link_state("s1", "s2", False)
        await app.apply_topology_snapshot(snapshot_from(service))
        assert app.network_graph.graph["s1"]["s2"]["is_active"] is False
        assert app.router.calculate_shortest_path("s1", "s7")[0][1] == "s3"

        app.port_down_links.add("s1-s3")                  # physical failure observed
        service.set_link_state("s1", "s2", True)
        await app.apply_topology_snapshot(snapshot_from(service))
        assert app.network_graph.graph["s1"]["s2"]["is_active"] is True
        assert app.network_graph.graph["s1"]["s3"]["is_active"] is False   # model cannot revive it
    asyncio.run(run())


def test_hosts_in_snapshot_become_routable_endpoints():
    async def run():
        app = new_app()
        service = TopologyService()
        service.add_host("h9", "10.0.0.9", "s4")
        await app.apply_topology_snapshot(snapshot_from(service))
        assert app.packet_handler.host_ip_table["10.0.0.9"][0] == "s4"
        assert any("10.0.0.9" in k for k in app.flow_manager.active_flows)
    asyncio.run(run())


# ------------------------------------------------------------ management API
def test_management_api_auth_state_sync_and_stale_version():
    async def run():
        app, port = new_app(), free_port()
        await start_api(app, port)
        try:
            assert (await call(port, "GET", "/health", token="wrong")).status_code == 401
            assert (await call(port, "GET", "/health")).json()["status"] == "ok"
            state = (await call(port, "GET", "/state")).json()
            assert len(state["switches"]) == 7 and all(s["connected"] for s in state["switches"])
            assert len(state["links"]) == 18 and state["topology_version"] == 0

            service = TopologyService()
            service.add_switch("s8")
            ok = await call(port, "POST", "/topology/sync", service.snapshot())
            assert ok.status_code == 200 and ok.json()["added_switches"] == ["s8"]
            assert (await call(port, "GET", "/state")).json()["topology_version"] == service.version

            stale = {**service.snapshot(), "version": service.version - 1}
            assert (await call(port, "POST", "/topology/sync", stale)).status_code == 409
            bad = {**service.snapshot(), "links": [{"src": "s1", "dst": "zz"}]}
            assert (await call(port, "POST", "/topology/sync", bad)).status_code == 422
            assert (await call(port, "POST", "/topology/sync", [1, 2])).status_code == 422
            flows = (await call(port, "GET", "/flows")).json()["flows"]
            assert flows and {"flow_id", "switch", "out_port"} <= set(flows[0])
            assert (await call(port, "GET", "/nope")).status_code == 404
        finally:
            await app.management_api.stop()
    asyncio.run(run())


def test_route_install_now_succeeds_with_cookie():
    async def run():
        app, port = new_app(), free_port()
        await start_api(app, port)
        try:
            body = {"installation_id": "install-12345678", "source_ip": "10.0.0.1",
                    "dest_ip": "10.0.0.8", "path": ["s1", "s2", "s5", "s7"], "cookie": 7}
            result = (await call(port, "POST", "/routes/install", body)).json()
            assert result["status"] == "INSTALLED", result
        finally:
            await app.management_api.stop()
    asyncio.run(run())


# --------------------------------------------------------- flow cache / OVS
def test_expired_cached_rule_is_re_added_not_modified():
    from controller.openflow.flow_manager import FlowManager
    from controller.openflow.protocol import ETH_TYPE_IP, OFPFC_ADD

    async def run():
        manager = FlowManager(type("SM", (), {})())
        dp = MockDatapath("s1")
        match = {"eth_type": ETH_TYPE_IP, "ipv4_dst": "10.0.0.7"}
        await manager.install_flow(dp, match, out_port=1, idle_timeout=300)
        manager.active_flows["s1_2048_10.0.0.7_100"]["installed_at"] -= 301   # idled out on the switch
        await manager.install_flow(dp, match, out_port=1, idle_timeout=300)
        assert dp.messages[1][25] == OFPFC_ADD
        manager.forget_switch("s1")
        assert manager.active_flows == {}
    asyncio.run(run())


def test_switch_reconnect_clears_stale_flow_cache():
    app = new_app()
    asyncio.run(app._recover_host_routes("x"))
    assert any(k.startswith("s1_") for k in app.flow_manager.active_flows)
    app._on_switch_disconnected(app.switch_manager.datapaths[1])
    assert not any(k.startswith("s1_") for k in app.flow_manager.active_flows)
    assert any(k.startswith("s7_") for k in app.flow_manager.active_flows)   # others untouched


async def handshake(port, dpid):
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    await reader.readexactly(8)                       # controller HELLO
    writer.write(build_hello())
    feat_req = parse_header(await reader.readexactly(8))
    body = struct.pack("!QIBB2sI", dpid, 256, 254, 0, b"\0\0", 0x4f)
    writer.write(struct.pack("!BBHI", OFP_VERSION, OFPT_FEATURES_REPLY, 8 + len(body), feat_req.xid) + body)
    await writer.drain()
    await reader.readexactly(12)                      # SET_CONFIG
    miss = parse_header(await reader.readexactly(8))   # table-miss FLOW_MOD
    await reader.readexactly(miss.length - 8)
    return reader, writer


def test_switch_error_message_no_longer_drops_the_session():
    async def run():
        port = free_port()
        manager = SwitchManager()
        await manager.start_server("127.0.0.1", port)
        try:
            reader, writer = await handshake(port, 1)
            await asyncio.sleep(0.05)
            err = struct.pack("!HH", 1, 1) + b"x" * 8
            writer.write(struct.pack("!BBHI", OFP_VERSION, OFPT_ERROR, 8 + len(err), 9) + err)
            writer.write(struct.pack("!BBHI", OFP_VERSION, 21, 8, 10))   # BARRIER_REPLY (unhandled type)
            await writer.drain()
            await asyncio.sleep(0.1)
            assert 1 in manager.datapaths and manager.datapaths[1].is_active
            writer.close()
        finally:
            await manager.stop_server()
    asyncio.run(run())


def test_silent_switch_is_declared_dead_and_removed():
    async def run():
        port = free_port()
        seen = {}
        manager = SwitchManager(keepalive_interval=0.05, keepalive_timeout=0.2,
                                on_switch_disconnected=lambda dp: seen.setdefault("dp", dp.sw_id))
        await manager.start_server("127.0.0.1", port)
        try:
            reader, writer = await handshake(port, 4)
            assert 4 in manager.datapaths
            # Switch answers echoes for a while, then goes silent (half-open TCP).
            echo = parse_header(await reader.readexactly(8))
            assert echo.msg_type == OFPT_ECHO_REQUEST
            writer.write(struct.pack("!BBHI", OFP_VERSION, OFPT_ECHO_REPLY, 8, echo.xid))
            await asyncio.sleep(0.6)
            assert 4 not in manager.datapaths and seen.get("dp") == "s4"
            writer.close()
        finally:
            await manager.stop_server()
    asyncio.run(run())


# ----------------------------------------- real backend <-> controller outage
def test_real_controller_crash_failover_and_resync_round_trip():
    async def run():
        service = TopologyService()
        events = []

        async def on_event(e):
            events.append(e["type"])

        primary_port, standby_port = free_port(), free_port()
        primary, standby = new_app(), new_app()
        await start_api(primary, primary_port)
        await start_api(standby, standby_port)
        monitor = ControllerMonitor(
            [f"http://127.0.0.1:{primary_port}", f"http://127.0.0.1:{standby_port}"],
            lambda: TOKEN, service.snapshot, timeout=0.5, failure_threshold=2,
            recovery_threshold=2, on_event=on_event)
        try:
            await monitor.check_once()
            assert monitor.status == UP and primary.topology_version == service.version

            service.add_switch("s8"); service.add_connection("s7", "s8", 200, 2)
            assert await monitor.sync_now() == "SYNCED"
            assert primary.network_graph.graph.has_edge("s7", "s8")

            # --- crash the primary (management API dies like a killed process)
            await primary.management_api.stop()
            await monitor.check_once()
            assert monitor.status == UP                    # one miss only
            await monitor.check_once()
            assert monitor.status == UP and monitor.active_index == 1
            assert events[-2:] == ["CONTROLLER_DOWN", "CONTROLLER_FAILOVER"]
            assert standby.network_graph.graph.has_edge("s7", "s8")   # standby has the live model

            # user edits while running on the standby
            service.update_connection("s7", "s8", latency_ms=44)
            assert await monitor.sync_now() == "SYNCED"
            assert standby.network_graph.graph["s7"]["s8"]["latency_ms"] == 44

            # --- primary restarts with an empty model and is resynced on fail-back
            primary = new_app()
            await start_api(primary, primary_port)
            await monitor.check_once()
            assert monitor.active_index == 1
            await monitor.check_once()
            assert monitor.active_index == 0 and events[-1] == "CONTROLLER_FAILBACK"
            assert primary.topology_version == service.version
            assert primary.network_graph.graph["s7"]["s8"]["latency_ms"] == 44
            assert any(primary.switch_manager.datapaths[n].messages for n in (1, 7))
        finally:
            await monitor.stop()
            for app in (primary, standby):
                await app.management_api.stop()
    asyncio.run(run())


def test_edit_while_all_controllers_down_is_applied_after_recovery():
    async def run():
        service = TopologyService()
        port = free_port()
        app = new_app()
        await start_api(app, port)
        monitor = ControllerMonitor([f"http://127.0.0.1:{port}"], lambda: TOKEN, service.snapshot,
                                    timeout=0.5, failure_threshold=1, recovery_threshold=1)
        try:
            await monitor.check_once()
            await app.management_api.stop()
            await monitor.check_once()
            assert monitor.status == DOWN
            service.remove_connection("s1", "s2")                     # edit during outage
            assert await monitor.sync_now() == "PENDING_CONTROLLER_UNAVAILABLE"
            app2 = new_app()
            await start_api(app2, port)
            await monitor.check_once()
            assert monitor.status == UP and not monitor.pending_sync
            assert not app2.network_graph.graph.has_edge("s1", "s2")
            assert app2.router.calculate_shortest_path("s1", "s7")[0][1] == "s3"
            await app2.management_api.stop()
        finally:
            await monitor.stop()
    asyncio.run(run())


def test_overlapping_reconciles_never_delete_each_others_rules():
    """Regression from the real-OVS run: a port-down reconcile and a snapshot
    reconcile overlapped and the slower one's stale cleanup removed fresh rules."""
    class SlowDP(MockDatapath):
        async def send_msg(self, message):
            await asyncio.sleep(0)             # yield so reconciles interleave
            return await super().send_msg(message)

    async def run():
        app = SDNTrafficEngineApp()
        app.initialize_mesh_topology()
        for n in range(1, 8):
            app.switch_manager.datapaths[n] = SlowDP(f"s{n}")
        await app._recover_host_routes("baseline")
        app.network_graph.update_link_metrics("s1", "s3", utilization_pct=0.0, is_active=False)
        app.network_graph.update_link_metrics("s3", "s1", utilization_pct=0.0, is_active=False)
        await asyncio.gather(app._recover_host_routes("a"), app._recover_host_routes("b"),
                             app._recover_host_routes("c"))
        path, _ = app.router.calculate_shortest_path("s1", "s7")
        for sw in path:
            assert f"{sw}_2048_10.0.0.8_100" in app.flow_manager.active_flows, sw
        assert not any(k.startswith("s3_2048_10.0.0.8") for k in app.flow_manager.active_flows if "s3" not in path)
    asyncio.run(run())


def test_reconcile_re_adds_rules_that_vanished_from_the_switch():
    """OVS ignores MODIFY for a missing rule, so re-asserting state must use ADD."""
    from controller.openflow.protocol import OFPFC_ADD

    async def run():
        app = new_app()
        await app._recover_host_routes("first")
        for dp in app.switch_manager.datapaths.values():
            dp.messages.clear()                 # pretend OVS lost its rules behind our back
        await app._recover_host_routes("second")
        commands = {m[25] for dp in app.switch_manager.datapaths.values() for m in dp.messages
                    if parse_header(m[:8]).msg_type == OFPT_FLOW_MOD}
        assert commands == {OFPFC_ADD}
        app.switch_manager.datapaths[1].messages.clear()
        await app.packet_handler.install_proactive_mesh_routes()
        assert {m[25] for m in app.switch_manager.datapaths[1].messages
                if parse_header(m[:8]).msg_type == OFPT_FLOW_MOD} == {OFPFC_ADD}
    asyncio.run(run())
