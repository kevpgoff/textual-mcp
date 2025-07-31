"""Tests for widget tools module."""

import pytest
from unittest.mock import patch, MagicMock

from textual_mcp.tools.widget_tools import register_widget_tools
from textual_mcp.config import TextualMCPConfig
from textual_mcp.utils.errors import ToolExecutionError


class TestWidgetTools:
    """Test widget tool registration and functionality."""

    def test_register_widget_tools(self, test_config: TextualMCPConfig):
        """Test that widget tools are registered correctly."""
        mock_mcp = MagicMock()

        # Register tools
        register_widget_tools(mock_mcp, test_config)

        # Check that tool decorator was called for each tool
        assert mock_mcp.tool.called
        # Should register 4 tools: generate_widget, list_widget_types,
        # list_event_handlers, validate_widget_name
        assert mock_mcp.tool.call_count >= 4

    @pytest.mark.asyncio
    async def test_generate_widget_tool_logic(self, test_config: TextualMCPConfig):
        """Test the generate_widget tool implementation logic."""
        mock_mcp = MagicMock()
        registered_tools = {}

        # Capture registered tools
        def tool_decorator():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = tool_decorator

        # Register tools
        register_widget_tools(mock_mcp, test_config)

        # Test generate_widget
        generate_widget = registered_tools["generate_widget"]

        # Test widget generation
        result = await generate_widget(
            widget_name="TestWidget",
            widget_type="container",
            includes_css=True,
            event_handlers=["click", "mount"],
        )

        assert "python_code" in result
        assert "css_code" in result
        assert "usage_example" in result
        assert "widget_info" in result

        # Check widget info
        widget_info = result["widget_info"]
        assert widget_info["name"] == "TestWidget"
        assert widget_info["type"] == "container"
        assert widget_info["includes_css"] is True
        assert "click" in widget_info["event_handlers"]
        assert "mount" in widget_info["event_handlers"]
        assert widget_info["generation_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_generate_widget_no_css(self, test_config: TextualMCPConfig):
        """Test generate_widget without CSS."""
        mock_mcp = MagicMock()
        registered_tools = {}

        def tool_decorator():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = tool_decorator
        register_widget_tools(mock_mcp, test_config)

        generate_widget = registered_tools["generate_widget"]

        result = await generate_widget(
            widget_name="NoCSSWidget", widget_type="input", includes_css=False
        )

        assert result["css_code"] == ""
        assert result["widget_info"]["includes_css"] is False

    @pytest.mark.asyncio
    async def test_generate_widget_error_handling(self, test_config: TextualMCPConfig):
        """Test error handling in generate_widget tool."""
        mock_mcp = MagicMock()
        registered_tools = {}

        def tool_decorator():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = tool_decorator
        register_widget_tools(mock_mcp, test_config)

        generate_widget = registered_tools["generate_widget"]

        # Test with invalid widget name
        with pytest.raises(ToolExecutionError) as exc_info:
            await generate_widget(
                widget_name="invalid_name",  # Should start with uppercase
                widget_type="container",
            )

        assert "Widget generation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_widget_types_tool_logic(self, test_config: TextualMCPConfig):
        """Test the list_widget_types tool implementation logic."""
        mock_mcp = MagicMock()
        registered_tools = {}

        def tool_decorator():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = tool_decorator
        register_widget_tools(mock_mcp, test_config)

        list_widget_types = registered_tools["list_widget_types"]

        # Test listing widget types
        result = await list_widget_types()

        assert "widgets" in result
        assert "widget_info" in result
        assert "categorized" in result
        assert "total_count" in result
        assert result["source"] == "textual.widgets"

        # Check that we have some widgets
        assert len(result["widgets"]) > 0
        assert result["total_count"] > 0

        # Check categorization
        categories = result["categorized"]
        assert "input" in categories
        assert "display" in categories
        assert "container" in categories
        assert "interactive" in categories
        assert "navigation" in categories
        assert "other" in categories

    @pytest.mark.asyncio
    async def test_list_widget_types_with_mock(self, test_config: TextualMCPConfig):
        """Test list_widget_types with mocked textual.widgets."""
        mock_mcp = MagicMock()
        registered_tools = {}

        def tool_decorator():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = tool_decorator
        register_widget_tools(mock_mcp, test_config)

        list_widget_types = registered_tools["list_widget_types"]

        # Mock textual.widgets - import happens inside the function
        with patch("textual.widgets") as mock_tw:
            # Create mock widget classes
            class MockButton:
                """A button widget"""

                pass

            class MockInput:
                """An input widget"""

                pass

            # Set up __all__ attribute
            mock_tw.__all__ = ["Button", "Input"]
            mock_tw.Button = MockButton
            mock_tw.Input = MockInput

            # Mock inspect functions
            with patch(
                "textual_mcp.tools.widget_tools.inspect.isclass", return_value=True
            ):
                with patch(
                    "textual_mcp.tools.widget_tools.inspect.getdoc"
                ) as mock_getdoc:
                    mock_getdoc.side_effect = lambda obj: obj.__doc__

                    result = await list_widget_types()

            assert "Button" in result["widgets"]
            assert "Input" in result["widgets"]
            assert result["widget_info"]["Button"] == "A button widget"
            assert result["widget_info"]["Input"] == "An input widget"

    @pytest.mark.asyncio
    async def test_list_event_handlers_tool_logic(self, test_config: TextualMCPConfig):
        """Test the list_event_handlers tool implementation logic."""
        mock_mcp = MagicMock()
        registered_tools = {}

        def tool_decorator():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = tool_decorator
        register_widget_tools(mock_mcp, test_config)

        list_event_handlers = registered_tools["list_event_handlers"]

        # Test listing event handlers
        result = await list_event_handlers()

        assert "event_handlers" in result
        assert "descriptions" in result
        assert "count" in result

        # Check expected handlers
        handlers = result["event_handlers"]
        assert "click" in handlers
        assert "key_press" in handlers
        assert "input_changed" in handlers
        assert "focus" in handlers
        assert "blur" in handlers
        assert "mount" in handlers
        assert "default" in handlers

        # Check descriptions
        descriptions = result["descriptions"]
        assert descriptions["click"] == "Handle button click events"
        assert descriptions["key_press"] == "Handle keyboard key press events"
        assert descriptions["input_changed"] == "Handle input field value changes"

        # Check count
        assert result["count"] == len(handlers)

    @pytest.mark.asyncio
    async def test_validate_widget_name_tool_logic(self, test_config: TextualMCPConfig):
        """Test the validate_widget_name tool implementation logic."""
        mock_mcp = MagicMock()
        registered_tools = {}

        def tool_decorator():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = tool_decorator
        register_widget_tools(mock_mcp, test_config)

        validate_widget_name = registered_tools["validate_widget_name"]

        # Test valid widget name
        result = await validate_widget_name(widget_name="MyWidget")

        assert result["valid"] is True
        assert result["widget_name"] == "MyWidget"
        assert result["error"] is None
        assert result["suggestions"] == []

        # Test invalid widget name - lowercase start
        result = await validate_widget_name(widget_name="myWidget")

        assert result["valid"] is False
        assert result["error"] is not None
        assert len(result["suggestions"]) > 0
        assert (
            "Mywidget" in result["suggestions"][0]
            or "MyWidget" in result["suggestions"][0]
        )

        # Test empty widget name
        result = await validate_widget_name(widget_name="")

        assert result["valid"] is False
        assert result["error"] is not None
        assert len(result["suggestions"]) > 0
        assert "Widget name cannot be empty" in result["suggestions"][0]

        # Test widget name with invalid characters
        result = await validate_widget_name(widget_name="My-Widget")

        assert result["valid"] is False
        assert result["error"] is not None
        assert len(result["suggestions"]) > 0
        assert "MyWidget" in result["suggestions"][0]

        # Test widget name starting with number
        result = await validate_widget_name(widget_name="123Widget")

        assert result["valid"] is False
        assert result["error"] is not None
        assert len(result["suggestions"]) > 0
        assert "Widget123Widget" in result["suggestions"][0]

    @pytest.mark.asyncio
    async def test_tool_error_handling_list_widgets(
        self, test_config: TextualMCPConfig
    ):
        """Test error handling in list_widget_types tool."""
        mock_mcp = MagicMock()
        registered_tools = {}

        def tool_decorator():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = tool_decorator
        register_widget_tools(mock_mcp, test_config)

        list_widget_types = registered_tools["list_widget_types"]

        # Mock textual.widgets import to raise an exception
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "textual.widgets":
                raise ImportError("Module error")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=mock_import):
            with pytest.raises(ToolExecutionError) as exc_info:
                await list_widget_types()

            assert "Failed to list widget types" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_tool_logging(self, test_config: TextualMCPConfig):
        """Test that widget tools log their execution."""
        mock_mcp = MagicMock()
        registered_tools = {}

        def tool_decorator():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = tool_decorator

        with patch(
            "textual_mcp.tools.widget_tools.log_tool_execution"
        ) as mock_log_exec:
            with patch(
                "textual_mcp.tools.widget_tools.log_tool_completion"
            ) as mock_log_complete:
                register_widget_tools(mock_mcp, test_config)

                # Execute a tool
                generate_widget = registered_tools["generate_widget"]

                await generate_widget(widget_name="TestWidget", widget_type="container")

                # Check logging was called
                mock_log_exec.assert_called_once()
                mock_log_complete.assert_called_once()

                # Check log parameters
                exec_call = mock_log_exec.call_args
                assert exec_call[0][0] == "generate_widget"
                assert exec_call[0][1]["widget_name"] == "TestWidget"
                assert exec_call[0][1]["widget_type"] == "container"

                complete_call = mock_log_complete.call_args
                assert complete_call[0][0] == "generate_widget"
                assert complete_call[0][1] is True  # Success
                assert complete_call[0][2] > 0  # Duration
