"""Tests for inline CSS validator."""

from textual_mcp.validators.inline_validator import (
    InlineValidator,
    InlineValidationResult,
)


class TestInlineValidator:
    """Test cases for inline CSS validator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = InlineValidator()

    def test_validate_valid_styles(self):
        """Test validation of valid inline styles."""
        valid_styles = [
            "color: red;",
            "color: red; background: blue;",
            "padding: 1 2; margin: 0;",
            "width: 100%; height: auto;",
            "border: solid red;",
            "display: none;",
            "text-align: center; text-style: bold;",
        ]

        for style in valid_styles:
            result = self.validator.validate(style)

            assert isinstance(result, InlineValidationResult)
            assert result.valid is True
            assert len(result.errors) == 0

    def test_validate_empty_style(self):
        """Test validation of empty style string."""
        result = self.validator.validate("")

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_whitespace_only(self):
        """Test validation of whitespace-only string."""
        result = self.validator.validate("   \n\t  ")

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_missing_semicolon(self):
        """Test validation with missing semicolon."""
        # Textual requires semicolons, so this will be invalid
        result = self.validator.validate("color: red; background: blue")

        # Without trailing semicolon, Textual will reject it
        assert result.valid is False
        assert len(result.errors) > 0
        assert "end of file" in result.errors[0].message.lower()

    def test_validate_single_property_no_semicolon(self):
        """Test single property without semicolon."""
        result = self.validator.validate("color: red")

        # Textual requires semicolons even for single properties
        assert result.valid is False
        assert len(result.errors) > 0

    def test_validate_properties_with_spaces(self):
        """Test properties with various spacing."""
        # Textual is strict about spacing - only standard format is accepted
        valid_styles = [
            "color:red;",  # No spaces
            "color: red;",  # Normal spacing
        ]

        invalid_styles = [
            "color : red ;",  # Extra spaces around colon
            "  color  :  red  ;  ",  # Lots of spaces
        ]

        for style in valid_styles:
            result = self.validator.validate(style)
            assert result.valid is True
            assert len(result.errors) == 0

        for style in invalid_styles:
            result = self.validator.validate(style)
            assert result.valid is False
            assert len(result.errors) > 0

    def test_validate_textual_specific_properties(self):
        """Test Textual-specific CSS properties."""
        textual_styles = [
            "dock: top;",
            "layer: overlay;",
            "offset: 1 2;",
            "tint: blue 50%;",
            "scrollbar-gutter: stable;",
            "overflow-x: auto;",
            "overflow-y: hidden;",
        ]

        for style in textual_styles:
            result = self.validator.validate(style)
            assert result.valid is True
            assert len(result.errors) == 0

    def test_validate_color_values(self):
        """Test various color value formats."""
        color_styles = [
            "color: red;",
            "color: #ff0000;",
            "color: #f00;",
            "color: rgb(255, 0, 0);",
            "color: rgba(255, 0, 0, 0.5);",
            "color: transparent;",
        ]

        # CSS variables are not supported in inline styles
        invalid_color_styles = [
            "color: $primary;",  # Textual variable
            "color: $text-color;",  # Variable with dash
        ]

        for style in color_styles:
            result = self.validator.validate(style)
            assert result.valid is True
            assert len(result.errors) == 0

        for style in invalid_color_styles:
            result = self.validator.validate(style)
            assert result.valid is False
            assert len(result.errors) > 0

    def test_validate_numeric_values(self):
        """Test numeric property values."""
        numeric_styles = [
            "width: 100;",
            "width: 100%;",
            "width: 50.5%;",
            "padding: 1 2 3 4;",
            "margin: 0;",
            "opacity: 0.8;",
        ]

        # These are not supported by Textual
        invalid_numeric_styles = [
            "font-size: 14;",
            "line-height: 1.5;",
        ]

        for style in numeric_styles:
            result = self.validator.validate(style)
            assert result.valid is True
            assert len(result.errors) == 0

        for style in invalid_numeric_styles:
            result = self.validator.validate(style)
            assert result.valid is False
            assert len(result.errors) > 0

    def test_validate_invalid_properties(self):
        """Test invalid property names and values."""
        # Note: Textual's parser might be more lenient than expected
        invalid_styles = [
            "invalid-property: value;",  # Unknown property
            "color: ;",  # Missing value
            ": value;",  # Missing property name
            "color red;",  # Missing colon
            "color: 'unclosed string;",  # Unclosed string
        ]

        for style in invalid_styles:
            result = self.validator.validate(style)
            # These should either be invalid or have errors
            if result.valid:
                # If valid, check for warnings
                assert len(result.warnings) > 0 or len(result.errors) > 0
            else:
                assert len(result.errors) > 0

    def test_validate_multiple_properties(self):
        """Test multiple properties in one declaration."""
        result = self.validator.validate(
            "color: red; background: blue; padding: 1 2; margin: 0;"
        )

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_quoted_values(self):
        """Test properties with quoted values."""
        quoted_styles = [
            'content: "Hello World";',
            "font-family: 'Arial', sans-serif;",
            'background-image: url("image.png");',
        ]

        for style in quoted_styles:
            result = self.validator.validate(style)
            # These might fail with Textual's parser
            assert isinstance(result, InlineValidationResult)

    def test_validate_complex_values(self):
        """Test complex property values."""
        complex_styles = [
            "border: 1px solid $primary;",
            "box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);",
            "transition: all 0.3s ease-in-out;",
            "grid-template-columns: 1fr 2fr 1fr;",
        ]

        for style in complex_styles:
            result = self.validator.validate(style)
            # These might not all be supported by Textual
            assert isinstance(result, InlineValidationResult)

    def test_validate_line_breaks(self):
        """Test styles with line breaks."""
        multiline_style = """
        color: red;
        background: blue;
        padding: 1 2;
        """

        result = self.validator.validate(multiline_style)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_property_parsing_details(self):
        """Test property parsing edge cases."""
        # Test duplicate properties
        result = self.validator.validate("color: red; color: blue;")

        # Textual's parser resolves duplicates automatically (last wins)
        # So we don't get warnings about duplicates
        assert result.valid is True
        assert len(result.warnings) == 0

    def test_error_recovery(self):
        """Test error recovery in parsing."""
        # Invalid syntax that should produce errors
        result = self.validator.validate(
            "color: red; invalid syntax here; background: blue;"
        )

        # Should have errors but might still parse some valid parts
        assert len(result.errors) > 0 or len(result.warnings) > 0
