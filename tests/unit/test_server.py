"""Tests for the TextualMCPServer class."""

import pytest
from unittest.mock import patch, MagicMock
import asyncio

from textual_mcp.server import TextualMCPServer, create_server, main
from textual_mcp.config import TextualMCPConfig
from textual_mcp.utils.errors import ConfigurationError


class TestTextualMCPServer:
    """Test cases for TextualMCPServer."""

    def test_server_initialization(self, test_config: TextualMCPConfig):
        """Test server initialization with configuration."""
        server = TextualMCPServer(test_config)

        assert server.config == test_config
        assert server.mcp is not None
        assert server.logger is not None

    def test_server_tool_registration(self, test_config: TextualMCPConfig):
        """Test that all tools are registered properly."""
        server = TextualMCPServer(test_config)

        # Check that tools are registered (FastMCP stores them internally)
        # We can't directly access the tools, but we can verify no errors occurred
        assert server.mcp is not None

    @patch("textual_mcp.server.register_validation_tools")
    def test_tool_registration_failure(self, mock_register, test_config: TextualMCPConfig):
        """Test server behavior when tool registration fails."""
        mock_register.side_effect = Exception("Registration failed")

        with pytest.raises(ConfigurationError) as exc_info:
            TextualMCPServer(test_config)

        assert "Tool registration failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_server_start(self, test_config: TextualMCPConfig):
        """Test server start method."""
        server = TextualMCPServer(test_config)

        # Mock the run method to avoid actually starting the server
        with patch.object(server.mcp, "run", new_callable=MagicMock) as mock_run:
            mock_run.return_value = asyncio.Future()
            mock_run.return_value.set_result(None)

            await server.start()
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_server_start_failure(self, test_config: TextualMCPConfig):
        """Test server behavior when start fails."""
        server = TextualMCPServer(test_config)

        # Mock the run method to raise an exception
        with patch.object(server.mcp, "run", side_effect=Exception("Start failed")):
            with pytest.raises(Exception) as exc_info:
                await server.start()

            assert "Start failed" in str(exc_info.value)

    def test_server_run_keyboard_interrupt(self, test_config: TextualMCPConfig):
        """Test server behavior on keyboard interrupt."""
        server = TextualMCPServer(test_config)

        with patch("asyncio.run", side_effect=KeyboardInterrupt()):
            # Should exit gracefully without raising
            server.run()

    def test_server_run_exception(self, test_config: TextualMCPConfig):
        """Test server behavior on general exception."""
        server = TextualMCPServer(test_config)

        with patch("asyncio.run", side_effect=Exception("Runtime error")):
            with patch("sys.exit") as mock_exit:
                server.run()
                mock_exit.assert_called_once_with(1)


class TestCreateServer:
    """Test cases for create_server function."""

    def test_create_server_default_config(self):
        """Test creating server with default configuration."""
        with patch("textual_mcp.server.load_config") as mock_load:
            mock_load.return_value = TextualMCPConfig()

            server = create_server()

            assert isinstance(server, TextualMCPServer)
            mock_load.assert_called_once_with(None)

    def test_create_server_custom_config_path(self):
        """Test creating server with custom config path."""
        config_path = "/custom/config.yaml"

        with patch("textual_mcp.server.load_config") as mock_load:
            mock_load.return_value = TextualMCPConfig()

            server = create_server(config_path)

            assert isinstance(server, TextualMCPServer)
            mock_load.assert_called_once_with(config_path)

    def test_create_server_failure(self):
        """Test create_server behavior on failure."""
        with patch("textual_mcp.server.load_config", side_effect=Exception("Config error")):
            with patch("sys.exit") as mock_exit:
                with patch("builtins.print") as mock_print:
                    create_server()

                    mock_print.assert_called_once()
                    assert "Failed to create server" in mock_print.call_args[0][0]
                    mock_exit.assert_called_once_with(1)


class TestMain:
    """Test cases for main entry point."""

    def test_main_default_args(self):
        """Test main function with default arguments."""
        test_args = ["server.py"]

        with patch("sys.argv", test_args):
            with patch("textual_mcp.server.create_server") as mock_create:
                mock_server = MagicMock()
                mock_create.return_value = mock_server

                main()

                mock_create.assert_called_once_with(None)
                mock_server.run.assert_called_once()

    def test_main_with_config(self):
        """Test main function with config argument."""
        test_args = ["server.py", "--config", "/path/to/config.yaml"]

        with patch("sys.argv", test_args):
            with patch("textual_mcp.server.create_server") as mock_create:
                mock_server = MagicMock()
                mock_create.return_value = mock_server

                main()

                mock_create.assert_called_once_with("/path/to/config.yaml")
                mock_server.run.assert_called_once()

    def test_main_with_log_level(self):
        """Test main function with log level argument."""
        test_args = ["server.py", "--log-level", "DEBUG"]

        with patch("sys.argv", test_args):
            with patch("textual_mcp.server.create_server") as mock_create:
                with patch("os.environ", {}) as mock_env:
                    mock_server = MagicMock()
                    mock_create.return_value = mock_server

                    main()

                    assert mock_env["LOG_LEVEL"] == "DEBUG"
                    mock_create.assert_called_once_with(None)
                    mock_server.run.assert_called_once()

    def test_main_with_version(self):
        """Test main function with version argument."""
        test_args = ["server.py", "--version"]

        with patch("sys.argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # argparse exits with 0 for --version
            assert exc_info.value.code == 0


class TestModuleLevel:
    """Test module-level code."""

    def test_default_server_instance(self):
        """Test that default server instance is created at module level."""
        # Import the module to trigger module-level code
        import textual_mcp.server as server_module

        # The module should have a 'server' variable for FastMCP
        assert hasattr(server_module, "server")
        assert server_module.server is not None

        # It should also have the private _server_instance
        assert hasattr(server_module, "_server_instance")
        assert isinstance(server_module._server_instance, TextualMCPServer)
