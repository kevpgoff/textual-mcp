# Textual MCP Server

A Model Context Protocol (MCP) server for building and managing Textual TUI applications. This server provides tools to validate CSS, generate widgets, analyze styles, and search Textual documentation.

## Overview

The Textual MCP Server enables AI assistants to help you develop Textual applications by providing:

- **CSS Validation**: Validate TCSS (Textual CSS) using Textual's native parser
- **Code Generation**: Generate boilerplate for widgets, layouts, and screens
- **Style Analysis**: Analyze CSS selectors, detect conflicts, and extract variables
- **Documentation Search**: Semantic search through Textual docs and examples
- **Widget Information**: Get detailed information about Textual widgets and their properties

## Installation

### Prerequisites

Install `uv` if you haven't already:

```bash
# macOS
brew install uv

# Linux/Windows
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Clone and Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/textual-mcp.git
cd textual-mcp
```

2. Create virtual environment and install dependencies:
```bash
# Create a virtual environment
uv venv

# Activate it (Linux/macOS)
source .venv/bin/activate

# Activate it (Windows)
.venv\Scripts\activate

# Install dependencies
uv sync
```

3. Configure environment (optional):
```bash
cp .env.example .env
# Edit .env with your settings
```

## Usage

### Install in Claude Desktop
```bash
fastmcp install claude-desktop server.py --name "Textual MCP"
```

### Install in Claude Code  
```bash
fastmcp install claude-code server.py --name "Textual MCP"
```

### Install in Cursor
```bash
fastmcp install cursor server.py --name "Textual MCP"
```

### Run Development Server
```bash
# With MCP Inspector
fastmcp dev server.py

# Or directly with uv
uv run python server.py

# Or if venv is activated
python server.py
```

### Install with Additional Dependencies
If your server needs extra packages:
```bash
fastmcp install claude-desktop server.py \
  --name "Textual MCP" \
  --with pandas \
  --with requests
```

### Install with Environment Variables
```bash
fastmcp install claude-desktop server.py \
  --name "Textual MCP" \
  --env-file .env
```

### Generate MCP Configuration
```bash
# Generate and copy to clipboard
fastmcp install mcp-json server.py --copy

# Generate with specific dependencies
fastmcp install mcp-json server.py \
  --with textual \
  --with rich
```

## Development

### Install in Editable Mode
For development, install the package in editable mode:
```bash
uv pip install -e .
```

### Run Tests
```bash
uv run pytest
```

### Update Dependencies
```bash
# Add a new dependency
uv add new-package

# Update all dependencies
uv sync --upgrade
```

## Troubleshooting

### UV Not Found
If `fastmcp` commands fail with "uv not found", ensure uv is in your PATH:
```bash
which uv  # Should show the uv location
```

### Permission Errors
If you get permission errors on Windows, run as administrator or use:
```bash
uv venv --system-site-packages
```

## Available Tools

### Validation Tools

- **`validate_tcss`** - Validate TCSS content using Textual's native CSS parser
  ```python
  # Example: Validate CSS content
  await client.call_tool("validate_tcss", {
      "css_content": "Button { background: $primary; }",
      "strict_mode": False
  })
  ```

- **`validate_inline_styles`** - Check inline CSS declarations in Python code
- **`check_selector`** - Validate a single CSS selector for correctness

### Code Generation Tools

- **`generate_widget`** - Generate custom widget boilerplate code
  ```python
  # Example: Generate a custom button widget
  await client.call_tool("generate_widget", {
      "widget_name": "CustomButton",
      "widget_type": "input",
      "includes_css": True
  })
  ```

- **`generate_layout`** - Create grid or dock layout templates
- **`generate_screen`** - Generate a complete screen with widgets

### Analysis Tools

- **`analyze_selectors`** - Analyze CSS selector usage and specificity
- **`extract_css_variables`** - Find and list all CSS variables
- **`detect_style_conflicts`** - Identify potential CSS conflicts

### Documentation Tools

- **`search_documentation`** - Semantic search across Textual docs
  ```python
  # Example: Search for reactive properties info
  await client.call_tool("search_documentation", {
      "query": "how to create reactive properties",
      "limit": 5
  })
  ```

- **`get_widget_docs`** - Get detailed widget API documentation
- **`find_similar_examples`** - Find code examples similar to your snippet

## Features

- **Native Textual Integration**: Uses Textual's TCSS parser for 100% compatibility
- **Intelligent Code Generation**: Context-aware templates for common patterns
- **Vector Search**: Semantic search for better documentation discovery
- **MCP Inspector Support**: Debug and test tools interactively

## License

MIT