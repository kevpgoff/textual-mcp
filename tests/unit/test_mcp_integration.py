"""Integration tests for MCP tools using FastMCP Client."""

import pytest
from fastmcp import Client

from textual_mcp.server import TextualMCPServer


class TestMCPIntegration:
    """Test MCP tools through FastMCP Client interface."""

    @pytest.mark.asyncio
    async def test_server_with_client(self, mcp_server: TextualMCPServer):
        """Test basic server connection with client."""
        async with Client(mcp_server.mcp) as client:
            # Client should connect successfully
            assert client is not None

    @pytest.mark.asyncio
    async def test_validate_css_tool(self, mcp_client: Client):
        """Test validate_tcss tool through MCP client."""
        async with mcp_client as client:
            # Valid CSS
            result = await client.call_tool(
                "validate_tcss",
                {
                    "css_content": """
                    Button {
                        background: $primary;
                        color: white;
                        padding: 1 2;
                    }
                    """
                },
            )

            assert result.data["valid"] is True
            assert len(result.data["errors"]) == 0
            assert "stats" in result.data
            assert result.data["stats"]["rule_count"] > 0
            assert result.data["stats"]["selector_count"] > 0
            assert "summary" in result.data

    @pytest.mark.asyncio
    async def test_validate_css_file_tool(self, mcp_client: Client, sample_css_file):
        """Test validate_tcss_file tool through MCP client."""
        async with mcp_client as client:
            result = await client.call_tool(
                "validate_tcss_file", {"file_path": str(sample_css_file)}
            )

            assert result.data["valid"] is True
            assert len(result.data["errors"]) == 0

    @pytest.mark.asyncio
    async def test_validate_css_file_not_found(self, mcp_client: Client):
        """Test validate_tcss_file with non-existent file."""
        async with mcp_client as client:
            result = await client.call_tool(
                "validate_tcss_file", {"file_path": "/nonexistent/file.tcss"}
            )

            assert result.data["valid"] is False
            assert len(result.data["errors"]) > 0
            assert "not found" in result.data["errors"][0]["message"].lower()

    @pytest.mark.asyncio
    async def test_validate_inline_styles_tool(self, mcp_client: Client):
        """Test validate_inline_styles tool through MCP client."""
        async with mcp_client as client:
            result = await client.call_tool(
                "validate_inline_styles",
                {"style_string": "color: red; background: blue; padding: 1 2;"},
            )

            assert result.data["valid"] is True
            assert len(result.data["errors"]) == 0
            assert isinstance(result.data["warnings"], list)

    @pytest.mark.asyncio
    async def test_validate_inline_styles_invalid(self, mcp_client: Client):
        """Test validate_inline_styles with invalid styles."""
        async with mcp_client as client:
            result = await client.call_tool(
                "validate_inline_styles",
                {"style_string": "invalid-property: value; color: ;"},
            )

            # Should still return results but with errors
            assert result.data["valid"] is False
            assert len(result.data["errors"]) > 0 or len(result.data["warnings"]) > 0

    @pytest.mark.asyncio
    async def test_validate_selector_tool(self, mcp_client: Client):
        """Test check_selector tool through MCP client."""
        # Valid selectors
        valid_selectors = [
            "Button",
            ".custom-class",
            "#unique-id",
            "Button.active",
            "Container Button",  # Descendant selector instead of child combinator
        ]

        async with mcp_client as client:
            for selector in valid_selectors:
                result = await client.call_tool(
                    "check_selector", {"selector": selector}
                )

                assert result.data["valid"] is True
                assert result.data["selector"] == selector
                assert "type" in result.data

    @pytest.mark.asyncio
    async def test_generate_widget_tool(self, mcp_client: Client):
        """Test generate_widget tool through MCP client."""
        async with mcp_client as client:
            result = await client.call_tool(
                "generate_widget",
                {
                    "widget_name": "MyCustomWidget",
                    "widget_type": "container",
                    "includes_css": True,
                    "event_handlers": ["click", "mount"],
                },
            )

            assert "python_code" in result.data
            assert "css_code" in result.data
            assert "usage_example" in result.data
            assert "widget_info" in result.data

            # Check widget info
            widget_info = result.data["widget_info"]
            assert widget_info["name"] == "MyCustomWidget"
            assert widget_info["type"] == "container"
            assert widget_info["includes_css"] is True
            assert "click" in widget_info["event_handlers"]
            assert "mount" in widget_info["event_handlers"]

            # Check generated code content
            assert "class MyCustomWidget(Widget):" in result.data["python_code"]
            assert "MyCustomWidget {" in result.data["css_code"]
            assert (
                "from your_module import MyCustomWidget" in result.data["usage_example"]
            )

    @pytest.mark.asyncio
    async def test_generate_widget_invalid_name(self, mcp_client: Client):
        """Test generate_widget with invalid widget name."""
        async with mcp_client as client:
            with pytest.raises(Exception) as exc_info:
                await client.call_tool(
                    "generate_widget",
                    {
                        "widget_name": "invalid_name",  # Should start with uppercase
                        "widget_type": "container",
                    },
                )

            # The error comes from Pydantic validation on the pattern field
            error_msg = str(exc_info.value)
            assert "does not match" in error_msg and "^[A-Z][a-zA-Z0-9]*$" in error_msg

    @pytest.mark.asyncio
    async def test_list_widget_types_tool(self, mcp_client: Client):
        """Test list_widget_types tool through MCP client."""
        async with mcp_client as client:
            result = await client.call_tool("list_widget_types", {})

            assert "widgets" in result.data
            assert "widget_info" in result.data
            assert "categorized" in result.data
            assert "total_count" in result.data

            # Check some expected widgets
            widgets = result.data["widgets"]
            assert "Button" in widgets
            assert "Label" in widgets
            assert "Input" in widgets

            # Check categorization
            categories = result.data["categorized"]
            assert "input" in categories
            assert "display" in categories
            assert "container" in categories

    @pytest.mark.asyncio
    async def test_list_event_handlers_tool(self, mcp_client: Client):
        """Test list_event_handlers tool through MCP client."""
        async with mcp_client as client:
            result = await client.call_tool("list_event_handlers", {})

            assert "event_handlers" in result.data
            assert "descriptions" in result.data
            assert "count" in result.data

            handlers = result.data["event_handlers"]
            assert "click" in handlers
            assert "key_press" in handlers
            assert "input_changed" in handlers

            # Check descriptions
            descriptions = result.data["descriptions"]
            assert descriptions["click"] == "Handle button click events"

    @pytest.mark.asyncio
    async def test_validate_widget_name_tool(self, mcp_client: Client):
        """Test validate_widget_name tool through MCP client."""
        async with mcp_client as client:
            # Valid name
            result = await client.call_tool(
                "validate_widget_name", {"widget_name": "MyWidget"}
            )

            assert result.data["valid"] is True
            assert result.data["widget_name"] == "MyWidget"
            assert result.data["error"] is None

            # Invalid name
            result = await client.call_tool(
                "validate_widget_name",
                {"widget_name": "myWidget"},  # Lowercase start
            )

            assert result.data["valid"] is False
            assert result.data["error"] is not None
            assert len(result.data["suggestions"]) > 0

    @pytest.mark.asyncio
    async def test_suggest_layout_tool(self, mcp_client: Client):
        """Test generate_grid_layout tool through MCP client."""
        async with mcp_client as client:
            result = await client.call_tool(
                "generate_grid_layout",
                {
                    "rows": 3,
                    "columns": 3,
                },
            )

            assert "example_html" in result.data
            assert "css" in result.data
            assert "grid" in result.data["css"]

    @pytest.mark.asyncio
    async def test_analyze_layout_tool(self, mcp_client: Client):
        """Test analyze_selectors tool through MCP client."""
        async with mcp_client as client:
            css_content = """
            Button {
                color: red;
            }
            .custom {
                background: blue;
            }
            """

            result = await client.call_tool(
                "analyze_selectors", {"css_content": css_content}
            )

            assert "selectors" in result.data
            assert "recommendations" in result.data

    @pytest.mark.asyncio
    async def test_tool_error_handling(self, mcp_client: Client):
        """Test error handling for tool execution."""
        async with mcp_client as client:
            # Test with missing required parameter
            with pytest.raises(Exception) as exc_info:
                await client.call_tool("validate_tcss", {})  # Missing 'css_content'

            # Should raise an error about missing parameter
            assert (
                "css_content" in str(exc_info.value).lower()
                or "required" in str(exc_info.value).lower()
            )

    @pytest.mark.asyncio
    async def test_multiple_tool_calls(self, mcp_client: Client):
        """Test making multiple tool calls in sequence."""
        async with mcp_client as client:
            # First validate a widget name
            name_result = await client.call_tool(
                "validate_widget_name", {"widget_name": "TestWidget"}
            )
            assert name_result.data["valid"] is True

            # Then generate the widget
            widget_result = await client.call_tool(
                "generate_widget",
                {
                    "widget_name": "TestWidget",
                    "widget_type": "container",
                    "includes_css": True,
                },
            )
            assert "python_code" in widget_result.data

            # Finally validate the generated CSS
            css_result = await client.call_tool(
                "validate_tcss", {"css_content": widget_result.data["css_code"]}
            )
            assert css_result.data["valid"] is True

    @pytest.mark.asyncio
    async def test_analysis_tools_placeholder(self, mcp_client: Client):
        """Test analysis tools (currently have TODO implementations)."""
        async with mcp_client as client:
            # These tools currently return placeholder responses

            # Test analyze_selectors
            result = await client.call_tool(
                "analyze_selectors", {"css_content": "Button { color: red; }"}
            )
            assert "selectors" in result.data
            assert "recommendations" in result.data

            # Test extract_css_variables
            result = await client.call_tool(
                "extract_css_variables", {"css_content": ":root { --primary: blue; }"}
            )
            assert "variables" in result.data

            # Test detect_style_conflicts
            result = await client.call_tool(
                "detect_style_conflicts",
                {"css_content": "Button { color: red; } Button { color: blue; }"},
            )
            assert "conflicts" in result.data
