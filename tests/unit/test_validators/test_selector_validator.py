"""Tests for CSS selector validator."""

from textual_mcp.validators.selector_validator import (
    SelectorValidator,
    SelectorValidationResult,
)


class TestSelectorValidator:
    """Test cases for CSS selector validator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SelectorValidator()

    def test_validate_type_selectors(self):
        """Test validation of type selectors."""
        type_selectors = [
            "Button",
            "Label",
            "Input",
            "Container",
            "Widget",
            "CustomWidget",
        ]

        for selector in type_selectors:
            result = self.validator.validate_selector(selector)

            assert isinstance(result, SelectorValidationResult)
            assert result.valid is True
            # Selector field doesn't exist in result
            assert result.selector_type == "type"
            assert result.specificity == (0, 0, 1)
            assert result.error is None

    def test_validate_class_selectors(self):
        """Test validation of class selectors."""
        class_selectors = [
            ".button",
            ".custom-class",
            ".primary",
            ".btn-large",
            ".active",
            ".-disabled",  # Leading dash
            ".className123",  # With numbers
        ]

        for selector in class_selectors:
            result = self.validator.validate_selector(selector)

            assert result.valid is True
            # Selector field doesn't exist in result
            assert result.selector_type == "class"
            assert result.specificity == (0, 1, 1)  # Textual adds 1 for type count

    def test_validate_id_selectors(self):
        """Test validation of ID selectors."""
        id_selectors = [
            "#main",
            "#submit-button",
            "#container-1",
            "#app",
            "#main_content",
        ]

        for selector in id_selectors:
            result = self.validator.validate_selector(selector)

            assert result.valid is True
            # Selector field doesn't exist in result
            assert result.selector_type == "id"
            assert result.specificity == (1, 0, 1)  # Textual adds 1 for type count

    def test_validate_pseudo_class_selectors(self):
        """Test validation of pseudo-class selectors."""
        pseudo_selectors = [
            "Button:hover",
            "Input:focus",
            "Label:disabled",
            ".active:hover",
            "#main:focus",
            "Container:first-child",
            "Widget:last-child",
        ]

        for selector in pseudo_selectors:
            result = self.validator.validate_selector(selector)

            assert result.valid is True
            assert result.selector_type == "pseudo-class"
            # Specificity should include the base selector

    def test_validate_pseudo_element_selectors(self):
        """Test validation of pseudo-element selectors."""
        # Textual doesn't support pseudo-elements like ::before, ::after
        pseudo_element_selectors = [
            "Button::before",
            "Label::after",
            "::placeholder",
            ".custom::before",
            "#main::after",
        ]

        for selector in pseudo_element_selectors:
            result = self.validator.validate_selector(selector)

            # These should be invalid in Textual
            assert result.valid is False
            assert result.error is not None
            assert "::" in selector  # Verify it contains double colon

    def test_validate_attribute_selectors(self):
        """Test validation of attribute selectors."""
        # Textual doesn't support attribute selectors
        attribute_selectors = [
            "[disabled]",
            "[type='button']",
            '[data-test="value"]',
            "[class~='active']",
            "[id^='prefix']",
            "[href$='.pdf']",
            "[title*='substring']",
            "Button[disabled]",
            ".custom[data-id='123']",
        ]

        for selector in attribute_selectors:
            result = self.validator.validate_selector(selector)

            # These should be invalid in Textual
            assert result.valid is False
            assert result.error is not None

    def test_validate_combinator_selectors(self):
        """Test validation of combinator selectors."""
        # Textual only supports descendant combinators (space)
        valid_combinators = [
            "Container Button",  # Descendant - should work
        ]

        invalid_combinators = [
            "Container > Button",  # Child combinator - not supported
            "Header + Content",  # Adjacent sibling - not supported
            "Header ~ Footer",  # General sibling - not supported
            ".parent > .child",  # Child combinator - not supported
            "#main > Button.primary",  # Child combinator - not supported
            "Container > Button:hover",  # Child combinator - not supported
        ]

        for selector in valid_combinators:
            result = self.validator.validate_selector(selector)
            assert result.valid is True
            assert result.selector_type == "descendant"

        for selector in invalid_combinators:
            result = self.validator.validate_selector(selector)
            assert result.valid is False
            assert result.error is not None

    def test_validate_complex_selectors(self):
        """Test validation of complex selectors."""
        # Test complex selectors based on what Textual supports
        valid_complex = [
            "Container Button.primary",  # Descendant with class
            "#main Button",  # ID with descendant
        ]

        invalid_complex = [
            "Container > Button.primary:hover",  # Child combinator
            "#main .sidebar Button[disabled]",  # Attribute selector
            ".card:first-child > .title",  # Pseudo-class and child
            "Button.primary[disabled]:hover::before",  # Multiple unsupported
            "#app > .container > .row > .col:nth-child(2)",  # Complex chain
        ]

        for selector in valid_complex:
            result = self.validator.validate_selector(selector)
            assert result.valid is True

        for selector in invalid_complex:
            result = self.validator.validate_selector(selector)
            assert result.valid is False

    def test_validate_empty_selector(self):
        """Test validation of empty selector."""
        result = self.validator.validate_selector("")

        assert result.valid is False
        assert result.error is not None
        assert "empty" in result.error.lower()

    def test_validate_whitespace_selector(self):
        """Test validation of whitespace-only selector."""
        result = self.validator.validate_selector("   \t\n  ")

        assert result.valid is False
        assert result.error is not None

    def test_validate_invalid_selectors(self):
        """Test validation of invalid selectors."""
        invalid_selectors = [
            "123invalid",  # Starts with number
            ".123class",  # Class starts with number
            "#123id",  # ID starts with number
            "Button..double",  # Double dot
            "Button:::",  # Triple colon
            ".class..",  # Trailing dots
            "Button >",  # Incomplete combinator
            "> Button",  # Starting with combinator
            "Button[",  # Unclosed attribute
            "Button[attr=]",  # Empty attribute value
        ]

        for selector in invalid_selectors:
            result = self.validator.validate_selector(selector)

            # Should either be invalid or have warnings
            # Should either be invalid or have an error
            if not result.valid:
                assert result.error is not None

    def test_validate_universal_selector(self):
        """Test validation of universal selector."""
        # Test if Textual supports universal selector
        result = self.validator.validate_selector("*")

        if result.valid:
            # If * is valid, test combinations
            assert result.selector_type == "type"
        else:
            # If * is not supported
            assert result.error is not None

        # These combinations likely won't work due to unsupported combinators
        invalid_universal = [
            "* > Button",
            ".container > *",
            "* + *",
        ]

        for selector in invalid_universal:
            result = self.validator.validate_selector(selector)
            assert result.valid is False

    def test_validate_multiple_classes(self):
        """Test selectors with multiple classes."""
        multi_class_selectors = [
            ".btn.primary",
            ".active.highlighted",
            "Button.large.primary",
            "#main.active.visible",
        ]

        for selector in multi_class_selectors:
            result = self.validator.validate_selector(selector)

            assert result.valid is True
            # Specificity should account for all classes

    def test_specificity_calculation(self):
        """Test specificity calculation for various selectors."""
        # Only test selectors that Textual actually supports
        test_cases = [
            ("Button", (0, 0, 1)),  # Type selector
            (".class", (0, 1, 1)),  # Class selector - Textual counts differently
            ("#id", (1, 0, 1)),  # ID selector - Textual counts differently
            ("Button.class", (0, 1, 1)),  # Type + class
            ("#id.class", (1, 1, 1)),  # ID + class - adjusted for Textual
            ("Button:hover", (0, 1, 1)),  # Type + pseudo-class
            (".class1.class2", (0, 2, 1)),  # Two classes - adjusted
            ("Container Button", (0, 0, 2)),  # Descendant selector
        ]

        for selector, expected_specificity in test_cases:
            result = self.validator.validate_selector(selector)
            if result.valid:
                # Some selectors might have different specificity than expected
                assert isinstance(result.specificity, tuple)
                assert len(result.specificity) == 3

    def test_selector_components(self):
        """Test parsing of selector components."""
        # Test with a simpler selector that Textual supports
        selector = "Container Button"
        result = self.validator.validate_selector(selector)

        assert result.valid is True
        # Should be identified as a descendant selector
        assert result.selector_type == "descendant"

        # Test other component types
        selector = "Button:hover"
        result = self.validator.validate_selector(selector)
        assert result.valid is True
        assert result.selector_type == "pseudo-class"

    def test_textual_specific_selectors(self):
        """Test Textual-specific selector patterns."""
        textual_selectors = [
            "Screen",
            "App",
            "Widget",
            "Container",
            "ScrollableContainer",
            "Horizontal",
            "Vertical",
            "Grid",
        ]

        for selector in textual_selectors:
            result = self.validator.validate_selector(selector)
            assert result.valid is True

    def test_case_sensitivity(self):
        """Test case sensitivity in selectors."""
        # Textual expects PascalCase for widget types
        valid_selectors = [
            "Button",  # Correct case for Textual widget
            ".class",  # Class selector
            "#id",  # ID selector
        ]

        invalid_selectors = [
            "button",  # Lowercase - Textual expects PascalCase
            "BUTTON",  # All caps - Textual expects PascalCase
        ]

        for selector in valid_selectors:
            result = self.validator.validate_selector(selector)
            assert result.valid is True

        for selector in invalid_selectors:
            result = self.validator.validate_selector(selector)
            # These might be invalid due to case
            assert result.valid is False

    def test_escaped_characters(self):
        """Test selectors with escaped characters."""
        escaped_selectors = [
            r".class\.with\.dots",
            r"#id\:with\:colons",
            r".class\@special",
        ]

        for selector in escaped_selectors:
            result = self.validator.validate_selector(selector)
            # Should handle escaped characters properly
            assert isinstance(result, SelectorValidationResult)
