"""Main MCP server implementation using FastMCP."""

import asyncio
import sys
from typing import Optional, Any

from fastmcp import FastMCP

from textual_mcp.config import load_config, TextualMCPConfig
from textual_mcp.utils.logging_config import setup_logging, get_logger
from textual_mcp.utils.errors import ConfigurationError
from textual_mcp.tools.validation_tools import register_validation_tools
from textual_mcp.tools.analysis_tools import register_analysis_tools
from textual_mcp.tools.widget_tools import register_widget_tools
from textual_mcp.tools.layout_tools import register_layout_tools
from textual_mcp.tools.documentation_tools import (
    register_documentation_tools,
    get_docs_memory,
)


class TextualMCPServer:
    """Main Textual MCP Server class."""

    def __init__(self, config: TextualMCPConfig):
        self.config = config
        self.logger = get_logger("server")

        self.mcp: Any = FastMCP(
            name="TextualMCP",
            version="0.1.0",
        )

        self._register_tools()

        # Initialize documentation search if enabled
        if config.search.auto_index:
            try:
                memory = get_docs_memory(config)
                if not memory.is_indexed():
                    self.logger.info("Documentation search will be indexed on first use")
                else:
                    self.logger.info("Documentation search index is ready")
            except Exception as e:
                self.logger.warning(f"Failed to initialize documentation search: {e}")

        self.logger.info("Textual MCP Server initialized")

    def _register_tools(self) -> None:
        """Register all MCP tools."""
        try:
            register_validation_tools(self.mcp, self.config)
            self.logger.info("Registered validation tools")

            register_analysis_tools(self.mcp, self.config)
            self.logger.info("Registered analysis tools")

            register_widget_tools(self.mcp, self.config)
            self.logger.info("Registered widget tools")

            register_layout_tools(self.mcp, self.config)
            self.logger.info("Registered layout tools")

            register_documentation_tools(self.mcp, self.config)
            self.logger.info("Registered documentation tools")

        except Exception as e:
            self.logger.error(f"Failed to register tools: {e}")
            raise ConfigurationError(f"Tool registration failed: {e}")

    async def start(self) -> None:
        """Start the MCP server."""
        try:
            self.logger.info("Starting Textual MCP Server...")
            await self.mcp.run()
        except Exception as e:
            self.logger.error(f"Server failed to start: {e}")
            raise

    def run(self) -> None:
        """Run the server (blocking)."""
        try:
            asyncio.run(self.start())
        except KeyboardInterrupt:
            self.logger.info("Server stopped by user")
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            sys.exit(1)


def create_server(config_path: Optional[str] = None) -> TextualMCPServer:
    """
    Create and configure the MCP server.

    Args:
        config_path: Optional path to configuration file

    Returns:
        Configured TextualMCPServer instance
    """
    try:
        config = load_config(config_path)

        setup_logging(config.logging)

        server = TextualMCPServer(config)

        return server

    except Exception as e:
        print(f"Failed to create server: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point for the server."""
    import argparse

    parser = argparse.ArgumentParser(description="Textual MCP Server")
    parser.add_argument("--config", "-c", type=str, help="Path to configuration file")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level",
    )
    parser.add_argument("--version", action="version", version="0.1.0")

    args = parser.parse_args()

    if args.log_level:
        import os

        os.environ["LOG_LEVEL"] = args.log_level

    server = create_server(args.config)
    server.run()


if __name__ == "__main__":
    main()


# Create a default server instance for FastMCP to discover
_default_config = load_config()
setup_logging(_default_config.logging)
_server_instance = TextualMCPServer(_default_config)
server = _server_instance.mcp
