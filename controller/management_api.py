"""Small authenticated HTTP management API hosted by the controller process."""
import asyncio
import hmac
import json
from typing import Any

from controller.topology.sync import SnapshotError

MAX_BODY_BYTES = 1_000_000
REASONS = {
    200: "OK", 400: "Bad Request", 401: "Unauthorized", 404: "Not Found",
    409: "Conflict", 422: "Unprocessable Entity", 500: "Internal Server Error",
}


class ControllerManagementAPI:
    def __init__(self, app: Any, host: str, port: int, token: str):
        self.app = app
        self.host = host
        self.port = port
        self.token = token
        self.server: asyncio.AbstractServer | None = None

    async def start(self) -> None:
        if not self.token or self.token == "change-me":
            raise RuntimeError("CONTROLLER_API_TOKEN must be set to a non-default value")
        self.server = await asyncio.start_server(self._handle, self.host, self.port)

    async def stop(self) -> None:
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            header_bytes = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5)
            header = header_bytes.decode("latin-1")
            lines = header.split("\r\n")
            method, path, _ = lines[0].split(" ", 2)
            headers = {
                key.lower(): value.strip()
                for line in lines[1:] if ": " in line
                for key, value in [line.split(": ", 1)]
            }
            length = int(headers.get("content-length", "0"))
            if length < 0 or length > MAX_BODY_BYTES:
                await self._write(writer, 400, {"detail": "Invalid content length"})
                return
            body = await asyncio.wait_for(reader.readexactly(length), timeout=5) if length else b""
            if not hmac.compare_digest(headers.get("authorization", ""), f"Bearer {self.token}"):
                await self._write(writer, 401, {"detail": "Unauthorized"})
                return
            if method == "GET" and path == "/health":
                await self._write(writer, 200, {
                    "status": "ok",
                    "connected_switches": len(self.app.switch_manager.datapaths),
                })
                return
            if method == "POST" and path == "/routes/install":
                request = json.loads(body.decode("utf-8"))
                result = await self.app.route_installer.install(request)
                await self._write(writer, 200 if result["status"] != "FAILED" else 422, result)
                return
            if method == "GET" and path == "/state":
                await self._write(writer, 200, self.app.export_state())
                return
            if method == "POST" and path == "/role":
                request = json.loads(body.decode("utf-8") or "{}")
                try:
                    result = await self.app.ha.set_role(str(request.get("role", "")), reason=request.get("reason", "api"))
                except ValueError as exc:
                    await self._write(writer, 422, {"detail": str(exc)})
                    return
                await self._write(writer, 200, result)
                return
            if method == "GET" and path == "/flows":
                await self._write(writer, 200, {"flows": self.app.export_flows()})
                return
            if method == "POST" and path == "/topology/sync":
                try:
                    snapshot = json.loads(body.decode("utf-8"))
                    summary = await self.app.apply_topology_snapshot(snapshot)
                except SnapshotError as exc:
                    await self._write(writer, 422, {"detail": str(exc)})
                    return
                except ValueError as exc:
                    if str(exc).startswith("stale"):
                        await self._write(writer, 409, {
                            "detail": str(exc),
                            "applied_version": self.app.topology_version,
                        })
                        return
                    raise
                await self._write(writer, 200, {"status": "APPLIED", **summary})
                return
            await self._write(writer, 404, {"detail": "Not found"})
        except (asyncio.IncompleteReadError, asyncio.TimeoutError, ValueError, json.JSONDecodeError) as exc:
            await self._write(writer, 400, {"detail": str(exc) or exc.__class__.__name__})
        except Exception as exc:  # never leave the caller hanging on a handler bug
            await self._write(writer, 500, {"detail": f"{exc.__class__.__name__}: {exc}"})
        finally:
            writer.close()
            await writer.wait_closed()

    @staticmethod
    async def _write(writer: asyncio.StreamWriter, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        reason = REASONS.get(status, "Error")
        response = (
            f"HTTP/1.1 {status} {reason}\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii") + body
        writer.write(response)
        await writer.drain()
