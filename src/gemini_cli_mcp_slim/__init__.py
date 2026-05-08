"""gemini_cli_mcp_slim - thin auditable MCP wrapper around the gemini CLI."""

from importlib.metadata import version as _pkg_version

from .server import main

__version__ = _pkg_version("gemini-cli-mcp-slim")
__all__ = ["__version__", "main"]
