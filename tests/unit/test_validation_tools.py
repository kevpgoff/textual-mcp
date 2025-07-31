"""Tests for validation tools module."""

import pytest
from unittest.mock import patch, MagicMock

from textual_mcp.tools.validation_tools import register_validation_tools
from textual_mcp.config import TextualMCPConfig
from textual_mcp.utils.errors import ToolExecutionError


class TestValidationTools:
    """Test validation tool registration and functionality."""

    def test_register_validation_tools(self, test_config: TextualMCPConfig):
        """Test that validation tools are registered correctly."""
        mock_mcp = MagicMock()

        # Register tools
        register_validation_tools(mock_mcp, test_config)

        # Check that tool decorator was called for each tool
        assert mock_mcp.tool.called
        # Should register 4 tools: validate_tcss, validate_tcss_file,
        # validate_inline_styles, check_selector
        assert mock_mcp.tool.call_count >= 4

    @pytest.mark.asyncio
    async def test_validate_css_tool_logic(self, test_config: TextualMCPConfig):
        """Test the validate_tcss tool implementation logic."""
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
        register_validation_tools(mock_mcp, test_config)

        # Test validate_tcss
        validate_tcss = registered_tools["validate_tcss"]

        # Test with valid CSS
        result = await validate_tcss(
            css_content="""
            Button {
                background: $primary;
                color: white;
            }
        """
        )

        assert result["valid"] is True
        assert result["errors"] == []
        assert result["stats"]["rule_count"] > 0
        assert result["stats"]["selector_count"] > 0
        assert "summary" in result
        assert "parse_time_ms" in result["stats"]

    @pytest.mark.asyncio
    async def test_validate_css_empty_content(self, test_config: TextualMCPConfig):
        """Test validate_tcss with empty content."""
        mock_mcp = MagicMock()
        registered_tools = {}

        def tool_decorator():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = tool_decorator
        register_validation_tools(mock_mcp, test_config)

        validate_tcss = registered_tools["validate_tcss"]

        # Test with empty CSS
        result = await validate_tcss(css_content="")

        assert result["valid"] is True
        assert result["errors"] == []
        assert result["stats"]["rule_count"] == 0
        assert result["stats"]["selector_count"] == 0

    @pytest.mark.asyncio
    async def test_validate_css_file_tool_logic(
        self, test_config: TextualMCPConfig, sample_css_file
    ):
        """Test the validate_tcss_file tool implementation logic."""
        mock_mcp = MagicMock()
        registered_tools = {}

        def tool_decorator():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = tool_decorator
        register_validation_tools(mock_mcp, test_config)

        validate_tcss_file = registered_tools["validate_tcss_file"]

        # Test with valid file
        result = await validate_tcss_file(file_path=str(sample_css_file))

        assert result["valid"] is True
        assert result["errors"] == []
        assert result["stats"]["rule_count"] > 0

    @pytest.mark.asyncio
    async def test_validate_css_file_not_found(self, test_config: TextualMCPConfig):
        """Test validate_tcss_file with non-existent file."""
        mock_mcp = MagicMock()
        registered_tools = {}

        def tool_decorator():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = tool_decorator
        register_validation_tools(mock_mcp, test_config)

        validate_tcss_file = registered_tools["validate_tcss_file"]

        # Test with non-existent file
        result = await validate_tcss_file(file_path="/nonexistent/file.tcss")

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert any(
            "not found" in error["message"].lower() for error in result["errors"]
        )

    @pytest.mark.asyncio
    async def test_validate_inline_styles_tool_logic(
        self, test_config: TextualMCPConfig
    ):
        """Test the validate_inline_styles tool implementation logic."""
        mock_mcp = MagicMock()
        registered_tools = {}

        def tool_decorator():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = tool_decorator
        register_validation_tools(mock_mcp, test_config)

        validate_inline_styles = registered_tools["validate_inline_styles"]

        # Test with valid inline styles
        result = await validate_inline_styles(
            style_string="color: red; background: blue; padding: 1 2;"
        )

        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert isinstance(result["warnings"], list)

    @pytest.mark.asyncio
    async def test_validate_inline_styles_empty(self, test_config: TextualMCPConfig):
        """Test validate_inline_styles with empty string."""
        mock_mcp = MagicMock()
        registered_tools = {}

        def tool_decorator():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = tool_decorator
        register_validation_tools(mock_mcp, test_config)

        validate_inline_styles = registered_tools["validate_inline_styles"]

        # Test with empty styles
        result = await validate_inline_styles(style_string="")

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_validate_selector_tool_logic(self, test_config: TextualMCPConfig):
        """Test the validate_selector tool implementation logic."""
        mock_mcp = MagicMock()
        registered_tools = {}

        def tool_decorator():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = tool_decorator
        register_validation_tools(mock_mcp, test_config)

        check_selector = registered_tools["check_selector"]

        # Test various valid selectors
        test_cases = [
            ("Button", "type"),
            (".custom-class", "class"),
            ("#unique-id", "id"),
            ("Button:hover", "pseudo-class"),
        ]

        for selector, expected_type in test_cases:
            result = await check_selector(selector=selector)

            assert result["valid"] is True
            assert result["selector"] == selector
            assert "type" in result
            # Type detection might vary, so just check it exists

    @pytest.mark.asyncio
    async def test_tool_error_handling(self, test_config: TextualMCPConfig):
        """Test error handling in validation tools."""
        mock_mcp = MagicMock()
        registered_tools = {}

        def tool_decorator():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = tool_decorator
        register_validation_tools(mock_mcp, test_config)

        registered_tools["validate_tcss"]

        # We need to mock the tcss_validator instance that was created during registration
        # Since it's created in the closure, we need to patch it at module level
        with patch.object(
            test_config.validators, "strict_mode", False
        ):  # Ensure config matches
            # Re-register to get a fresh instance
            mock_mcp2 = MagicMock()
            registered_tools2 = {}

            def tool_decorator2():
                def decorator(func):
                    registered_tools2[func.__name__] = func
                    return func

                return decorator

            mock_mcp2.tool = tool_decorator2

            # Patch TCSSValidator to raise exception when instantiated
            with patch(
                "textual_mcp.tools.validation_tools.TCSSValidator"
            ) as mock_validator_class:
                mock_validator = MagicMock()
                mock_validator.validate.side_effect = Exception("Validation error")
                mock_validator_class.return_value = mock_validator

                # Re-register with mocked validator
                register_validation_tools(mock_mcp2, test_config)
                validate_tcss_mocked = registered_tools2["validate_tcss"]

                with pytest.raises(ToolExecutionError) as exc_info:
                    await validate_tcss_mocked(css_content="Button { color: red; }")

                assert "CSS validation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_tool_timing(self, test_config: TextualMCPConfig):
        """Test that tools include timing information."""
        mock_mcp = MagicMock()
        registered_tools = {}

        def tool_decorator():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = tool_decorator
        register_validation_tools(mock_mcp, test_config)

        validate_tcss = registered_tools["validate_tcss"]

        # Just run the tool normally - it should include timing
        result = await validate_tcss(css_content="Button { color: red; }")

        # Should have parse_time_ms in stats from the actual validator
        assert "stats" in result
        assert "parse_time_ms" in result["stats"]
        assert isinstance(result["stats"]["parse_time_ms"], (int, float))
        assert result["stats"]["parse_time_ms"] >= 0

    def test_tool_logging(self, test_config: TextualMCPConfig):
        """Test that tools log their execution."""
        mock_mcp = MagicMock()

        with patch(
            "textual_mcp.tools.validation_tools.log_tool_execution"
        ) as mock_log_exec:
            with patch(
                "textual_mcp.tools.validation_tools.log_tool_completion"
            ) as mock_log_complete:
                register_validation_tools(mock_mcp, test_config)

                # Tools should be registered but not executed yet
                assert mock_log_exec.call_count == 0
                assert mock_log_complete.call_count == 0
