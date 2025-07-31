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
from textual_mcp.tools.documentation_tools import register_documentation_tools


class TextualMCPServer:
    """Main Textual MCP Server class."""

    def __init__(self, config: TextualMCPConfig):
        self.config = config
        self.logger = get_logger("server")

        # Initialize FastMCP server
        self.mcp: Any = FastMCP(
            name="Textual Development Assistant",
            version="1.0.0",
        )

        # Register all tools
        self._register_tools()

        self.logger.info("Textual MCP Server initialized")

    def _register_tools(self) -> None:
        """Register all MCP tools."""
        try:
            # Register validation tools
            register_validation_tools(self.mcp, self.config)
            self.logger.info("Registered validation tools")

            # Register analysis tools
            register_analysis_tools(self.mcp, self.config)
            self.logger.info("Registered analysis tools")

            # Register widget tools
            register_widget_tools(self.mcp, self.config)
            self.logger.info("Registered widget tools")

            # Register layout tools
            register_layout_tools(self.mcp, self.config)
            self.logger.info("Registered layout tools")

            # Register documentation tools
            register_documentation_tools(self.mcp, self.config)
            self.logger.info("Registered documentation tools")

        except Exception as e:
            self.logger.error(f"Failed to register tools: {e}")
            raise ConfigurationError(f"Tool registration failed: {e}")

    async def start(self) -> None:
        """Start the MCP server."""
        try:
            self.logger.info("Starting Textual MCP Server...")
            await self.mcp.run()  # type: ignore[func-returns-value]
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
        # Load configuration
        config = load_config(config_path)

        # Setup logging
        setup_logging(config.logging)

        # Create server
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
    parser.add_argument(
        "--version", action="version", version="Textual MCP Server 1.0.0"
    )

    args = parser.parse_args()

    # Override log level if specified
    if args.log_level:
        import os

        os.environ["LOG_LEVEL"] = args.log_level

    # Create and run server
    server = create_server(args.config)
    server.run()


if __name__ == "__main__":
    main()


# Create a default server instance for FastMCP to discover
# This is what FastMCP CLI looks for when using `fastmcp dev`
_default_config = load_config()
setup_logging(_default_config.logging)
_server_instance = TextualMCPServer(_default_config)
server = _server_instance.mcp  # FastMCP expects a 'server' variable
