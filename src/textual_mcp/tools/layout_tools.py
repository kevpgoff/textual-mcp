"""MCP tools for layout generation and assistance."""

import time
from typing import Dict, Any, List, Optional, Annotated
from pydantic import Field

from ..config import TextualMCPConfig
from ..utils.logging_config import log_tool_execution, log_tool_completion, get_logger
from ..utils.errors import ToolExecutionError


def register_layout_tools(mcp: Any, config: TextualMCPConfig) -> None:
    """Register all layout tools with the MCP server."""

    logger = get_logger("layout_tools")

    @mcp.tool()
    async def generate_grid_layout(
        rows: Annotated[
            int,
            Field(description="Number of grid rows to create in the layout.", ge=1, le=20),
        ],
        columns: Annotated[
            int,
            Field(
                description="Number of grid columns to create in the layout.",
                ge=1,
                le=20,
            ),
        ],
        gap: Annotated[
            Optional[str],
            Field(
                description="Gap between grid items (e.g., '1' for 1 unit gap, '2 1' for 2 vertical and 1 horizontal gap). Uses Textual spacing units.",
                pattern=r"^\d+(\s+\d+)?$",
            ),
        ] = None,
        areas: Annotated[
            Optional[List[str]],
            Field(
                description="List of grid area definitions for named grid areas. Each string defines areas for a row (e.g., ['header header', 'sidebar content']).",
                min_length=0,
                max_length=20,
            ),
        ] = None,
    ) -> Dict[str, Any]:
        """
        Generate grid layout CSS for Textual.

        Args:
            rows: Number of grid rows
            columns: Number of grid columns
            gap: Gap between grid items (e.g., "1", "2 1")
            areas: List of grid area definitions

        Returns:
            Dictionary with generated grid CSS and example
        """
        start_time = time.time()
        tool_name = "generate_grid_layout"

        try:
            log_tool_execution(
                tool_name,
                {
                    "rows": rows,
                    "columns": columns,
                    "gap": gap,
                    "areas_count": len(areas) if areas else 0,
                },
            )

            # Generate grid template
            " ".join(["1fr"] * rows)
            " ".join(["1fr"] * columns)

            css_parts = ["layout: grid;", f"grid-size: {columns} {rows};"]

            if gap:
                css_parts.append(f"grid-gutter: {gap};")

            # Add grid areas if provided
            if areas:
                for i, area in enumerate(areas):
                    css_parts.append(f"/* Grid area {i + 1}: {area} */")

            css = "\n".join([f"    {part}" for part in css_parts])

            # Generate example HTML structure
            total_items = rows * columns
            example_html = f'''# Grid Layout Example

```python
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Static, Label

class GridApp(App):
    CSS = """
    .grid-container {{
{css}
    }}

    .grid-item {{
        border: solid $primary;
        padding: 1;
        text-align: center;
    }}
    """

    def compose(self) -> ComposeResult:
        with Container(classes="grid-container"):
            # Generate {total_items} grid items ({rows} rows x {columns} columns)
            for i in range({total_items}):
                yield Label(f"Item {{i+1}}", classes="grid-item")
```
'''

            response = {"css": css, "example_html": example_html}

            duration = time.time() - start_time
            log_tool_completion(tool_name, True, duration)

            return response

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Grid layout generation failed: {str(e)}"
            log_tool_completion(tool_name, False, duration, error_msg)
            raise ToolExecutionError(tool_name, error_msg)

    def _generate_grid_items(count: int) -> str:
        """Generate grid item widgets for the example."""
        items = []
        for i in range(count):
            items.append(f'            yield Static(f"Item {i + 1}", classes="grid-item")')
        return "\n".join(items)

    logger.info("Registered layout tools: generate_grid_layout")
