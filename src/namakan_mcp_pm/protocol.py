"""MCP stdio: Content-Length framing for Hermes agent profiles, plus NDJSON."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Callable

ListTools = Callable[[], list[dict[str, Any]]]
CallTool = Callable[[str, dict[str, Any]], dict[str, Any]]


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


def handle_rpc(
    req: dict[str, Any],
    *,
    server_name: str,
    version: str,
    list_tools: ListTools,
    call_tool: CallTool,
) -> dict[str, Any] | None:
    """Return a JSON-RPC response, or None for notifications."""
    method = req.get("method")
    req_id = req.get("id")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": server_name, "version": version},
            },
        }
    if method in {"notifications/initialized", "initialized"}:
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": list_tools()}}
    if method == "tools/call":
        params = req.get("params") or {}
        result = call_tool(params.get("name") or "", params.get("arguments") or {})
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result, default=str)}],
                "isError": not result.get("ok", True),
            },
        }
    if req_id is None:
        return None
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Unknown method {method}"},
    }


def serve(
    *,
    server_name: str,
    version: str,
    list_tools: ListTools,
    call_tool: CallTool,
) -> None:
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    while True:
        req = read_message(stdin)
        if req is None:
            return
        response = handle_rpc(
            req,
            server_name=server_name,
            version=version,
            list_tools=list_tools,
            call_tool=call_tool,
        )
        if response is not None:
            write_message(response, stdout)


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
                out[key] = json.loads(value)
            except json.JSONDecodeError:
                out[key] = value
    return out


def as_object(value: Any) -> Any:
    """MCP hosts sometimes send JSON objects as strings."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def cli_main(
    argv: list[str] | None,
    *,
    prog: str,
    description: str,
    version: str,
    server_name: str,
    list_tools: ListTools,
    call_tool: CallTool,
    run_workflow: Callable[..., dict[str, Any]],
) -> int:
    """serve (default) | tools | workflow | demo | call TOOL k=v."""
    parser = argparse.ArgumentParser(prog=prog, description=description)
    parser.add_argument("--version", action="version", version=f"{prog} {version}")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("serve", help="MCP stdio — Hermes launches this when the agent profile starts")
    sub.add_parser("tools", help="Print tool names (no host required)")
    sub.add_parser("workflow", help="Run the bundled AI workflow on synthetic data")
    sub.add_parser("demo", help="Alias for workflow")
    call = sub.add_parser("call", help="Invoke one tool without an MCP host: call TOOL k=v")
    call.add_argument("tool")
    call.add_argument("kv", nargs="*")
    args = parser.parse_args(argv)
    cmd = args.cmd or "serve"
    if cmd == "tools":
        for tool in list_tools():
            print(f"{tool['name']}\t{tool['description']}")
        return 0
    if cmd in {"workflow", "demo"}:
        print(json.dumps(run_workflow(), indent=2, default=str))
        return 0
    if cmd == "call":
        print(json.dumps(call_tool(args.tool, parse_kv(args.kv)), indent=2, default=str))
        return 0
    serve(
        server_name=server_name,
        version=version,
        list_tools=list_tools,
        call_tool=call_tool,
    )
    return 0
