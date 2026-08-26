"""Unified MCP server for project and work-management systems."""

from namakan_mcp_projects.server import handle, list_tools, serve_stdio

__version__ = "0.1.0"
__all__ = ["handle", "list_tools", "serve_stdio", "__version__"]
