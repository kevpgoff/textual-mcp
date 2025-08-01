# Textual MCP Server

A Model Context Protocol (MCP) server for building and managing Textual TUI applications. This server provides tools to validate CSS, generate widgets, analyze styles, and search Textual documentation.

## Overview

The Textual MCP Server enables AI assistants to help you develop Textual applications by providing:

- **CSS Validation**: Validate TCSS (Textual CSS) using Textual's native parser
- **Code Generation**: Generate boilerplate for widgets, layouts, and screens
- **Style Analysis**: Analyze CSS selectors, detect conflicts, and validate classes.
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
git clone https://github.com/kevpgoff/textual-mcp.git
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

- **`validate_tcss_file`** - Validate a TCSS file directly by path
  ```python
  # Example: Validate a CSS file
  await client.call_tool("validate_tcss_file", {
      "file_path": "styles/app.tcss",
      "watch": False
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

- **`generate_grid_layout`** - Generate grid layout code with specified rows and columns
  ```python
  # Example: Generate a 3x3 grid layout
  await client.call_tool("generate_grid_layout", {
      "rows": 3,
      "columns": 3,
      "areas": {
          "header": {"row": 0, "column": "0-2"},
          "sidebar": {"row": "1-2", "column": 0},
          "content": {"row": "1-2", "column": "1-2"}
      }
  })
  ```

### Widget Information Tools

- **`list_widget_types`** - List all available Textual widgets with descriptions
- **`list_event_handlers`** - List supported event handlers for widgets
- **`validate_widget_name`** - Validate widget names for Python naming conventions

### Analysis Tools (Coming Soon)

The following analysis tools are planned but not yet implemented:

- **`analyze_selectors`** - Analyze CSS selector usage and specificity (stub)
- **`detect_style_conflicts`** - Identify potential CSS conflicts (stub)

### Documentation Tools

- **`search_textual_docs`** - Semantic search across Textual documentation
  ```python
  # Example: Search for reactive properties info
  await client.call_tool("search_textual_docs", {
      "query": "how to create reactive properties",
      "limit": 5,
      "content_type": ["guide", "api"]  # Optional: filter by type
  })
  ```

- **`search_textual_code_examples`** - Search specifically for code examples
  ```python
  # Example: Find DataTable examples
  await client.call_tool("search_textual_code_examples", {
      "query": "DataTable sorting",
      "language": "python",
      "limit": 10
  })
  ```

- **`index_textual_docs`** - Manually trigger documentation indexing

## Vector Search Configuration

The Textual MCP Server includes semantic search capabilities for Textual documentation. This feature uses VectorDB2 for local embeddings and search.

### Setup Requirements

**Install Additional Dependencies**:

1. **GitHub Token** (Required for indexing):
   The documentation indexing requires a GitHub token to avoid API rate limits.

   Create a token at: https://github.com/settings/tokens/new
   - No special permissions needed (public access is sufficient)
   - Just used to increase rate limits from 60 to 5000 requests/hour

   Set it via environment variable:
   ```bash
   export GITHUB_TOKEN="your-github-token"
   ```

   Or add to `.env` file:
   ```bash
   GITHUB_TOKEN=your-github-token
   ```

2. **Configuration Options** (in `config/textual-mcp.yaml`):
   ```yaml
   search:
     auto_index: true  # Auto-index docs on first use
     embeddings_model: "BAAI/bge-base-en-v1.5"  # Embedding model
     persist_path: "./data/textual_docs.db"  # Where to store the index
     chunk_size: 200  # Text chunk size for indexing
     chunk_overlap: 20  # Overlap between chunks
     github_token: null  # Optional: for private repos
     default_limit: 10  # Default number of results
     similarity_threshold: 0.7  # Minimum similarity score
   ```

### Using Vector Search

The server automatically indexes Textual documentation on first use. You can also manually trigger indexing:

```bash

# Run the indexing script
uv run python scripts/index_documentation.py

# With custom settings
uv run python scripts/index_documentation.py --embeddings "sentence-transformers/all-MiniLM-L6-v2" --force
```

**Note**: Indexing requires approximately 300 GitHub API requests. Make sure you have sufficient rate limit available.

### Search Examples

1. **General Documentation Search**:
   ```python
   # Search across all documentation
   results = await search_textual_docs(
       query="reactive properties",
       limit=5
   )
   ```

2. **Filtered Search**:
   ```python
   # Search only in specific content types
   results = await search_textual_docs(
       query="CSS styling",
       content_type=["guide", "css_reference"],
       doc_path_pattern="*/css/*"
   )
   ```

3. **Code Example Search**:
   ```python
   # Find Python code examples
   results = await search_textual_code_examples(
       query="DataTable with sorting",
       language="python"
   )
   ```

### Content Types

The search system categorizes documentation into these types:
- `guide` - Tutorial and guide documents
- `api` - API reference documentation
- `widget` - Widget-specific documentation
- `example` - Code examples
- `css_reference` - CSS/styling documentation
- `code` - Code blocks within documentation

## Advanced Chunking with Chonkie

The Textual MCP Server uses [Chonkie](https://github.com/chonkie-inc/chonkie) for intelligent document chunking, providing content-aware processing that preserves semantic coherence. This system adapts its chunking strategy based on content type:

- **Code Examples**: Uses specialized code chunker that preserves code structure
- **API Documentation**: Uses semantic chunking with larger chunks to keep class/method documentation together
- **Guides**: Uses recursive markdown chunking that respects document structure
- **CSS Reference**: Uses semantic chunking with smaller chunks for individual properties

### Embedding Model Setup

Chonkie's semantic chunking requires embedding models. To avoid runtime download issues, pre-initialize the models:

```bash
# Quick start - download and convert default models
python scripts/init_embeddings.py
```

This will:
1. Download required embedding models from Hugging Face
2. Convert them to the efficient model2vec format
3. Store them in the `models/` directory
4. Create a model registry for easy lookup

### Available Embedding Models

The initialization script provides one model by default:
- `minishlab/potion-base-8M` - Primary model for semantic chunking


To add a custom model:
```bash
python scripts/init_embeddings.py --model "sentence-transformers/your-model" --output "your-model"
```

### Model Selection Priority

The system automatically selects models in this order:
1. Check for local pre-initialized models in `models/` directory
2. Use cached models from `~/.cache/huggingface/hub/` or `~/.cache/sentence_transformers/`
3. Fall back to downloading from Hugging Face

### Configuration Options

Control chunking behavior in `config/textual-mcp.yaml`:

```yaml
search:
  chunking_strategy: 'chonkie'  # Use 'manual' to disable semantic chunking
  # ... other settings
```

Set a custom models directory:
```bash
export TEXTUAL_MCP_MODELS_DIR=/path/to/your/models
python scripts/init_embeddings.py
```

### Troubleshooting

If you see the error:
```
"Folder does not exist locally, attempting to use huggingface hub."
```

This means models aren't initialized. Either:
1. Run `python scripts/init_embeddings.py` (recommended)
2. Ensure you have models cached from other projects
3. Set `chunking_strategy: 'manual'` to use simpler chunking without embeddings

The system gracefully falls back to simpler chunking methods if semantic models aren't available, ensuring functionality even without pre-downloaded models.

## Features

- **Native Textual Integration**: Uses Textual's TCSS parser for 100% compatibility
- **Intelligent Code Generation**: Context-aware templates for common patterns
- **Vector Search**: Semantic search for better documentation discovery with local embeddings
- **MCP Inspector Support**: Debug and test tools interactively

## License

MIT
