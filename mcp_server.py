"""Local file tools over MCP stdio. Stdout is reserved for the protocol."""
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from workspace_tools import WorkspaceTools

workspace = WorkspaceTools(os.environ.get(
    "WORKSPACE_DIR", str(Path(__file__).resolve().parent / "mcp_workspace")))
mcp = FastMCP("DevOps Local Workspace")


@mcp.tool()
def list_files(path: str = ".") -> dict:
    """List files within the isolated demonstration workspace."""
    return workspace.list_files(path)


@mcp.tool()
def read_file(path: str) -> dict:
    """Read a UTF-8 text file inside the demonstration workspace."""
    return workspace.read_file(path)


@mcp.tool()
def write_file(path: str, content: str) -> dict:
    """Write UTF-8 text inside the demonstration workspace."""
    return workspace.write_file(path, content)


if __name__ == "__main__":
    mcp.run(transport="stdio")
