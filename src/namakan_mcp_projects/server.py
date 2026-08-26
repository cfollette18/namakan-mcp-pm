from __future__ import annotations

import json
import os
import sys
from typing import Any

from namakan_mcp_projects.backends import PmBackend, load_backend

WRITE_TOOLS = {"pm_update_status", "pm_add_comment"}


def writes_allowed() -> bool:
    return os.environ.get("NAMAKAN_MCP_ALLOW_WRITES", "").strip() in {"1", "true", "yes"}


def dry_run() -> bool:
    return os.environ.get("NAMAKAN_MCP_DRY_RUN", "").strip() in {"1", "true", "yes"}


def list_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "pm_find_task",
            "description": "Find tasks by title or id. Backend-agnostic.",
            "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        },
        {
            "name": "pm_update_status",
            "description": "Update task status. Disabled unless NAMAKAN_MCP_ALLOW_WRITES=1.",
            "inputSchema": {"type": "object", "properties": {"task_id": {"type": "string"}, "status": {"type": "string"}}, "required": ["task_id", "status"]},
        },
        {
            "name": "pm_add_comment",
            "description": "Comment on a task. Disabled unless NAMAKAN_MCP_ALLOW_WRITES=1.",
            "inputSchema": {"type": "object", "properties": {"task_id": {"type": "string"}, "body": {"type": "string"}}, "required": ["task_id", "body"]},
        },
    ]


def handle(tool: str, arguments: dict[str, Any], backend: PmBackend | None = None) -> dict[str, Any]:
    backend = backend or load_backend(os.environ.get("NAMAKAN_PM_BACKEND", "mock"))
    if tool in WRITE_TOOLS and not writes_allowed():
        return {"ok": False, "error": "writes_disabled", "hint": "Set NAMAKAN_MCP_ALLOW_WRITES=1 after CISO approval."}
    if tool in WRITE_TOOLS and dry_run():
        return {"ok": True, "dry_run": True, "would_call": tool, "arguments": arguments}
    if tool == "pm_find_task":
        return {"ok": True, "data": backend.find_task(arguments["query"])}
    if tool == "pm_update_status":
        return {"ok": True, "data": backend.update_status(arguments["task_id"], arguments["status"])}
    if tool == "pm_add_comment":
        return {"ok": True, "data": backend.add_comment(arguments["task_id"], arguments["body"])}
    return {"ok": False, "error": f"unknown tool {tool}"}


def serve_stdio() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req = json.loads(line)
        method = req.get("method")
        req_id = req.get("id")
        if method == "initialize":
            resp = {"jsonrpc": "2.0", "id": req_id, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "namakan-mcp-projects", "version": "0.1.0"}}}
        elif method == "tools/list":
            resp = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": list_tools()}}
        elif method == "tools/call":
            params = req.get("params") or {}
            resp = {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(handle(params["name"], params.get("arguments") or {}))}]}}
        else:
            resp = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": method}}
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


def main() -> None:
    serve_stdio()
