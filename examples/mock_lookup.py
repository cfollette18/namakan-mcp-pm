from namakan_mcp_projects.backends import MockPm
from namakan_mcp_projects.server import handle

print(handle("pm_find_task", {"query": "Phase 1"}, backend=MockPm()))
print(handle("pm_list_projects", {}, backend=MockPm()))
