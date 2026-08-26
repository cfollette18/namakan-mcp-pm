from namakan_mcp_projects.backends import MockPm
from namakan_mcp_projects.server import handle


def test_find_task():
    out = handle("pm_find_task", {"query": "audit"}, backend=MockPm())
    assert out["data"][0]["id"] == "t1"


def test_writes_disabled(monkeypatch):
    monkeypatch.delenv("NAMAKAN_MCP_ALLOW_WRITES", raising=False)
    out = handle("pm_update_status", {"task_id": "t1", "status": "done"}, backend=MockPm())
    assert out["error"] == "writes_disabled"
