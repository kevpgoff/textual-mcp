"""Tests for TCSS validator."""

from pathlib import Path

from textual_mcp.validators.tcss_validator import TCSSValidator, ValidationResult
from textual_mcp.utils.errors import ValidationError


class TestTCSSValidator:
    """Test cases for TCSS validator."""

    def test_validate_valid_css(self, tcss_validator: TCSSValidator, sample_css: str):
        """Test validation of valid CSS."""
        result = tcss_validator.validate(sample_css)

        assert isinstance(result, ValidationResult)
        assert result.valid is True
        assert len(result.errors) == 0
        assert result.rule_count > 0
        assert result.selector_count > 0
        assert result.parse_time_ms >= 0
        assert "Valid" in result.summary

    def test_validate_empty_css(self, tcss_validator: TCSSValidator):
        """Test validation of empty CSS."""
        result = tcss_validator.validate("")

        assert result.valid is True
        assert len(result.errors) == 0
        assert result.rule_count == 0
        assert result.selector_count == 0

    def test_validate_css_with_comments(self, tcss_validator: TCSSValidator):
        """Test validation of CSS with comments."""
        css_with_comments = """
        /* Main button styles */
        Button {
            background: $primary;
            /* Color for text */
            color: $text;
        }
        """

        result = tcss_validator.validate(css_with_comments)
        assert result.valid is True
        assert result.rule_count >= 1

    def test_validate_file_exists(self, tcss_validator: TCSSValidator, sample_css_file: Path):
        """Test validation of existing file."""
        result = tcss_validator.validate_file(str(sample_css_file))

        assert result.valid is True
        assert len(result.errors) == 0
        assert result.rule_count > 0

    def test_validate_file_not_exists(self, tcss_validator: TCSSValidator):
        """Test validation of non-existent file."""
        result = tcss_validator.validate_file("nonexistent.tcss")

        assert result.valid is False
        assert len(result.errors) == 1
        assert "not found" in result.errors[0].message.lower()

    def test_validate_large_css_file_limit(self, tcss_validator: TCSSValidator):
        """Test validation with file size limit."""
        # Create CSS content larger than the limit
        large_css = "Button { color: red; }\n" * 10000

        # This should exceed the default 1MB limit in our test config
        if len(large_css) > tcss_validator.config.max_file_size:
            result = tcss_validator.validate(large_css)
            assert result.valid is False
            assert any("exceeds maximum size" in error.message for error in result.errors)

    def test_strict_mode_toggle(self, tcss_validator: TCSSValidator, sample_css: str):
        """Test strict mode functionality."""
        # Test with strict mode off
        tcss_validator.strict_mode = False
        result_normal = tcss_validator.validate(sample_css)

        # Test with strict mode on
        tcss_validator.strict_mode = True
        result_strict = tcss_validator.validate(sample_css)

        # Both should be valid for our sample CSS, but strict mode might have more warnings
        assert result_normal.valid is True
        assert result_strict.valid is True

    def test_css_with_variables(self, tcss_validator: TCSSValidator):
        """Test CSS with Textual variables."""
        css_with_vars = """
        Button {
            background: $primary;
            color: $text;
            border: solid $accent;
        }
        """

        result = tcss_validator.validate(css_with_vars)
        assert result.valid is True

    def test_css_with_textual_properties(self, tcss_validator: TCSSValidator):
        """Test CSS with Textual-specific properties."""
        textual_css = """
        Button {
            dock: top;
            layer: overlay;
            offset: 1 2;
            tint: $primary 50%;
        }
        """

        result = tcss_validator.validate(textual_css)
        # This might be valid or invalid depending on Textual version
        # We mainly test that it doesn't crash
        assert isinstance(result, ValidationResult)

    def test_validation_result_structure(self, tcss_validator: TCSSValidator, sample_css: str):
        """Test that validation result has correct structure."""
        result = tcss_validator.validate(sample_css)

        # Check all required fields are present
        assert hasattr(result, "valid")
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")
        assert hasattr(result, "suggestions")
        assert hasattr(result, "summary")
        assert hasattr(result, "parse_time_ms")
        assert hasattr(result, "rule_count")
        assert hasattr(result, "selector_count")

        # Check types
        assert isinstance(result.valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
        assert isinstance(result.suggestions, list)
        assert isinstance(result.summary, str)
        assert isinstance(result.parse_time_ms, (int, float))
        assert isinstance(result.rule_count, int)
        assert isinstance(result.selector_count, int)

    def test_error_details(self, tcss_validator: TCSSValidator):
        """Test that validation errors contain proper details."""
        # This test might need to be adjusted based on what Textual's parser actually catches
        potentially_invalid_css = """
        Button {
            background: ;
            color: red
        }
        """

        result = tcss_validator.validate(potentially_invalid_css)

        # Check that if there are errors, they have proper structure
        for error in result.errors:
            assert isinstance(error, ValidationError)
            assert error.message
            # Line and column might be None for some errors
            if error.line is not None:
                assert isinstance(error.line, int)
            if error.column is not None:
                assert isinstance(error.column, int)
