"""MCP stdio: Content-Length framing (Cursor / Claude Desktop / Hermes) plus NDJSON."""

from __future__ import annotations

import json
import sys
from typing import Any, Callable


def read_message(stdin_buffer) -> dict[str, Any] | None:
    header = b""
    while True:
        chunk = stdin_buffer.readline()
        if chunk == b"":
            return None
        if chunk in (b"\r\n", b"\n"):
            break
        header += chunk
        if header.lstrip().startswith(b"{") and chunk.rstrip().endswith(b"}"):
            return json.loads(header.decode("utf-8"))
    if not header.strip():
        # NDJSON: the JSON was the "blank" after a JSON line handled above; try again
        return read_message(stdin_buffer)
    if header.lstrip().startswith(b"{"):
        return json.loads(header.decode("utf-8"))
    length = 0
    for raw_line in header.splitlines():
        line = raw_line.decode("utf-8", errors="replace")
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip().lower() == "content-length":
            length = int(value.strip())
    body = stdin_buffer.read(length)
    if not body:
        return None
    return json.loads(body.decode("utf-8"))


def write_message(payload: dict[str, Any], stdout_buffer) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    stdout_buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body)
    stdout_buffer.flush()


def serve(
    *,
    server_name: str,
    version: str,
    list_tools: Callable[[], list[dict[str, Any]]],
    call_tool: Callable[[str, dict[str, Any]], dict[str, Any]],
) -> None:
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    while True:
        req = read_message(stdin)
        if req is None:
            return
        method = req.get("method")
        req_id = req.get("id")
        if method == "initialize":
            write_message(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {"listChanged": False}},
                        "serverInfo": {"name": server_name, "version": version},
                    },
                },
                stdout,
            )
        elif method == "notifications/initialized" or method == "initialized":
            continue
        elif method == "ping":
            write_message({"jsonrpc": "2.0", "id": req_id, "result": {}}, stdout)
        elif method == "tools/list":
            write_message(
                {"jsonrpc": "2.0", "id": req_id, "result": {"tools": list_tools()}},
                stdout,
            )
        elif method == "tools/call":
            params = req.get("params") or {}
            result = call_tool(params.get("name") or "", params.get("arguments") or {})
            write_message(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, default=str)}],
                        "isError": not result.get("ok", True),
                    },
                },
                stdout,
            )
        elif req_id is None:
            continue
        else:
            write_message(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown method {method}"},
                },
                stdout,
            )


def parse_kv(pairs: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for item in pairs:
        if "=" not in item:
            raise SystemExit(f"expected key=value, got {item!r}")
        key, value = item.split("=", 1)
        if value.lower() in {"true", "false"}:
            out[key] = value.lower() == "true"
        else:
            try:
                out[key] = int(value) if value.isdigit() else float(value)
            except ValueError:
                out[key] = value
    return out
