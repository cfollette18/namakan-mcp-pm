from __future__ import annotations

import os
import sys
from typing import Any

from namakan_mcp_pm.backends import PmBackend, load_backend
from namakan_mcp_pm.protocol import cli_main

VERSION = "0.3.1"

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
        {
            "name": "pm_run_workflow",
            "description": "Full AI workflow out of the box: list projects → find task → blocked status update. Mock board. No Jira token.",
            "inputSchema": {
                "type": "object",
                "properties": {"use_case": {"type": "string"}, "query": {"type": "string"}},
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
        if tool == "pm_run_workflow":
            return run_workflow(
                str(arguments.get("use_case") or "engagement-board"),
                query=str(arguments.get("query") or "workflow"),
                backend=backend,
            )
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
    except KeyError as exc:
        return {"ok": False, "error": f"missing argument {exc}"}
    return {"ok": False, "error": f"unknown tool {tool}"}


def run_workflow(
    use_case: str = "engagement-board",
    *,
    query: str = "workflow",
    backend: PmBackend | None = None,
) -> dict[str, Any]:
    known = {"engagement-board", "where-is-the-audit", "close-the-task"}
    if use_case not in known:
        return {"ok": False, "error": f"unknown use_case {use_case}"}
    backend = backend or load_backend(None)
    steps = [
        {"tool": "pm_list_projects", **handle("pm_list_projects", {}, backend=backend)},
        {"tool": "pm_find_task", **handle("pm_find_task", {"query": query}, backend=backend)},
        {"tool": "pm_list_tasks", **handle("pm_list_tasks", {}, backend=backend)},
        {
            "tool": "pm_update_status",
            **handle("pm_update_status", {"task_id": "t1", "status": "done"}, backend=backend),
        },
    ]
    return {
        "ok": True,
        "workflow": use_case,
        "summary": (
            "Listed projects and found a task on the unified PM tools. "
            "The status write stayed blocked (read-only default) — that is the demo, not a failure."
        ),
        "steps": steps,
    }


def main(argv: list[str] | None = None) -> int:
    return cli_main(
        argv,
        prog="namakan-mcp-pm",
        description="Unified project-management MCP server.",
        version=VERSION,
        server_name="namakan-mcp-pm",
        list_tools=list_tools,
        call_tool=handle,
        run_workflow=run_workflow,
    )


if __name__ == "__main__":
    sys.exit(main())
