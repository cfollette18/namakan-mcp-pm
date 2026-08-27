from namakan_mcp_pm.backends import MockPm
from namakan_mcp_pm.protocol import handle_rpc
from namakan_mcp_pm.server import VERSION, handle, list_tools, main, run_workflow


def test_find_task():
    out = handle("pm_find_task", {"query": "workflow"}, backend=MockPm())
    assert out["data"][0]["id"] == "t1"


def test_list_projects():
    out = handle("pm_list_projects", {}, backend=MockPm())
    assert len(out["data"]) >= 1


def test_writes_disabled(monkeypatch):
    monkeypatch.delenv("NAMAKAN_MCP_ALLOW_WRITES", raising=False)
    out = handle("pm_update_status", {"task_id": "t1", "status": "done"}, backend=MockPm())
    assert out["error"] == "writes_disabled"


def test_workflow_blocks_write(monkeypatch):
    monkeypatch.delenv("NAMAKAN_MCP_ALLOW_WRITES", raising=False)
    out = run_workflow("engagement-board", backend=MockPm())
    assert out["ok"]
    assert out["steps"][-1]["error"] == "writes_disabled"


def test_mcp_list():
    resp = handle_rpc(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        server_name="namakan-mcp-pm",
        version=VERSION,
        list_tools=list_tools,
        call_tool=handle,
    )
    names = {tool["name"] for tool in resp["result"]["tools"]}
    assert "pm_run_workflow" in names


def test_cli():
    assert main(["tools"]) == 0
    assert main(["demo"]) == 0
