"""Integration tests for conflict detection in analysis tools."""

import pytest

from textual_mcp.tools.analysis_tools import register_analysis_tools
from textual_mcp.config import TextualMCPConfig


class MockMCP:
    """Mock MCP server for testing tools."""

    def __init__(self):
        self.tools = {}

    def tool(self):
        """Decorator to register tools."""

        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


class TestDetectStyleConflictsTool:
    """Test the detect_style_conflicts MCP tool."""

    @pytest.fixture
    def mcp_with_tools(self, test_config: TextualMCPConfig) -> MockMCP:
        """Create mock MCP with analysis tools registered."""
        mcp = MockMCP()
        register_analysis_tools(mcp, test_config)
        return mcp

    @pytest.mark.asyncio
    async def test_detect_simple_conflicts(self, mcp_with_tools: MockMCP):
        """Test detection of simple CSS conflicts via the tool."""
        tool = mcp_with_tools.tools["detect_style_conflicts"]

        css_content = """
        Button {
            color: red;
            background: blue;
            margin: 1 2;
        }

        Button {
            color: green;
            padding: 2;
        }
        """

        result = await tool(css_content)

        assert isinstance(result, dict)
        assert "conflicts" in result
        assert "overlapping_selectors" in result
        assert "resolution_suggestions" in result
        assert "summary" in result

        # Check summary
        assert result["summary"]["total_conflicts"] > 0
        assert result["summary"]["has_issues"] is True

        # Check conflicts
        assert len(result["conflicts"]) > 0
        conflict = result["conflicts"][0]
        assert "selector1" in conflict
        assert "selector2" in conflict
        assert "conflicting_properties" in conflict
        assert "color" in conflict["conflicting_properties"]

    @pytest.mark.asyncio
    async def test_detect_overlapping_selectors(self, mcp_with_tools: MockMCP):
        """Test detection of overlapping selectors."""
        tool = mcp_with_tools.tools["detect_style_conflicts"]

        css_content = """
        Button {
            color: red;
        }

        Button.primary {
            background: blue;
        }

        Button.secondary {
            background: green;
        }

        Label {
            color: black;
        }

        Label.title {
            font-size: 2rem;
        }
        """

        result = await tool(css_content)

        # Should detect Button group (Label group may not have conflicts)
        assert len(result["overlapping_selectors"]) >= 1

        # Check for Button overlap group
        button_group = next(
            (g for g in result["overlapping_selectors"] if "Button" in g["selectors"]), None
        )
        assert button_group is not None
        assert button_group["overlap_type"] in ["subset", "partial"]

    @pytest.mark.asyncio
    async def test_specificity_issues(self, mcp_with_tools: MockMCP):
        """Test detection of specificity issues."""
        tool = mcp_with_tools.tools["detect_style_conflicts"]

        css_content = """
        #main #content .container Button.primary.active {
            color: red;
        }

        #id1 #id2 {
            background: blue;
        }

        .simple {
            color: green;
        }
        """

        result = await tool(css_content)

        assert "specificity_issues" in result
        assert len(result["specificity_issues"]) > 0

        # Check for high specificity issues
        high_spec = [issue for issue in result["specificity_issues"] if issue["score"] > 5]
        assert len(high_spec) > 0

    @pytest.mark.asyncio
    async def test_property_conflict_categorization(self, mcp_with_tools: MockMCP):
        """Test categorization of property conflicts."""
        tool = mcp_with_tools.tools["detect_style_conflicts"]

        css_content = """
        Button {
            /* Spacing conflicts */
            margin: 1 2;
            padding: 2 3;

            /* Color conflicts */
            color: red;
            background: blue;

            /* Sizing conflicts */
            width: 100%;
            height: 3;

            /* Positioning conflicts */
            dock: top;
        }

        Button.primary {
            margin-top: 3;
            padding: 4;
            color: white;
            background: green;
            width: 80%;
            height: 4;
            dock: bottom;
        }
        """

        result = await tool(css_content)

        assert "property_conflicts" in result
        categories = result["property_conflicts"]

        # Check that conflicts are properly categorized
        assert "spacing" in categories
        assert "colors" in categories
        assert "sizing" in categories
        assert "positioning" in categories

    @pytest.mark.asyncio
    async def test_resolution_suggestions(self, mcp_with_tools: MockMCP):
        """Test that resolution suggestions are provided."""
        tool = mcp_with_tools.tools["detect_style_conflicts"]

        css_content = """
        Button {
            color: red;
        }

        Button {
            color: blue;
        }

        #id1 {
            background: white;
        }

        #id1 {
            background: black;
        }
        """

        result = await tool(css_content)

        assert len(result["resolution_suggestions"]) > 0

        # Check individual conflict resolutions
        for conflict in result["conflicts"]:
            assert "resolution" in conflict
            assert conflict["resolution"] is not None

    @pytest.mark.asyncio
    async def test_empty_css(self, mcp_with_tools: MockMCP):
        """Test handling of empty CSS content."""
        tool = mcp_with_tools.tools["detect_style_conflicts"]

        result = await tool("")

        assert result["summary"]["total_conflicts"] == 0
        assert result["summary"]["has_issues"] is False
        assert len(result["conflicts"]) == 0
        assert len(result["overlapping_selectors"]) == 0

    @pytest.mark.asyncio
    async def test_textual_specific_properties(self, mcp_with_tools: MockMCP):
        """Test conflict detection with Textual-specific properties."""
        tool = mcp_with_tools.tools["detect_style_conflicts"]

        css_content = """
        Screen {
            layers: base overlay;
            dock: top;
            offset: 1 2;
        }

        Screen {
            layers: overlay popup;
            dock: bottom;
            offset-x: 3;
        }

        Button {
            tint: $primary 50%;
            content-align: center middle;
        }

        Button.highlighted {
            tint: $accent 75%;
            content-align: left top;
        }
        """

        result = await tool(css_content)

        # Should detect Textual-specific property conflicts
        assert result["summary"]["total_conflicts"] > 0

        # Check that Textual properties are in conflicts
        all_conflicting_props = []
        for conflict in result["conflicts"]:
            all_conflicting_props.extend(conflict["conflicting_properties"])

        textual_props = {"dock", "offset", "tint", "content-align", "layers", "offset-x"}
        assert any(prop in all_conflicting_props for prop in textual_props)

    @pytest.mark.asyncio
    async def test_large_css_performance(self, mcp_with_tools: MockMCP):
        """Test performance with larger CSS files."""
        tool = mcp_with_tools.tools["detect_style_conflicts"]

        # Generate a larger CSS file with potential conflicts
        css_parts = []
        for i in range(50):
            css_parts.append(f"""
            .class{i} {{
                color: #{i:06x};
                margin: {i} {i * 2};
                padding: {i // 2};
            }}

            Button.class{i} {{
                color: #{(i + 1):06x};
                margin-top: {i + 1};
            }}
            """)

        css_content = "\n".join(css_parts)

        # Should complete without timing out
        result = await tool(css_content)

        assert isinstance(result, dict)
        assert "summary" in result
        # With 50 classes and overlaps, should find some issues
        assert result["summary"]["total_overlaps"] > 0

    @pytest.mark.asyncio
    async def test_error_handling(self, mcp_with_tools: MockMCP):
        """Test error handling in the tool."""
        tool = mcp_with_tools.tools["detect_style_conflicts"]

        # Even with potentially problematic CSS, tool should not crash
        css_content = """
        Button {
            color: ;
            background: invalid;
            ;;;
        }

        {
            property: value;
        }
        """

        # Should handle gracefully
        try:
            result = await tool(css_content)
            assert isinstance(result, dict)
            assert "summary" in result
        except Exception as e:
            # If it does throw, should be a ToolExecutionError
            assert "Style conflict detection failed" in str(e)
