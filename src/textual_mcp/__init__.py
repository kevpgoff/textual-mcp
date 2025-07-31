"""Textual MCP Server - Model Context Protocol server for Textual TUI framework."""

__version__ = "0.1.0"
__author__ = "Textual MCP Team"
__email__ = "team@textual-mcp.dev"

from .server import create_server

__all__ = ["create_server", "__version__"]
