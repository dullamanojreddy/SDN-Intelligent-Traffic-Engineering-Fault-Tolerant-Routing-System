"""Small authenticated HTTP management API hosted by the controller process."""
import asyncio
import json
from typing import Any


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
            body = await asyncio.wait_for(reader.readexactly(length), timeout=5) if length else b""
            if headers.get("authorization") != f"Bearer {self.token}":
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
            await self._write(writer, 404, {"detail": "Not found"})
        except (asyncio.IncompleteReadError, asyncio.TimeoutError, ValueError, json.JSONDecodeError) as exc:
            await self._write(writer, 400, {"detail": str(exc)})
        finally:
            writer.close()
            await writer.wait_closed()

    @staticmethod
    async def _write(writer: asyncio.StreamWriter, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        reason = "OK" if status == 200 else "Unauthorized" if status == 401 else "Bad Request" if status == 400 else "Unprocessable Entity" if status == 422 else "Not Found"
        response = (
            f"HTTP/1.1 {status} {reason}\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii") + body
        writer.write(response)
        await writer.drain()
