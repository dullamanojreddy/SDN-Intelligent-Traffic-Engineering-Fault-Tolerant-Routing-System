"""Controller failure detection, failover, recovery and resynchronisation."""
import asyncio

import pytest

from backend.services.controller_monitor import ControllerMonitor, DOWN, UNKNOWN, UP
from tests.conftest import FakeCluster, FakeController

SNAPSHOT = {"version": 1, "switches": ["s1", "s2"], "links": [
    {"src": "s1", "dst": "s2", "src_port": 1, "dst_port": 1, "capacity_mbps": 100,
     "latency_ms": 5, "loss_pct": 0, "is_active": True}], "hosts": []}


def make(cluster, names, **kw):
    events = []

    async def on_event(event):
        events.append(event)

    box = {"snap": dict(SNAPSHOT)}
    monitor = ControllerMonitor(
        endpoints=[cluster.ports[n] for n in names],
        token_provider=lambda: "test-token",
        snapshot_provider=lambda: box["snap"],
        transport=cluster.transport,
        on_event=on_event,
        **kw,
    )
    return monitor, events, box


def ticks(monitor, n):
    for _ in range(n):
        asyncio.run(monitor.check_once())


def test_first_contact_connects_and_pushes_model():
    primary = FakeController()
    monitor, events, _ = make(FakeCluster(primary=primary), ["primary"])
    assert monitor.status == UNKNOWN
    ticks(monitor, 1)
    assert monitor.status == UP and primary.syncs and events[0]["type"] == "CONTROLLER_CONNECTED"


def test_failure_needs_consecutive_missed_heartbeats():
    primary = FakeController()
    monitor, events, _ = make(FakeCluster(primary=primary), ["primary"], failure_threshold=3)
    ticks(monitor, 1)
    primary.up = False
    ticks(monitor, 2)
    assert monitor.status == UP and monitor.consecutive_failures == 2   # not yet declared
    primary.up = True
    ticks(monitor, 1)
    assert monitor.consecutive_failures == 0                             # blip forgiven
    primary.up = False
    ticks(monitor, 3)
    assert monitor.status == DOWN and monitor.outage_count == 1
    assert events[-1]["type"] == "CONTROLLER_DOWN" and events[-1]["severity"] == "CRITICAL"


def test_recovery_requires_consecutive_good_heartbeats_and_resyncs():
    primary = FakeController()
    monitor, events, box = make(FakeCluster(primary=primary), ["primary"], failure_threshold=1, recovery_threshold=3)
    ticks(monitor, 1)
    primary.up = False
    ticks(monitor, 1)
    assert monitor.status == DOWN
    box["snap"] = {**SNAPSHOT, "version": 2, "switches": ["s1", "s2", "s3"]}   # edited while down
    assert asyncio.run(monitor.sync_now()) == "PENDING_CONTROLLER_UNAVAILABLE"
    primary.up = True
    ticks(monitor, 2)
    assert monitor.status == DOWN                                        # not trusted yet
    primary.up = False
    ticks(monitor, 1)
    primary.up = True
    ticks(monitor, 2)
    assert monitor.status == DOWN                                        # flap reset the streak
    ticks(monitor, 1)
    assert monitor.status == UP and monitor.pending_sync is False
    assert primary.syncs[-1]["version"] == 2 and "s3" in primary.syncs[-1]["switches"]
    assert events[-1]["type"] == "CONTROLLER_RECOVERED" and events[-1]["data"]["outage_seconds"] is not None


def test_failover_to_standby_then_failback_to_primary():
    primary, standby = FakeController("primary"), FakeController("standby")
    monitor, events, _ = make(FakeCluster(primary=primary, standby=standby), ["primary", "standby"],
                              failure_threshold=2, recovery_threshold=2)
    ticks(monitor, 1)
    assert monitor.active_index == 0
    primary.up = False
    ticks(monitor, 2)
    assert monitor.status == UP and monitor.active_index == 1 and monitor.failover_count == 1
    assert standby.syncs and standby.syncs[-1]["version"] == 1           # standby got the model
    assert [e["type"] for e in events[-2:]] == ["CONTROLLER_DOWN", "CONTROLLER_FAILOVER"]

    primary.up = True
    ticks(monitor, 1)
    assert monitor.active_index == 1                                     # one good beat is not enough
    ticks(monitor, 1)
    assert monitor.active_index == 0 and events[-1]["type"] == "CONTROLLER_FAILBACK"
    assert primary.syncs[-1]["version"] == 1


def test_repeated_failures_are_each_detected_and_counted():
    primary = FakeController()
    monitor, events, _ = make(FakeCluster(primary=primary), ["primary"], failure_threshold=1, recovery_threshold=1)
    ticks(monitor, 1)
    for cycle in range(1, 4):
        primary.up = False
        ticks(monitor, 1)
        assert monitor.status == DOWN and monitor.outage_count == cycle
        primary.up = True
        ticks(monitor, 1)
        assert monitor.status == UP
    assert [e["type"] for e in events].count("CONTROLLER_DOWN") == 3
    assert monitor.describe()["outage_count"] == 3


def test_total_outage_with_all_standbys_down_then_one_returns():
    primary, standby = FakeController("p"), FakeController("s")
    monitor, events, _ = make(FakeCluster(primary=primary, standby=standby), ["primary", "standby"],
                              failure_threshold=1, recovery_threshold=1)
    ticks(monitor, 1)
    primary.up = standby.up = False
    ticks(monitor, 2)
    assert monitor.status == DOWN and monitor.failover_count == 0
    standby.up = True
    ticks(monitor, 1)
    assert monitor.status == UP and monitor.active_index == 1


def test_restarted_controller_with_empty_model_is_resynced():
    primary = FakeController()
    monitor, _, box = make(FakeCluster(primary=primary), ["primary"])
    ticks(monitor, 1)
    box["snap"] = {**SNAPSHOT, "version": 5}
    primary.applied_version = 0          # controller restarted between heartbeats
    primary.syncs.clear()
    ticks(monitor, 1)
    assert primary.syncs and primary.syncs[-1]["version"] == 5


def test_wrong_token_is_reported_not_treated_as_healthy():
    primary = FakeController()
    cluster = FakeCluster(primary=primary)
    monitor = ControllerMonitor([cluster.ports["primary"]], lambda: "wrong", lambda: SNAPSHOT,
                                transport=cluster.transport, failure_threshold=1)
    ticks(monitor, 2)
    assert monitor.status == DOWN and "401" in monitor.last_error


def test_rejected_or_stale_sync_is_reported():
    primary = FakeController()
    monitor, _, box = make(FakeCluster(primary=primary), ["primary"])
    ticks(monitor, 1)
    primary.reject_with = 422
    assert asyncio.run(monitor.sync_now()) == "REJECTED"
    primary.reject_with = 0
    primary.applied_version = 99
    assert asyncio.run(monitor.sync_now()) == "REJECTED"
    assert "409" in monitor.last_error


def test_describe_never_leaks_token_and_lists_endpoints():
    primary, standby = FakeController(), FakeController()
    monitor, _, _ = make(FakeCluster(primary=primary, standby=standby), ["primary", "standby"])
    ticks(monitor, 1)
    text = str(monitor.describe())
    assert "test-token" not in text
    assert [e["role"] for e in monitor.describe()["endpoints"]] == ["primary", "standby-1"]


def test_monitor_requires_an_endpoint():
    with pytest.raises(ValueError):
        ControllerMonitor([], lambda: "", lambda: {})


def test_background_loop_detects_failure_without_manual_ticks():
    async def run():
        primary = FakeController()
        monitor, events, _ = make(FakeCluster(primary=primary), ["primary"],
                                  interval=0.02, failure_threshold=2, recovery_threshold=1)
        monitor.start()
        await asyncio.sleep(0.1)
        assert monitor.status == UP
        primary.up = False
        await asyncio.sleep(0.2)
        assert monitor.status == DOWN
        primary.up = True
        await asyncio.sleep(0.2)
        assert monitor.status == UP
        await monitor.stop()
        return [e["type"] for e in events]
    assert asyncio.run(run()) == ["CONTROLLER_CONNECTED", "CONTROLLER_DOWN", "CONTROLLER_RECOVERED"]
