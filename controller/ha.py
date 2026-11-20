"""Controller high availability: OpenFlow role arbitration and peer supervision.

Several controllers may connect to the same switches. OpenFlow lets exactly one
of them be MASTER (it receives Packet-Ins and may program flows); the others are
SLAVE (read-only). Arbitration happens *in the switch*: a ROLE_REQUEST carrying a
newer generation_id demotes the previous master, and a request with an older id
is rejected as stale. That prevents two controllers from programming the same
switch even if both believe they are in charge.

``HAManager`` decides which role this controller *asks* for:

* a controller starts as MASTER unless its peer is already MASTER;
* a SLAVE promotes itself after the peer misses ``failure_threshold`` heartbeats;
* a non-preferred MASTER (the standby) hands control back to the preferred
  controller once that peer has been healthy for ``recovery_threshold`` beats.

The backend can also assign roles explicitly through ``POST /role``.
"""
import asyncio
import time
from typing import Any, Callable, Dict, Optional

import httpx

from controller.openflow.protocol import (
    OFPCR_ROLE_EQUAL,
    OFPCR_ROLE_NOCHANGE,
    OFPCR_ROLE_MASTER,
    OFPCR_ROLE_SLAVE,
    OFPBRC_IS_SLAVE,
    OFPET_BAD_REQUEST,
    OFPET_ROLE_REQUEST_FAILED,
    OFPRRFC_STALE,
    build_role_request,
)
from controller.utils.logger import log

ROLE_NAMES = {OFPCR_ROLE_EQUAL: "EQUAL", OFPCR_ROLE_MASTER: "MASTER", OFPCR_ROLE_SLAVE: "SLAVE"}
NAME_TO_ROLE = {"MASTER": OFPCR_ROLE_MASTER, "SLAVE": OFPCR_ROLE_SLAVE}


NO_GENERATION = 0xFFFFFFFFFFFFFFFF   # a switch reports this when it has seen no generation id yet


def next_generation_id() -> int:
    """Local clock proposal (epoch ms). Not trusted alone: see ``learn_generation``."""
    return int(time.time() * 1000)


class HAManager:
    def __init__(
        self,
        switch_manager: Any,
        controller_id: str,
        preferred: bool = True,
        peer_url: Optional[str] = None,
        token: str = "",
        interval: float = 1.0,
        failure_threshold: int = 3,
        recovery_threshold: int = 3,
        on_promoted: Optional[Callable[[], Any]] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self.switch_manager = switch_manager
        self.controller_id = controller_id
        self.preferred = preferred
        self.peer_url = peer_url.rstrip("/") if peer_url else None
        self.token = token
        self.interval = interval
        self.failure_threshold = failure_threshold
        self.recovery_threshold = recovery_threshold
        self.on_promoted = on_promoted
        self.transport = transport

        # Role negotiation is only active in multi-controller deployments (a peer is
        # configured, or the backend assigns roles); a lone controller stays EQUAL.
        self.enabled: bool = bool(peer_url)
        # A configured standby waits for the preferred controller; everyone else leads.
        self.desired: int = OFPCR_ROLE_MASTER if (preferred or not peer_url) else OFPCR_ROLE_SLAVE
        self.generation_id: int = 0
        self.peer_failures = 0
        self.peer_successes = 0
        self.peer_role: Optional[str] = None
        self._stale_retries: Dict[str, int] = {}
        self._awaiting_generation: set = set()
        self.switch_generations: Dict[str, int] = {}   # newest generation id each switch reported
        self.transitions: list = []
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    # ----------------------------------------------------------------- state
    @property
    def role_name(self) -> str:
        return ROLE_NAMES[self.desired]

    @property
    def is_master(self) -> bool:
        return self.desired == OFPCR_ROLE_MASTER

    def describe(self) -> Dict[str, Any]:
        roles = {dp.sw_id: ROLE_NAMES.get(getattr(dp, "role", None), "UNKNOWN")
                 for dp in self.switch_manager.datapaths.values()}
        return {
            "controller_id": self.controller_id,
            "enabled": self.enabled,
            "role": self.role_name,
            "preferred": self.preferred,
            "generation_id": self.generation_id,
            "peer_url": self.peer_url,
            "peer_role": self.peer_role,
            "peer_failures": self.peer_failures,
            "switch_roles": roles,
            "transitions": self.transitions[-10:],
        }

    def _record(self, event: str, **data: Any) -> None:
        entry = {"event": event, "role": self.role_name, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **data}
        self.transitions.append(entry)
        log.info("HA %s -> role=%s %s", event, self.role_name, data or "")

    # ------------------------------------------------------------- switches
    async def request_role(self, dp: Any) -> bool:
        """Ask one switch for our desired role with the current generation id."""
        if not self.enabled:
            return True
        # Fresh, monotonic generation per request: the switch rejects any MASTER or
        # SLAVE request older than the newest one it has seen from any controller.
        self.generation_id = max(self.generation_id + 1, next_generation_id())
        return await dp.send_msg(build_role_request(self.desired, self.generation_id, xid=0x5000))

    async def apply_to_all(self) -> None:
        for dp in list(self.switch_manager.datapaths.values()):
            await self.request_role(dp)

    async def set_role(self, role_name: str, reason: str = "requested") -> Dict[str, Any]:
        """Switch this controller to MASTER or SLAVE and tell every switch.

        Promotion uses a fresh generation id so it supersedes any previous master;
        ``on_promoted`` then reprograms routes because a former slave's flow
        registry may be stale.
        """
        role_name = role_name.upper()
        if role_name not in NAME_TO_ROLE:
            raise ValueError("role must be MASTER or SLAVE")
        async with self._lock:
            self.enabled = True
            new = NAME_TO_ROLE[role_name]
            changed = new != self.desired
            self.desired = new
            await self.apply_to_all()
            if changed:
                self._record("promoted" if new == OFPCR_ROLE_MASTER else "demoted", reason=reason)
        if changed and new == OFPCR_ROLE_MASTER and self.on_promoted:
            res = self.on_promoted()
            if asyncio.iscoroutine(res):
                await res
        return self.describe()

    # ---------------------------------------------------- switch callbacks
    async def on_switch_connected(self, dp: Any) -> None:
        await self.request_role(dp)

    def on_error(self, dp: Any, err_type: int, err_code: int) -> None:
        """React to arbitration errors reported by a switch."""
        stale = err_type == OFPET_ROLE_REQUEST_FAILED and err_code == OFPRRFC_STALE
        slave_write = err_type == OFPET_BAD_REQUEST and err_code == OFPBRC_IS_SLAVE
        if stale and self.enabled:
            # Our generation id is older than the switch's (lost a race, or this host's
            # clock is behind). Ask the switch what generation it holds (NOCHANGE query);
            # on_role_reply then retries with an id above it, independent of clock skew.
            retries = self._stale_retries.get(dp.sw_id, 0)
            if retries < 5:
                self._stale_retries[dp.sw_id] = retries + 1
                self._awaiting_generation.add(dp.sw_id)
                try:
                    asyncio.get_running_loop().create_task(
                        dp.send_msg(build_role_request(OFPCR_ROLE_NOCHANGE, 0, xid=0x5001)))
                except RuntimeError:
                    pass
        elif slave_write and self.desired == OFPCR_ROLE_MASTER:
            # The switch demoted us (another controller became master).
            self.desired = OFPCR_ROLE_SLAVE
            self._record("demoted", reason="switch reports we are slave", switch=dp.sw_id)

    async def on_role_reply(self, dp: Any, reply: Any) -> None:
        """Learn the switch's generation id; finish a pending stale-retry above it."""
        if reply.generation_id != NO_GENERATION:
            self.switch_generations[dp.sw_id] = reply.generation_id
            # Never propose an id at or below what the switch already holds.
            self.generation_id = max(self.generation_id, reply.generation_id)
        else:
            self.switch_generations.pop(dp.sw_id, None)
        if dp.sw_id in self._awaiting_generation:
            self._awaiting_generation.discard(dp.sw_id)
            await self.request_role(dp)           # request_role takes max(learned + 1, clock)
        elif reply.role == self.desired:
            self._stale_retries.pop(dp.sw_id, None)

    # ----------------------------------------------------------- peer watch
    async def _peer_state(self) -> Optional[Dict[str, Any]]:
        if not self.peer_url:
            return None
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(min(self.interval, 1.5)), transport=self.transport) as client:
                resp = await client.get(f"{self.peer_url}/state", headers={"Authorization": f"Bearer {self.token}"})
            return resp.json() if resp.status_code == 200 else None
        except (httpx.HTTPError, ValueError):
            return None

    async def _ask_peer_to_take_over(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(2.0), transport=self.transport) as client:
                resp = await client.post(f"{self.peer_url}/role", json={"role": "MASTER", "reason": "failback"},
                                         headers={"Authorization": f"Bearer {self.token}"})
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def decide_initial_role(self) -> None:
        """Start SLAVE if the peer is already master (it holds the fresher state)."""
        state = await self._peer_state()
        if state and (state.get("ha") or {}).get("role") == "MASTER":
            self.desired = OFPCR_ROLE_SLAVE
            self.peer_role = "MASTER"
            self._record("start-slave", reason="peer is already master")

    async def check_peer(self) -> None:
        """One supervision step (also called directly by tests)."""
        state = await self._peer_state()
        if state is None:
            self.peer_failures += 1
            self.peer_successes = 0
            self.peer_role = None
            if self.desired == OFPCR_ROLE_SLAVE and self.peer_failures >= self.failure_threshold:
                await self.set_role("MASTER", reason=f"peer missed {self.peer_failures} heartbeats")
            return
        self.peer_failures = 0
        self.peer_successes += 1
        self.peer_role = (state.get("ha") or {}).get("role")
        if (self.desired == OFPCR_ROLE_MASTER and not self.preferred
                and self.peer_successes >= self.recovery_threshold and self.peer_role != "MASTER"):
            if await self._ask_peer_to_take_over():
                await self.set_role("SLAVE", reason="preferred controller recovered")
                self.peer_successes = 0
        elif self.desired == OFPCR_ROLE_MASTER and self.peer_role == "MASTER" and not self.preferred:
            # Two masters (e.g. partition healed): the non-preferred one yields.
            await self.set_role("SLAVE", reason="peer also master; yielding to preferred")

    async def _run(self) -> None:
        await self.decide_initial_role()
        while True:
            try:
                await self.check_peer()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.error("HA peer check failed: %s", exc)
            await asyncio.sleep(self.interval)

    def start(self) -> None:
        if self.peer_url and (self._task is None or self._task.done()):
            self._task = asyncio.create_task(self._run())

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
