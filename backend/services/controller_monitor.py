"""Controller liveness monitoring, failover between controller endpoints and
topology resynchronisation.

The monitor heartbeats the active controller's management API. After
``failure_threshold`` consecutive failed heartbeats the controller is declared
DOWN and the monitor immediately tries the configured standby endpoints. A
healthy endpoint is only trusted again after ``recovery_threshold`` consecutive
good heartbeats (no flapping), the primary is preferred again once it has
recovered, and every transition to a healthy controller pushes the backend's
current topology snapshot so the controller never runs on a stale model.
"""
import asyncio
import logging
import time
from collections import deque
from typing import Any, Awaitable, Callable, Deque, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger("backend.controller_monitor")

UP, DOWN, UNKNOWN = "UP", "DOWN", "UNKNOWN"
EventCallback = Callable[[Dict[str, Any]], Awaitable[None]]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class ControllerMonitor:
    def __init__(
        self,
        endpoints: List[str],
        token_provider: Callable[[], str],
        snapshot_provider: Callable[[], Dict[str, Any]],
        interval: float = 2.0,
        timeout: float = 1.5,
        failure_threshold: int = 3,
        recovery_threshold: int = 2,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        on_event: Optional[EventCallback] = None,
        on_state: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        on_version_conflict: Optional[Callable[[int], None]] = None,
    ):
        if not endpoints:
            raise ValueError("at least one controller endpoint is required")
        self.endpoints = [e.rstrip("/") for e in endpoints]
        self.token_provider = token_provider
        self.snapshot_provider = snapshot_provider
        self.interval = interval
        self.timeout = timeout
        self.failure_threshold = failure_threshold
        self.recovery_threshold = recovery_threshold
        self.transport = transport
        self.on_event = on_event
        self.on_state = on_state
        self.on_version_conflict = on_version_conflict

        self.status = UNKNOWN
        self.active_index = 0
        self.consecutive_failures = 0
        self.last_error: Optional[str] = None
        self.last_heartbeat: Optional[str] = None
        self.last_change: Optional[str] = None
        self.failover_count = 0
        self.outage_count = 0
        self.down_since: Optional[float] = None
        self.pending_sync = False
        self.synced_version: Optional[int] = None
        self.state: Optional[Dict[str, Any]] = None
        self.history: Deque[Dict[str, Any]] = deque(maxlen=100)
        self.endpoint_health: Dict[str, Dict[str, Any]] = {
            e: {"healthy": None, "last_probe": None, "error": None} for e in self.endpoints
        }
        self._recovery_candidate: Optional[int] = None
        self._recovery_successes = 0
        self._primary_successes = 0
        self._lock = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------ http
    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=httpx.Timeout(self.timeout), transport=self.transport)

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token_provider()}"}

    @property
    def active_url(self) -> str:
        return self.endpoints[self.active_index]

    def role_of(self, index: int) -> str:
        return "primary" if index == 0 else f"standby-{index}"

    async def _request(self, method: str, url: str, path: str, **kw) -> httpx.Response:
        async with self._client() as client:
            return await client.request(method, f"{url}{path}", headers=self._headers(), **kw)

    async def probe(self, index: int) -> Tuple[bool, Optional[str]]:
        """One heartbeat to endpoint ``index``. Returns (healthy, error)."""
        url = self.endpoints[index]
        try:
            response = await self._request("GET", url, "/health")
            if response.status_code == 401:
                error = "401 Unauthorized (CONTROLLER_API_TOKEN mismatch)"
            elif response.status_code != 200:
                error = f"HTTP {response.status_code}"
            elif response.json().get("status") != "ok":
                error = "controller reported unhealthy"
            else:
                error = None
        except (httpx.HTTPError, ValueError) as exc:
            error = f"{exc.__class__.__name__}: {exc}" if str(exc) else exc.__class__.__name__
        health = self.endpoint_health[url]
        health.update(healthy=error is None, last_probe=_now(), error=error)
        return error is None, error

    async def fetch_state(self) -> Optional[Dict[str, Any]]:
        try:
            response = await self._request("GET", self.active_url, "/state")
            if response.status_code == 200:
                return response.json()
        except (httpx.HTTPError, ValueError):
            pass
        return None

    # ---------------------------------------------------------------- events
    async def _emit(self, type_: str, severity: str, message: str, **data: Any) -> None:
        event = {
            "type": type_, "severity": severity, "message": message,
            "timestamp": _now(), "data": {"active_url": self.active_url, **data},
        }
        self.history.append(event)
        log = logger.error if severity in ("ERROR", "CRITICAL") else logger.info
        log("%s: %s", type_, message)
        if self.on_event:
            try:
                await self.on_event(event)
            except Exception:  # persistence/broadcast problems must not stop monitoring
                logger.exception("controller event handler failed")

    # ------------------------------------------------------------------ sync
    async def sync_now(self) -> str:
        """Push the current topology snapshot to the active controller.

        Returns SYNCED, PENDING_CONTROLLER_UNAVAILABLE or REJECTED. A change made
        while the controller is unavailable is never lost: it stays pending and is
        pushed as part of the recovery sequence.
        """
        if self.status != UP:
            self.pending_sync = True
            return "PENDING_CONTROLLER_UNAVAILABLE"
        snapshot = self.snapshot_provider()
        try:
            response = await self._request("POST", self.active_url, "/topology/sync", json=snapshot)
        except httpx.HTTPError as exc:
            self.pending_sync = True
            self.last_error = f"sync failed: {exc.__class__.__name__}"
            return "PENDING_CONTROLLER_UNAVAILABLE"
        if response.status_code == 200:
            self.pending_sync = False
            self.synced_version = snapshot["version"]
            await self._warm_standbys(snapshot)
            return "SYNCED"
        detail = response.text
        self.last_error = f"sync rejected ({response.status_code}): {detail}"
        logger.error(self.last_error)
        if response.status_code == 409 and self.on_version_conflict:
            # The controller holds a newer topology version than this backend (backend
            # restarted on a host with an earlier clock, or another writer exists).
            # Jump above it and retry once instead of staying rejected forever.
            try:
                self.on_version_conflict(int(response.json()["applied_version"]))
                retry = self.snapshot_provider()
                again = await self._request("POST", self.active_url, "/topology/sync", json=retry)
                if again.status_code == 200:
                    self.pending_sync = False
                    self.synced_version = retry["version"]
                    self.last_error = None
                    await self._warm_standbys(retry)
                    return "SYNCED"
            except (httpx.HTTPError, KeyError, ValueError):
                pass
        self.pending_sync = False
        return "REJECTED"

    async def _warm_standbys(self, snapshot: Dict[str, Any]) -> None:
        """Best-effort push of the model to non-active, healthy controllers so a
        standby can take over with a current topology even if the backend is gone."""
        for index, url in enumerate(self.endpoints):
            if index == self.active_index or not self.endpoint_health[url].get("healthy"):
                continue
            try:
                await self._request("POST", url, "/topology/sync", json=snapshot)
            except httpx.HTTPError:
                pass

    async def assign_roles(self, active_index: int) -> Dict[str, str]:
        """Make ``active_index`` the OpenFlow MASTER and every other reachable
        controller a SLAVE. The switches arbitrate by generation id, so a stale or
        duplicate assignment cannot leave two controllers programming one switch."""
        results: Dict[str, str] = {}
        if len(self.endpoints) < 2:
            return results
        order = [active_index] + [i for i in range(len(self.endpoints)) if i != active_index]
        for index in order:
            role = "MASTER" if index == active_index else "SLAVE"
            url = self.endpoints[index]
            try:
                response = await self._request("POST", url, "/role", json={"role": role, "reason": "backend arbitration"})
                results[url] = f"{role}:{response.status_code}"
            except httpx.HTTPError as exc:
                results[url] = f"{role}:unreachable"
        return results

    # ------------------------------------------------------------ transitions
    async def _become_up(self, index: int, kind: str, error_free_detail: str) -> None:
        previous_down_since = self.down_since
        self.active_index = index
        self.status = UP
        self.consecutive_failures = 0
        self.last_error = None
        self.last_change = _now()
        self.down_since = None
        self._recovery_candidate, self._recovery_successes, self._primary_successes = None, 0, 0
        outage = round(time.time() - previous_down_since, 2) if previous_down_since else None
        self.pending_sync = True
        result = await self.sync_now()
        roles = await self.assign_roles(index)
        severity = "INFO" if result == "SYNCED" else "WARNING"
        await self._emit(
            kind, severity,
            f"{error_free_detail} Active controller: {self.role_of(index)} ({self.active_url}). "
            f"Topology resync: {result}.",
            role=self.role_of(index), sync_status=result, outage_seconds=outage, roles=roles,
        )

    async def _declare_down(self) -> None:
        self.status = DOWN
        self.outage_count += 1
        self.down_since = time.time()
        self.last_change = _now()
        self.pending_sync = True
        self._recovery_candidate, self._recovery_successes, self._primary_successes = None, 0, 0
        await self._emit(
            "CONTROLLER_DOWN", "CRITICAL",
            f"Controller {self.role_of(self.active_index)} ({self.active_url}) missed "
            f"{self.consecutive_failures} consecutive heartbeats: {self.last_error}. "
            "Existing switch flows keep forwarding; topology changes are queued.",
            failures=self.consecutive_failures, error=self.last_error,
        )
        # Immediate failover attempt to a standby, in configured order.
        for index in range(1, len(self.endpoints)):
            if index == self.active_index:
                continue
            healthy, _ = await self.probe(index)
            if healthy:
                self.failover_count += 1
                await self._become_up(index, "CONTROLLER_FAILOVER",
                                      f"Failed over to standby controller {self.endpoints[index]}.")
                return

    # ------------------------------------------------------------------ loop
    async def check_once(self) -> str:
        async with self._lock:
            if self.status == UP:
                await self._check_active()
            else:
                await self._check_for_recovery()
            return self.status

    async def _check_active(self) -> None:
        healthy, error = await self.probe(self.active_index)
        if not healthy:
            self.consecutive_failures += 1
            self.last_error = error
            self._primary_successes = 0
            if self.consecutive_failures >= self.failure_threshold:
                await self._declare_down()
            return
        self.consecutive_failures = 0
        self.last_heartbeat = _now()

        # Running on a standby: fail back once the primary is durably healthy.
        if self.active_index != 0:
            ok, _ = await self.probe(0)
            self._primary_successes = self._primary_successes + 1 if ok else 0
            if self._primary_successes >= self.recovery_threshold:
                await self._become_up(0, "CONTROLLER_FAILBACK",
                                      f"Primary controller {self.endpoints[0]} recovered.")
                return

        await self._refresh_standby_roles()
        state = await self.fetch_state()
        if state is not None:
            self.state = state
            self.endpoint_health[self.active_url]["of_role"] = (state.get("ha") or {}).get("role")
            # A restarted controller comes back with an empty model: resync it.
            version = self.snapshot_provider()["version"]
            if state.get("topology_version") != version and not self.pending_sync:
                self.pending_sync = True
            if self.pending_sync:
                await self.sync_now()
            ha = state.get("ha") or {}
            if len(self.endpoints) > 1 and ha.get("enabled") and ha.get("role") != "MASTER":
                # The active controller is not holding the master role: re-assert it.
                await self.assign_roles(self.active_index)
            if self.on_state:
                await self.on_state(state)

    async def _refresh_standby_roles(self) -> None:
        """Record each reachable controller's own view of its OpenFlow role (display only)."""
        for index, url in enumerate(self.endpoints):
            health = self.endpoint_health[url]
            if index != self.active_index:
                await self.probe(index)          # keep standby health current for the dashboard
            if index == self.active_index or not health.get("healthy"):
                health["of_role"] = None if not health.get("healthy") else health.get("of_role")
                continue
            try:
                response = await self._request("GET", url, "/state")
                health["of_role"] = (response.json().get("ha") or {}).get("role")
            except (httpx.HTTPError, ValueError):
                health["of_role"] = None

    async def _check_for_recovery(self) -> None:
        for index in range(len(self.endpoints)):
            healthy, error = await self.probe(index)
            if healthy:
                if self.status == UNKNOWN:  # first contact: trust immediately
                    await self._become_up(index, "CONTROLLER_CONNECTED",
                                          "Controller connection established.")
                    return
                if self._recovery_candidate == index:
                    self._recovery_successes += 1
                else:
                    self._recovery_candidate, self._recovery_successes = index, 1
                if self._recovery_successes >= self.recovery_threshold:
                    kind = "CONTROLLER_RECOVERED" if index == 0 else "CONTROLLER_FAILOVER"
                    if index != 0:
                        self.failover_count += 1
                    await self._become_up(index, kind, f"Controller {self.endpoints[index]} is reachable again.")
                return
            self.last_error = error
        self._recovery_candidate, self._recovery_successes = None, 0
        if self.status == UNKNOWN:
            self.consecutive_failures += 1
            if self.consecutive_failures >= self.failure_threshold:
                await self._declare_down()

    async def _run(self) -> None:
        while True:
            try:
                await self.check_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("controller monitor iteration failed")
            await asyncio.sleep(self.interval)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    # ---------------------------------------------------------------- status
    def describe(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "connected": self.status == UP,
            "active_url": self.active_url,
            "active_role": self.role_of(self.active_index),
            "controller_id": (self.state or {}).get("controller_id"),
            "consecutive_failures": self.consecutive_failures,
            "failure_threshold": self.failure_threshold,
            "recovery_threshold": self.recovery_threshold,
            "heartbeat_interval_sec": self.interval,
            "last_error": self.last_error,
            "last_heartbeat": self.last_heartbeat,
            "last_change": self.last_change,
            "failover_count": self.failover_count,
            "outage_count": self.outage_count,
            "pending_sync": self.pending_sync,
            "ha": (self.state or {}).get("ha"),
            "synced_version": self.synced_version,
            "current_version": self.snapshot_provider()["version"],
            "endpoints": [
                {"url": url, "role": self.role_of(i), "active": i == self.active_index,
                 **self.endpoint_health[url]}
                for i, url in enumerate(self.endpoints)
            ],
            "history": list(self.history)[-20:],
        }
