"""Tests for the widget generator module."""

import pytest
from unittest.mock import patch

from textual_mcp.generators.widget_generator import (
    WidgetGenerator,
    WidgetType,
    WidgetGenerationResult,
)
from textual_mcp.utils.errors import ValidationError, ToolExecutionError


class TestWidgetGenerator:
    """Test cases for WidgetGenerator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = WidgetGenerator()

    def test_initialization(self):
        """Test widget generator initialization."""
        assert self.generator is not None
        assert len(self.generator._widget_templates) == len(WidgetType)
        assert len(self.generator._css_templates) == len(WidgetType)
        assert len(self.generator._event_handler_templates) > 0

    def test_get_supported_widget_types(self):
        """Test getting supported widget types."""
        types = self.generator.get_supported_widget_types()
        expected_types = ["container", "input", "display", "interactive", "layout"]

        assert isinstance(types, list)
        assert len(types) == len(expected_types)
        for widget_type in expected_types:
            assert widget_type in types

    def test_get_supported_event_handlers(self):
        """Test getting supported event handlers."""
        handlers = self.generator.get_supported_event_handlers()
        expected_handlers = [
            "click",
            "key_press",
            "input_changed",
            "focus",
            "blur",
            "mount",
            "default",
        ]

        assert isinstance(handlers, list)
        assert len(handlers) >= len(expected_handlers)
        for handler in expected_handlers:
            assert handler in handlers

    def test_validate_widget_name_valid(self):
        """Test widget name validation with valid names."""
        valid_names = ["MyWidget", "CustomButton", "DataDisplay", "UserInput"]

        for name in valid_names:
            is_valid, error = self.generator.validate_widget_name(name)
            assert is_valid is True
            assert error is None

    def test_validate_widget_name_invalid(self):
        """Test widget name validation with invalid names."""
        invalid_names = ["", "myWidget", "123Widget", "my-widget", "my widget"]

        for name in invalid_names:
            is_valid, error = self.generator.validate_widget_name(name)
            assert is_valid is False
            assert error is not None
            assert isinstance(error, str)

    def test_generate_container_widget(self):
        """Test generating a container widget."""
        result = self.generator.generate_widget(
            widget_name="MyContainer",
            widget_type="container",
            includes_css=True,
            event_handlers=["click"],
        )

        assert isinstance(result, WidgetGenerationResult)
        assert result.widget_name == "MyContainer"
        assert result.widget_type == "container"
        assert result.includes_css is True
        assert "click" in result.event_handlers

        # Check Python code
        assert "class MyContainer(Widget):" in result.python_code
        assert "from textual.widgets import Label, Button" in result.python_code
        assert "def compose(self)" in result.python_code
        assert (
            "def on_button_pressed(self, event: Button.Pressed)" in result.python_code
        )

        # Check CSS code
        assert "MyContainer {" in result.css_code
        assert "border: solid $primary;" in result.css_code

        # Check usage example
        assert "from your_module import MyContainer" in result.usage_example
        assert "widget = MyContainer()" in result.usage_example

    def test_generate_input_widget(self):
        """Test generating an input widget."""
        result = self.generator.generate_widget(
            widget_name="CustomInput",
            widget_type="input",
            includes_css=True,
            event_handlers=["input_changed", "focus"],
        )

        assert result.widget_name == "CustomInput"
        assert result.widget_type == "input"

        # Check Python code
        assert "class CustomInput(Widget):" in result.python_code
        assert "from textual.widgets import Input" in result.python_code
        assert "yield Input(" in result.python_code
        assert "def on_input_changed(self, event: Input.Changed)" in result.python_code
        assert "def on_focus(self, event)" in result.python_code

        # Check CSS code
        assert "CustomInput {" in result.css_code
        assert "> Input {" in result.css_code

    def test_generate_display_widget(self):
        """Test generating a display widget."""
        result = self.generator.generate_widget(
            widget_name="InfoDisplay", widget_type="display", includes_css=True
        )

        assert result.widget_name == "InfoDisplay"
        assert result.widget_type == "display"

        # Check Python code
        assert "class InfoDisplay(Widget):" in result.python_code
        assert "from textual.widgets import Static" in result.python_code
        assert "yield Static(" in result.python_code
        assert "def compose(self)" in result.python_code

        # Check CSS code
        assert "InfoDisplay {" in result.css_code
        assert "> Static {" in result.css_code

    def test_generate_interactive_widget(self):
        """Test generating an interactive widget."""
        result = self.generator.generate_widget(
            widget_name="InteractivePanel",
            widget_type="interactive",
            includes_css=True,
            event_handlers=["click", "key_press"],
        )

        assert result.widget_name == "InteractivePanel"
        assert result.widget_type == "interactive"

        # Check Python code
        assert "class InteractivePanel(Widget):" in result.python_code
        assert "from textual.widgets import Button, Label" in result.python_code
        assert "yield Button(" in result.python_code
        assert "yield Label(" in result.python_code
        assert (
            "def on_button_pressed(self, event: Button.Pressed)" in result.python_code
        )
        assert "def on_key(self, event: Key)" in result.python_code

    def test_generate_layout_widget(self):
        """Test generating a layout widget."""
        result = self.generator.generate_widget(
            widget_name="LayoutPanel", widget_type="layout", includes_css=True
        )

        assert result.widget_name == "LayoutPanel"
        assert result.widget_type == "layout"

        # Check Python code
        assert "class LayoutPanel(Widget):" in result.python_code
        assert "from textual.containers import Horizontal" in result.python_code
        assert "with Horizontal():" in result.python_code

        # Check CSS code
        assert "LayoutPanel {" in result.css_code
        assert "> Horizontal {" in result.css_code

    def test_generate_widget_without_css(self):
        """Test generating a widget without CSS."""
        result = self.generator.generate_widget(
            widget_name="NoCSSWidget", widget_type="container", includes_css=False
        )

        assert result.includes_css is False
        assert result.css_code == ""
        assert "class NoCSSWidget(Widget):" in result.python_code

    def test_generate_widget_without_event_handlers(self):
        """Test generating a widget without event handlers."""
        result = self.generator.generate_widget(
            widget_name="SimpleWidget",
            widget_type="container",
            includes_css=True,
            event_handlers=None,
        )

        assert result.event_handlers == []
        assert "def on_button_pressed" not in result.python_code
        assert "def on_key" not in result.python_code

    def test_generate_widget_invalid_name(self):
        """Test generating a widget with invalid name."""
        with pytest.raises(ValidationError) as exc_info:
            self.generator.generate_widget(
                widget_name="invalid_name", widget_type="container"
            )

        assert "Widget name should start with an uppercase letter" in str(
            exc_info.value
        )

    def test_generate_widget_invalid_type(self):
        """Test generating a widget with invalid type."""
        with pytest.raises(ValidationError) as exc_info:
            self.generator.generate_widget(
                widget_name="ValidName", widget_type="invalid_type"
            )

        assert "Invalid widget type" in str(exc_info.value)

    def test_generate_widget_empty_name(self):
        """Test generating a widget with empty name."""
        with pytest.raises(ValidationError) as exc_info:
            self.generator.generate_widget(widget_name="", widget_type="container")

        assert "Widget name must be a valid Python identifier" in str(exc_info.value)

    def test_generate_widget_timing(self):
        """Test that widget generation includes timing information."""
        result = self.generator.generate_widget(
            widget_name="TimedWidget", widget_type="container"
        )

        assert result.generation_time_ms > 0
        assert isinstance(result.generation_time_ms, float)

    def test_get_widget_type_enum(self):
        """Test getting WidgetType enum from string."""
        assert self.generator._get_widget_type("container") == WidgetType.CONTAINER
        assert self.generator._get_widget_type("input") == WidgetType.INPUT
        assert self.generator._get_widget_type("display") == WidgetType.DISPLAY
        assert self.generator._get_widget_type("interactive") == WidgetType.INTERACTIVE
        assert self.generator._get_widget_type("layout") == WidgetType.LAYOUT

        with pytest.raises(ValueError):
            self.generator._get_widget_type("invalid")

    def test_generate_event_handler_methods(self):
        """Test generating event handler methods."""
        handlers = ["click", "key_press", "input_changed"]
        methods = self.generator._generate_event_handler_methods(handlers)

        assert "def on_button_pressed(self, event: Button.Pressed)" in methods
        assert "def on_key(self, event: Key)" in methods
        assert "def on_input_changed(self, event: Input.Changed)" in methods

    def test_generate_event_handler_methods_empty(self):
        """Test generating event handler methods with empty list."""
        methods = self.generator._generate_event_handler_methods([])
        assert methods == ""

    def test_generate_compose_method_all_types(self):
        """Test generating compose methods for all widget types."""
        for widget_type in WidgetType:
            compose_method = self.generator._generate_compose_method(widget_type)
            assert "def compose(self)" in compose_method
            assert "ComposeResult" in compose_method

    def test_generate_render_method(self):
        """Test generating render method."""
        # Modern Textual widgets use compose, not render
        # For display widgets, it generates an update_content method instead
        render_method = self.generator._generate_render_method(
            WidgetType.DISPLAY, "TestWidget"
        )
        assert "update_content" in render_method
        assert "self.query_one" in render_method

        # Other widgets should not have render method
        render_method = self.generator._generate_render_method(
            WidgetType.CONTAINER, "TestWidget"
        )
        assert render_method == ""

    def test_get_additional_imports(self):
        """Test getting additional imports."""
        imports = self.generator._get_additional_imports(
            WidgetType.CONTAINER, ["click"]
        )
        assert "from textual.app import ComposeResult" in imports
        assert "from textual.widgets import Label, Button" in imports

        imports = self.generator._get_additional_imports(
            WidgetType.INPUT, ["input_changed"]
        )
        assert "from textual.widgets import Input" in imports

    @patch("textual_mcp.generators.widget_generator.time.time")
    def test_generate_widget_exception_handling(self, mock_time):
        """Test exception handling during widget generation."""
        mock_time.side_effect = [0, 0.1]  # start_time, end_time

        # Mock the _validate_inputs method to raise an exception
        with patch.object(
            self.generator, "_validate_inputs", side_effect=Exception("Test error")
        ):
            with pytest.raises(ToolExecutionError) as exc_info:
                self.generator.generate_widget("TestWidget", "container")

            assert "Test error" in str(exc_info.value)


class TestWidgetGenerationResult:
    """Test cases for WidgetGenerationResult dataclass."""

    def test_widget_generation_result_creation(self):
        """Test creating a WidgetGenerationResult."""
        result = WidgetGenerationResult(
            python_code="test code",
            css_code="test css",
            usage_example="test usage",
            widget_name="TestWidget",
            widget_type="container",
            includes_css=True,
            event_handlers=["click"],
            generation_time_ms=10.5,
        )

        assert result.python_code == "test code"
        assert result.css_code == "test css"
        assert result.usage_example == "test usage"
        assert result.widget_name == "TestWidget"
        assert result.widget_type == "container"
        assert result.includes_css is True
        assert result.event_handlers == ["click"]
        assert result.generation_time_ms == 10.5


class TestWidgetType:
    """Test cases for WidgetType enum."""

    def test_widget_type_values(self):
        """Test WidgetType enum values."""
        assert WidgetType.CONTAINER.value == "container"
        assert WidgetType.INPUT.value == "input"
        assert WidgetType.DISPLAY.value == "display"
        assert WidgetType.INTERACTIVE.value == "interactive"
        assert WidgetType.LAYOUT.value == "layout"

    def test_widget_type_count(self):
        """Test that we have the expected number of widget types."""
        assert len(WidgetType) == 5
