"""Widget generator for creating custom Textual widgets."""

import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..utils.errors import ValidationError, ToolExecutionError
from ..utils.logging_config import LoggerMixin


class WidgetType(Enum):
    """Supported widget types."""

    CONTAINER = "container"
    INPUT = "input"
    DISPLAY = "display"
    INTERACTIVE = "interactive"
    LAYOUT = "layout"


@dataclass
class WidgetGenerationResult:
    """Result of widget generation."""

    python_code: str
    css_code: str
    usage_example: str
    widget_name: str
    widget_type: str
    includes_css: bool
    event_handlers: List[str]
    generation_time_ms: float


class WidgetGenerator(LoggerMixin):
    """Generator for creating custom Textual widgets with templates."""

    def __init__(self) -> None:
        """Initialize the widget generator."""
        self._widget_templates = self._initialize_templates()
        self._css_templates = self._initialize_css_templates()
        self._event_handler_templates = self._initialize_event_templates()

    def generate_widget(
        self,
        widget_name: str,
        widget_type: str,
        includes_css: bool = True,
        event_handlers: Optional[List[str]] = None,
    ) -> WidgetGenerationResult:
        """
        Generate a custom Textual widget.

        Args:
            widget_name: Name of the widget class
            widget_type: Type of widget (container, input, display, etc.)
            includes_css: Whether to include CSS template
            event_handlers: List of event handlers to include

        Returns:
            WidgetGenerationResult with generated code
        """
        start_time = time.time()

        try:
            # Validate inputs
            self._validate_inputs(widget_name, widget_type, event_handlers)

            # Normalize widget type
            widget_type_enum = self._get_widget_type(widget_type)
            event_handlers = event_handlers or []

            # Generate Python code
            python_code = self._generate_python_code(
                widget_name, widget_type_enum, event_handlers
            )

            # Generate CSS code if requested
            css_code = ""
            if includes_css:
                css_code = self._generate_css_code(widget_name, widget_type_enum)

            # Generate usage example
            usage_example = self._generate_usage_example(
                widget_name, widget_type_enum, event_handlers
            )

            generation_time = (time.time() - start_time) * 1000

            return WidgetGenerationResult(
                python_code=python_code,
                css_code=css_code,
                usage_example=usage_example,
                widget_name=widget_name,
                widget_type=widget_type,
                includes_css=includes_css,
                event_handlers=event_handlers,
                generation_time_ms=generation_time,
            )

        except ValidationError:
            # Re-raise ValidationError as is
            raise
        except Exception as e:
            self.logger.error(f"Widget generation failed: {e}")
            raise ToolExecutionError("generate_widget", str(e))

    def _validate_inputs(
        self, widget_name: str, widget_type: str, event_handlers: Optional[List[str]]
    ) -> None:
        """Validate input parameters."""
        if not widget_name or not widget_name.isidentifier():
            raise ValidationError("Widget name must be a valid Python identifier")

        if not widget_name[0].isupper():
            raise ValidationError("Widget name should start with an uppercase letter")

        try:
            self._get_widget_type(widget_type)
        except ValueError:
            valid_types = [wt.value for wt in WidgetType]
            raise ValidationError(
                f"Invalid widget type '{widget_type}'. Valid types: {valid_types}"
            )

        if event_handlers:
            for handler in event_handlers:
                if not handler or not isinstance(handler, str):
                    raise ValidationError("Event handlers must be non-empty strings")

    def _get_widget_type(self, widget_type: str) -> WidgetType:
        """Get WidgetType enum from string."""
        try:
            return WidgetType(widget_type.lower())
        except ValueError:
            raise ValueError(f"Unknown widget type: {widget_type}")

    def _generate_python_code(
        self, widget_name: str, widget_type: WidgetType, event_handlers: List[str]
    ) -> str:
        """Generate Python code for the widget."""
        template = self._widget_templates[widget_type]

        # Generate event handler methods
        event_methods = self._generate_event_handler_methods(event_handlers)

        # Generate compose method based on widget type
        compose_method = self._generate_compose_method(widget_type)

        # Generate render method if needed
        render_method = self._generate_render_method(widget_type, widget_name)

        # Replace template placeholders
        python_code = template.format(
            widget_name=widget_name,
            widget_type=widget_type.value,
            event_methods=event_methods,
            compose_method=compose_method,
            render_method=render_method,
            additional_imports=self._get_additional_imports(
                widget_type, event_handlers
            ),
        )

        return python_code

    def _generate_css_code(self, widget_name: str, widget_type: WidgetType) -> str:
        """Generate CSS code for the widget."""
        template = self._css_templates[widget_type]

        return template.format(widget_name=widget_name, widget_type=widget_type.value)

    def _generate_usage_example(
        self, widget_name: str, widget_type: WidgetType, event_handlers: List[str]
    ) -> str:
        """Generate usage example for the widget."""
        base_example = f"""from your_module import {widget_name}

# Create and mount the widget
widget = {widget_name}()
await self.mount(widget)"""

        if widget_type == WidgetType.INPUT:
            base_example += f"""

# For input widgets, you can also set initial values
widget = {widget_name}(value="initial value")
await self.mount(widget)"""

        if event_handlers:
            base_example += f"""

# Event handlers are automatically set up
# The widget will respond to: {", ".join(event_handlers)}"""

        return base_example

    def _generate_event_handler_methods(self, event_handlers: List[str]) -> str:
        """Generate event handler methods."""
        if not event_handlers:
            return ""

        methods = []
        for handler in event_handlers:
            template = self._event_handler_templates.get(
                handler, self._event_handler_templates["default"]
            )
            methods.append(template.format(event_name=handler))

        return "\n".join(methods)

    def _generate_compose_method(self, widget_type: WidgetType) -> str:
        """Generate compose method based on widget type."""
        compose_templates = {
            WidgetType.CONTAINER: '''    def compose(self) -> ComposeResult:
        """Compose child widgets."""
        # Add child widgets here
        yield Label("Container content")
        yield Button("Action", id="action-btn")''',
            WidgetType.INPUT: '''    def compose(self) -> ComposeResult:
        """Compose input widget."""
        yield Input(placeholder="Enter text here", id="main-input")''',
            WidgetType.DISPLAY: '''    def compose(self) -> ComposeResult:
        """Compose display widget."""
        yield Static("Display content here", id="display-content")''',
            WidgetType.INTERACTIVE: '''    def compose(self) -> ComposeResult:
        """Compose interactive widget."""
        yield Button("Click me", id="interactive-btn")
        yield Label("Status: Ready", id="status-label")''',
            WidgetType.LAYOUT: '''    def compose(self) -> ComposeResult:
        """Compose layout widget."""
        with Horizontal():
            yield Label("Left panel")
            yield Label("Right panel")''',
        }

        return compose_templates.get(
            widget_type, compose_templates[WidgetType.CONTAINER]
        )

    def _generate_render_method(self, widget_type: WidgetType, widget_name: str) -> str:
        """Generate render method if needed."""
        if widget_type == WidgetType.DISPLAY:
            return '''
    def update_content(self, content: str) -> None:
        """Update the display content."""
        self.query_one("#display-content", Static).update(content)'''
        return ""

    def _get_additional_imports(
        self, widget_type: WidgetType, event_handlers: List[str]
    ) -> str:
        """Get additional imports based on widget type and event handlers."""
        imports = set()

        # Base imports for all widgets
        imports.add("from textual.app import ComposeResult")

        # Widget type specific imports
        if widget_type == WidgetType.CONTAINER:
            imports.update(["from textual.widgets import Label, Button"])
        elif widget_type == WidgetType.INPUT:
            imports.add("from textual.widgets import Input")
        elif widget_type == WidgetType.DISPLAY:
            imports.add("from textual.widgets import Static")
        elif widget_type == WidgetType.INTERACTIVE:
            imports.update(["from textual.widgets import Button, Label"])
        elif widget_type == WidgetType.LAYOUT:
            imports.update(
                [
                    "from textual.widgets import Label",
                    "from textual.containers import Horizontal",
                ]
            )

        # Event handler specific imports
        for handler in event_handlers:
            if "key" in handler.lower():
                imports.add("from textual.events import Key")
            elif "click" in handler.lower() or "button" in handler.lower():
                imports.add("from textual.widgets import Button")
            elif "input" in handler.lower():
                imports.add("from textual.widgets import Input")

        return "\n".join(sorted(imports))

    def _initialize_templates(self) -> Dict[WidgetType, str]:
        """Initialize widget templates."""
        base_template = '''{additional_imports}
from textual.widget import Widget
from textual.reactive import reactive


class {widget_name}(Widget):
    """A custom {widget_type} widget."""
    
    DEFAULT_CSS = """
    {widget_name} {{
        /* Widget styles will be defined here */
    }}
    """
    
    def __init__(self, **kwargs):
        """Initialize the {widget_name} widget."""
        super().__init__(**kwargs)
        self.setup_widget()
    
    def setup_widget(self) -> None:
        """Set up widget-specific configuration."""
        pass

{compose_method}
{render_method}
{event_methods}
    
    def on_mount(self) -> None:
        """Called when widget is mounted."""
        pass
    
    def on_unmount(self) -> None:
        """Called when widget is unmounted."""
        pass
'''

        return {widget_type: base_template for widget_type in WidgetType}

    def _initialize_css_templates(self) -> Dict[WidgetType, str]:
        """Initialize CSS templates for different widget types."""
        return {
            WidgetType.CONTAINER: """{widget_name} {{
    /* Container widget styles */
    width: 100%;
    height: auto;
    padding: 1;
    border: solid $primary;
    background: $surface;
}}

{widget_name}:focus {{
    border: solid $accent;
}}

{widget_name} > Label {{
    margin: 1;
    text-align: center;
}}

{widget_name} > Button {{
    margin: 1;
    width: auto;
}}""",
            WidgetType.INPUT: """{widget_name} {{
    /* Input widget styles */
    width: 100%;
    height: 3;
    border: solid $primary;
    background: $surface;
}}

{widget_name}:focus {{
    border: solid $accent;
}}

{widget_name} > Input {{
    width: 100%;
    height: 1;
    background: $surface;
    color: $text;
}}

{widget_name} > Input:focus {{
    background: $surface-lighten-1;
}}""",
            WidgetType.DISPLAY: """{widget_name} {{
    /* Display widget styles */
    width: 100%;
    height: auto;
    padding: 1;
    border: solid $primary;
    background: $surface;
    text-align: center;
}}

{widget_name}:focus {{
    border: solid $accent;
}}

{widget_name} > Static {{
    width: 100%;
    height: auto;
    text-align: center;
    color: $text;
}}""",
            WidgetType.INTERACTIVE: """{widget_name} {{
    /* Interactive widget styles */
    width: 100%;
    height: auto;
    padding: 1;
    border: solid $primary;
    background: $surface;
}}

{widget_name}:focus {{
    border: solid $accent;
}}

{widget_name} > Button {{
    margin: 1;
    width: auto;
    background: $primary;
    color: $text-on-primary;
}}

{widget_name} > Button:hover {{
    background: $primary-lighten-1;
}}

{widget_name} > Label {{
    margin: 1;
    text-align: center;
    color: $text;
}}""",
            WidgetType.LAYOUT: """{widget_name} {{
    /* Layout widget styles */
    width: 100%;
    height: auto;
    border: solid $primary;
    background: $surface;
}}

{widget_name}:focus {{
    border: solid $accent;
}}

{widget_name} > Horizontal {{
    width: 100%;
    height: auto;
}}

{widget_name} > Horizontal > Label {{
    width: 1fr;
    height: auto;
    padding: 1;
    text-align: center;
    border-right: solid $primary;
    background: $surface-lighten-1;
}}

{widget_name} > Horizontal > Label:last-child {{
    border-right: none;
}}""",
        }

    def _initialize_event_templates(self) -> Dict[str, str]:
        """Initialize event handler templates."""
        return {
            "click": '''    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button click events."""
        # Add your click handling logic here
        pass''',
            "key_press": '''    def on_key(self, event: Key) -> None:
        """Handle key press events."""
        # Add your key handling logic here
        pass''',
            "input_changed": '''    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input change events."""
        # Add your input handling logic here
        pass''',
            "focus": '''    def on_focus(self, event) -> None:
        """Handle focus events."""
        # Add your focus handling logic here
        pass''',
            "blur": '''    def on_blur(self, event) -> None:
        """Handle blur events."""
        # Add your blur handling logic here
        pass''',
            "mount": '''    def on_mount(self) -> None:
        """Handle mount events."""
        super().on_mount()
        # Add your mount handling logic here
        pass''',
            "default": '''    def on_{event_name}(self, event) -> None:
        """Handle {event_name} events."""
        # Add your {event_name} handling logic here
        pass''',
        }

    def get_supported_widget_types(self) -> List[str]:
        """Get list of supported widget types."""
        return [wt.value for wt in WidgetType]

    def get_supported_event_handlers(self) -> List[str]:
        """Get list of supported event handlers."""
        return list(self._event_handler_templates.keys())

    def validate_widget_name(self, widget_name: str) -> Tuple[bool, Optional[str]]:
        """Validate widget name and return result with error message if invalid."""
        try:
            self._validate_inputs(widget_name, "container", None)
            return True, None
        except ValidationError as e:
            return False, str(e)
