"""MCP tools for widget generation and manipulation."""

import time
import inspect
from typing import Dict, Any, List, Optional, Annotated
from pydantic import Field

from ..config import TextualMCPConfig
from ..utils.logging_config import log_tool_execution, log_tool_completion, get_logger
from ..utils.errors import ToolExecutionError
from ..generators.widget_generator import WidgetGenerator


def register_widget_tools(mcp: Any, config: TextualMCPConfig) -> None:
    """Register all widget tools with the MCP server."""

    logger = get_logger("widget_tools")

    @mcp.tool()
    async def generate_widget(
        widget_name: Annotated[
            str,
            Field(
                description="Name of the widget class to generate (e.g., 'CustomButton', 'StatusPanel'). Must follow PascalCase Python class naming conventions.",
                pattern=r"^[A-Z][a-zA-Z0-9]*$",
                min_length=1,
                max_length=50,
            ),
        ],
        widget_type: Annotated[
            str,
            Field(
                description="Type of widget to generate: 'container' (holds other widgets), 'input' (user input), 'display' (show content), or 'interactive' (buttons, links).",
                pattern=r"^(container|input|display|interactive)$",
            ),
        ],
        includes_css: Annotated[
            bool,
            Field(
                description="Whether to include a CSS template with the widget. Set to True for widgets that need custom styling."
            ),
        ] = True,
        event_handlers: Annotated[
            Optional[List[str]],
            Field(
                description="List of event handlers to include (e.g., ['click', 'key_press', 'focus']). Use list_event_handlers tool to see all available options.",
                min_length=0,
                max_length=10,
            ),
        ] = None,
    ) -> Dict[str, Any]:
        """
        Generate a custom Textual widget.

        Args:
            widget_name: Name of the widget class
            widget_type: Type of widget (container, input, display, etc.)
            includes_css: Whether to include CSS template
            event_handlers: List of event handlers to include

        Returns:
            Dictionary with generated widget code
        """
        start_time = time.time()
        tool_name = "generate_widget"

        try:
            log_tool_execution(
                tool_name,
                {
                    "widget_name": widget_name,
                    "widget_type": widget_type,
                    "includes_css": includes_css,
                    "event_handlers": event_handlers,
                },
            )

            # Initialize widget generator
            generator = WidgetGenerator()

            # Generate widget
            result = generator.generate_widget(
                widget_name=widget_name,
                widget_type=widget_type,
                includes_css=includes_css,
                event_handlers=event_handlers,
            )

            # Prepare response
            response = {
                "python_code": result.python_code,
                "css_code": result.css_code,
                "usage_example": result.usage_example,
                "widget_info": {
                    "name": result.widget_name,
                    "type": result.widget_type,
                    "includes_css": result.includes_css,
                    "event_handlers": result.event_handlers,
                    "generation_time_ms": result.generation_time_ms,
                },
            }

            duration = time.time() - start_time
            log_tool_completion(tool_name, True, duration)

            return response

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Widget generation failed: {str(e)}"
            log_tool_completion(tool_name, False, duration, error_msg)
            raise ToolExecutionError(tool_name, error_msg)

    @mcp.tool()
    async def list_widget_types() -> Dict[str, Any]:
        """
        List all available Textual widgets.

        Returns:
            Dictionary with available widgets from the Textual library
        """
        start_time = time.time()
        tool_name = "list_widget_types"

        try:
            log_tool_execution(tool_name, {})

            # Dynamically import and get all widgets from textual.widgets
            import textual.widgets as tw

            # Get all widgets from textual.widgets using __all__
            widgets = []
            widget_info = {}

            # Use __all__ if available, otherwise fall back to dir()
            widget_names = getattr(
                tw, "__all__", [name for name in dir(tw) if not name.startswith("_")]
            )

            for name in widget_names:
                try:
                    obj = getattr(tw, name)
                    # Check if it's a class (widget)
                    if inspect.isclass(obj):
                        widgets.append(name)

                        # Get basic info about the widget
                        doc = inspect.getdoc(obj)
                        first_line = doc.split("\n")[0] if doc else "No description available"
                        widget_info[name] = first_line
                except (ImportError, AttributeError, ModuleNotFoundError) as e:
                    # Skip widgets that can't be imported
                    logger.debug(f"Skipping widget {name}: {e}")
                    continue

            # Sort widgets alphabetically
            widgets.sort()

            # Categorize widgets by type
            categories: Dict[str, List[str]] = {
                "input": [
                    "Input",
                    "MaskedInput",
                    "TextArea",
                    "Checkbox",
                    "RadioButton",
                    "RadioSet",
                    "Switch",
                    "Select",
                    "SelectionList",
                ],
                "display": [
                    "Label",
                    "Static",
                    "Pretty",
                    "Markdown",
                    "MarkdownViewer",
                    "Rule",
                    "Digits",
                    "Sparkline",
                ],
                "container": [
                    "ListView",
                    "DataTable",
                    "Tree",
                    "DirectoryTree",
                    "TabbedContent",
                    "Collapsible",
                    "ContentSwitcher",
                ],
                "interactive": [
                    "Button",
                    "Link",
                    "ProgressBar",
                    "LoadingIndicator",
                    "Tooltip",
                ],
                "navigation": ["Header", "Footer", "Tabs", "Tab", "TabPane"],
                "other": [],
            }

            # Categorize each widget
            categorized: Dict[str, List[str]] = {cat: [] for cat in categories}
            for widget in widgets:
                found = False
                for category, widget_list in categories.items():
                    if widget in widget_list:
                        categorized[category].append(widget)
                        found = True
                        break
                if not found:
                    categorized["other"].append(widget)

            response = {
                "widgets": widgets,
                "widget_info": widget_info,
                "categorized": categorized,
                "total_count": len(widgets),
                "source": "textual.widgets",
            }

            duration = time.time() - start_time
            log_tool_completion(tool_name, True, duration)

            return response

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Failed to list widget types: {str(e)}"
            log_tool_completion(tool_name, False, duration, error_msg)
            raise ToolExecutionError(tool_name, error_msg)

    @mcp.tool()
    async def list_event_handlers() -> Dict[str, Any]:
        """
        List all supported event handlers.

        Returns:
            Dictionary with supported event handlers and their descriptions
        """
        start_time = time.time()
        tool_name = "list_event_handlers"

        try:
            log_tool_execution(tool_name, {})

            generator = WidgetGenerator()
            event_handlers = generator.get_supported_event_handlers()

            handler_descriptions = {
                "click": "Handle button click events",
                "key_press": "Handle keyboard key press events",
                "input_changed": "Handle input field value changes",
                "focus": "Handle widget focus events",
                "blur": "Handle widget blur events",
                "mount": "Handle widget mount events",
                "default": "Generic event handler template",
            }

            response = {
                "event_handlers": event_handlers,
                "descriptions": handler_descriptions,
                "count": len(event_handlers),
            }

            duration = time.time() - start_time
            log_tool_completion(tool_name, True, duration)

            return response

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Failed to list event handlers: {str(e)}"
            log_tool_completion(tool_name, False, duration, error_msg)
            raise ToolExecutionError(tool_name, error_msg)

    @mcp.tool()
    async def validate_widget_name(
        widget_name: Annotated[
            str,
            Field(
                description="The widget name to validate against Python class naming conventions. Should be PascalCase without spaces or special characters.",
                min_length=1,
                max_length=100,
            ),
        ],
    ) -> Dict[str, Any]:
        """
        Validate a widget name for Python class naming conventions.

        Args:
            widget_name: The widget name to validate

        Returns:
            Dictionary with validation result and suggestions
        """
        start_time = time.time()
        tool_name = "validate_widget_name"

        try:
            log_tool_execution(tool_name, {"widget_name": widget_name})

            generator = WidgetGenerator()
            is_valid, error_message = generator.validate_widget_name(widget_name)

            suggestions = []
            if not is_valid:
                # Provide suggestions for common issues
                if not widget_name:
                    suggestions.append("Widget name cannot be empty")
                elif not widget_name.isidentifier():
                    # Clean up the name
                    clean_name = "".join(c for c in widget_name if c.isalnum() or c == "_")
                    if clean_name and clean_name[0].isdigit():
                        clean_name = "Widget" + clean_name
                    if clean_name:
                        # If already PascalCase after cleaning, keep it
                        if clean_name[0].isupper():
                            suggestions.append(f"Consider: {clean_name}")
                        else:
                            suggestions.append(f"Consider: {clean_name.capitalize()}")
                elif not widget_name[0].isupper():
                    suggestions.append(f"Consider: {widget_name.capitalize()}")

            response = {
                "valid": is_valid,
                "widget_name": widget_name,
                "error": error_message,
                "suggestions": suggestions,
            }

            duration = time.time() - start_time
            log_tool_completion(tool_name, True, duration)

            return response

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Widget name validation failed: {str(e)}"
            log_tool_completion(tool_name, False, duration, error_msg)
            raise ToolExecutionError(tool_name, error_msg)

    logger.info(
        "Registered widget tools: generate_widget, list_widget_types, list_event_handlers, validate_widget_name"
    )
