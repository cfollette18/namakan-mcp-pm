from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from namakan_mcp_projects.backends import PmBackend, load_backend
from namakan_mcp_projects.protocol import parse_kv, serve as serve_mcp

VERSION = "0.2.0"

WRITE_TOOLS = {"pm_update_status", "pm_add_comment"}


def writes_allowed() -> bool:
    return os.environ.get("NAMAKAN_MCP_ALLOW_WRITES", "").strip() in {"1", "true", "yes"}


def dry_run() -> bool:
    return os.environ.get("NAMAKAN_MCP_DRY_RUN", "").strip() in {"1", "true", "yes"}


def list_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "pm_find_task",
            "description": "Find tasks by title, id, or assignee.",
            "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        },
        {
            "name": "pm_list_tasks",
            "description": "List tasks, optionally for one project_id.",
            "inputSchema": {"type": "object", "properties": {"project_id": {"type": "string"}}},
        },
        {
            "name": "pm_list_projects",
            "description": "List projects.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "pm_update_status",
            "description": "Update task status. Disabled unless NAMAKAN_MCP_ALLOW_WRITES=1.",
            "inputSchema": {
                "type": "object",
                "properties": {"task_id": {"type": "string"}, "status": {"type": "string"}},
                "required": ["task_id", "status"],
            },
        },
        {
            "name": "pm_add_comment",
            "description": "Comment on a task. Disabled unless NAMAKAN_MCP_ALLOW_WRITES=1.",
            "inputSchema": {
                "type": "object",
                "properties": {"task_id": {"type": "string"}, "body": {"type": "string"}},
                "required": ["task_id", "body"],
            },
        },
    ]


def handle(tool: str, arguments: dict[str, Any], backend: PmBackend | None = None) -> dict[str, Any]:
    backend = backend or load_backend(None)
    if tool in WRITE_TOOLS and not writes_allowed():
        return {
            "ok": False,
            "error": "writes_disabled",
            "hint": "Read-only by default. Set NAMAKAN_MCP_ALLOW_WRITES=1 after approval.",
        }
    if tool in WRITE_TOOLS and dry_run():
        return {"ok": True, "dry_run": True, "would_call": tool, "arguments": arguments}
    try:
        if tool == "pm_find_task":
            return {"ok": True, "data": backend.find_task(arguments["query"])}
        if tool == "pm_list_tasks":
            return {"ok": True, "data": backend.list_tasks(arguments.get("project_id"))}
        if tool == "pm_list_projects":
            return {"ok": True, "data": backend.list_projects()}
        if tool == "pm_update_status":
            return {"ok": True, "data": backend.update_status(arguments["task_id"], arguments["status"])}
        if tool == "pm_add_comment":
            return {"ok": True, "data": backend.add_comment(arguments["task_id"], arguments["body"])}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
    except KeyError as exc:
        return {"ok": False, "error": f"missing argument {exc}"}
    return {"ok": False, "error": f"unknown tool {tool}"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="namakan-mcp-projects",
        description="Unified project-management MCP server.",
    )
    parser.add_argument("--version", action="version", version=f"namakan-mcp-projects {VERSION}")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("serve")
    sub.add_parser("tools")
    sub.add_parser("demo")
    call = sub.add_parser("call")
    call.add_argument("tool")
    call.add_argument("kv", nargs="*")
    args = parser.parse_args(argv)
    cmd = args.cmd or "serve"
    if cmd == "tools":
        for tool in list_tools():
            print(f"{tool['name']}\t{tool['description']}")
        return 0
    if cmd == "demo":
        print(json.dumps(handle("pm_list_projects", {}), indent=2))
        print(json.dumps(handle("pm_find_task", {"query": "audit"}), indent=2))
        print(json.dumps(handle("pm_update_status", {"task_id": "t1", "status": "done"}), indent=2))
        return 0
    if cmd == "call":
        print(json.dumps(handle(args.tool, parse_kv(args.kv)), indent=2, default=str))
        return 0
    serve_mcp(
        server_name="namakan-mcp-projects",
        version=VERSION,
        list_tools=list_tools,
        call_tool=handle,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
