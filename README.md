# namakan-mcp-projects

Unified MCP server for project and work management. Same tools (`pm_find_task`, `pm_update_status`, `pm_add_comment`) for Jira, Asana, Monday, ClickUp, Smartsheet, Microsoft Project, and Trello.

Also used internally by Namakan's `delivery-manager` to project engagement status into a client's project tool.

**Read-only by default.** Writes: `NAMAKAN_MCP_ALLOW_WRITES=1`.

```bash
NAMAKAN_PM_BACKEND=mock namakan-mcp-projects
```

## License

MIT. Copyright (c) 2026 Namakan AI Engineering.
