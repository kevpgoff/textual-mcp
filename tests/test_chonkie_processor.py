"""Tests for Chonkie-based document processor."""

import pytest
from unittest.mock import Mock, patch
from textual_mcp.search.chonkie_processor import TextualChonkieProcessor
from textual_mcp.config import TextualMCPConfig


class TestTextualChonkieProcessor:
    """Test cases for TextualChonkieProcessor."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        config = TextualMCPConfig()
        config.search.chunking_strategy = "chonkie"
        config.search.chunk_size = 512
        config.search.chunk_overlap = 50
        return config

    @pytest.fixture
    def processor(self, config):
        """Create a processor instance for testing."""
        # Mock all Chonkie imports to avoid dependency issues in tests
        with (
            patch("textual_mcp.search.chonkie_processor.RecursiveChunker") as mock_recursive,
            patch("textual_mcp.search.chonkie_processor.SemanticChunker") as mock_semantic,
            patch("textual_mcp.search.chonkie_processor.SentenceChunker") as mock_sentence,
            patch("textual_mcp.search.chonkie_processor.CodeChunker") as mock_code,
            patch("textual_mcp.search.chonkie_processor.OverlapRefinery") as mock_overlap,
        ):
            # Configure mocks
            mock_recursive.from_recipe.return_value = Mock()
            mock_semantic.return_value = Mock()
            mock_sentence.return_value = Mock()
            mock_code.return_value = Mock()
            mock_overlap.return_value = Mock()

            processor = TextualChonkieProcessor(config)

            # Store mocks for test access
            processor._mock_chunkers = {
                "recursive": mock_recursive,
                "semantic": mock_semantic,
                "sentence": mock_sentence,
                "code": mock_code,
                "overlap": mock_overlap,
            }

            return processor

    def test_initialization(self, processor, config):
        """Test processor initialization."""
        assert processor.config == config
        assert processor.markdown_chunker is not None
        assert processor.semantic_chunker is not None
        assert processor.sentence_chunker is not None
        assert processor.code_chunker is not None
        assert processor.overlap_refinery is not None

    def test_determine_content_type(self, processor):
        """Test content type determination."""
        assert processor._determine_content_type("/docs/guide/intro.md") == "guide"
        assert processor._determine_content_type("/docs/api/widgets.md") == "api"
        assert processor._determine_content_type("/docs/widgets/button.md") == "widget"
        assert processor._determine_content_type("/docs/examples/app.md") == "code"
        assert processor._determine_content_type("/docs/css/styles.md") == "css_reference"
        assert processor._determine_content_type("/docs/other.md") == "documentation"

    def test_extract_code_blocks(self, processor):
        """Test code block extraction from markdown."""
        content = """# Example

Here's a code example:

```python
from textual.app import App
from textual.widgets import Button

class MyApp(App):
    pass
```

And another one:

```css
Button {
    background: blue;
}
```
"""

        blocks = processor._extract_code_blocks(content)

        assert len(blocks) == 2
        assert blocks[0]["language"] == "python"
        assert "from textual.app import App" in blocks[0]["code"]
        assert blocks[1]["language"] == "css"
        assert "background: blue" in blocks[1]["code"]

    def test_extract_text_content(self, processor):
        """Test non-code text extraction."""
        content = """# Title

This is some text with `inline code` and more text.

```python
code block
```

More text here."""

        text = processor._extract_text_content(content)

        assert "This is some text with  and more text." in text
        assert "code block" not in text
        assert "More text here." in text

    def test_extract_class_name(self, processor):
        """Test class name extraction."""
        # Python class definition
        text1 = "class MyWidget(Widget):"
        assert processor._extract_class_name(text1) == "MyWidget"

        # Markdown heading
        text2 = "## class Button"
        assert processor._extract_class_name(text2) == "Button"

        # No class
        text3 = "This is just some text"
        assert processor._extract_class_name(text3) is None

    def test_extract_method_names(self, processor):
        """Test method name extraction."""
        text = """
def on_mount(self):
    pass

def compose(self):
    pass

## Method `update`
"""

        methods = processor._extract_method_names(text)

        assert "on_mount" in methods
        assert "compose" in methods
        assert "update" in methods

    def test_extract_css_properties(self, processor):
        """Test CSS property extraction."""
        text = """
Button {
    background: blue;
    color: white;
    border: solid red;
}

The `margin` property sets margins.
"""

        properties = processor._extract_css_properties(text)

        assert "background" in properties
        assert "color" in properties
        assert "border" in properties
        assert "margin" in properties

    def test_process_document_code_type(self, processor):
        """Test processing a code example document."""
        doc_data = {
            "path": "/docs/examples/button.md",
            "content": """# Button Example

```python
from textual.widgets import Button
button = Button("Click me")
```

This creates a button widget.
""",
            "sha": "abc123",
            "last_modified": "2024-01-01T00:00:00",
        }

        # Mock chunker responses
        mock_chunk = Mock()
        mock_chunk.text = 'from textual.widgets import Button\nbutton = Button("Click me")'
        mock_chunk.token_count = 20

        processor.code_chunker.chunk = Mock(return_value=[mock_chunk])
        processor.sentence_chunker.chunk = Mock(
            return_value=[Mock(text="This creates a button widget.", token_count=10)]
        )

        chunks = processor._chunk_code_content(doc_data)

        assert len(chunks) > 0
        # Should have both code and explanation chunks
        code_chunks = [c for c in chunks if c["metadata"]["content_type"] == "code"]
        explanation_chunks = [
            c for c in chunks if c["metadata"]["content_type"] == "code_explanation"
        ]

        assert len(code_chunks) > 0
        assert len(explanation_chunks) > 0

    def test_process_document_api_type(self, processor):
        """Test processing an API documentation."""
        doc_data = {
            "path": "/docs/api/button.md",
            "content": """# Button API

class Button(Widget):
    def on_click(self):
        pass
""",
            "sha": "abc123",
            "last_modified": "2024-01-01T00:00:00",
        }

        # Mock semantic chunker
        mock_chunk = Mock()
        mock_chunk.text = "class Button(Widget):\n    def on_click(self):"
        mock_chunk.token_count = 15

        # Create a temporary semantic chunker for this test
        with patch("textual_mcp.search.chonkie_processor.SemanticChunker") as mock_semantic_class:
            mock_api_chunker = Mock()
            mock_api_chunker.chunk = Mock(return_value=[mock_chunk])
            mock_semantic_class.return_value = mock_api_chunker

            chunks = processor._chunk_api_documentation(doc_data)

        assert len(chunks) > 0
        assert chunks[0]["metadata"]["content_type"] == "api"
        assert chunks[0]["metadata"]["class_name"] == "Button"
        assert "on_click" in chunks[0]["metadata"]["methods"]

    def test_process_document_guide_type(self, processor):
        """Test processing a guide document."""
        doc_data = {
            "path": "/docs/guide/widgets.md",
            "content": """# Widgets Guide

## Introduction

Learn about Textual widgets.
""",
            "sha": "abc123",
            "last_modified": "2024-01-01T00:00:00",
        }

        mock_chunk = Mock()
        mock_chunk.text = "# Widgets Guide\n\n## Introduction\n\nLearn about Textual widgets."
        mock_chunk.token_count = 20

        processor.markdown_chunker.chunk = Mock(return_value=[mock_chunk])

        chunks = processor._chunk_guide_content(doc_data)

        assert len(chunks) > 0
        assert chunks[0]["metadata"]["content_type"] == "guide"
        assert "hierarchy" in chunks[0]["metadata"]

    def test_process_document_css_type(self, processor):
        """Test processing CSS reference documentation."""
        doc_data = {
            "path": "/docs/css/properties.md",
            "content": """# CSS Properties

Button {
    background: blue;
    margin: 1;
}
""",
            "sha": "abc123",
            "last_modified": "2024-01-01T00:00:00",
        }

        # Create a mock for CSS chunking
        with patch("textual_mcp.search.chonkie_processor.SemanticChunker") as mock_semantic_class:
            mock_css_chunker = Mock()
            mock_chunk = Mock()
            mock_chunk.text = "Button {\n    background: blue;\n    margin: 1;\n}"
            mock_chunk.token_count = 15
            mock_css_chunker.chunk = Mock(return_value=[mock_chunk])
            mock_semantic_class.return_value = mock_css_chunker

            chunks = processor._chunk_css_reference(doc_data)

        assert len(chunks) > 0
        assert chunks[0]["metadata"]["content_type"] == "css_reference"
        assert "background" in chunks[0]["metadata"]["css_properties"]
        assert "margin" in chunks[0]["metadata"]["css_properties"]

    def test_add_overlap_context(self, processor):
        """Test adding overlap context to chunks."""
        chunks = [
            {"text": "First chunk text", "metadata": {"position": 0}},
            {"text": "Second chunk text", "metadata": {"position": 1}},
        ]

        # Test the case where overlap refinery fails (common in tests)
        processor.overlap_refinery.__call__ = Mock(side_effect=Exception("Mock failure"))

        result = processor._add_overlap_context(chunks)

        # Should return original chunks when refinery fails
        assert len(result) == 2
        assert result[0]["text"] == "First chunk text"
        assert result[1]["text"] == "Second chunk text"

    def test_process_document_fallback_to_sentence_chunker(self, processor):
        """Test fallback to sentence chunker when semantic fails."""
        doc_data = {
            "path": "/docs/other/misc.md",
            "content": "Some general documentation content.",
            "sha": "abc123",
            "last_modified": "2024-01-01T00:00:00",
        }

        # Make semantic chunker fail
        processor.semantic_chunker.chunk = Mock(side_effect=Exception("Semantic chunking failed"))

        # Mock sentence chunker
        mock_chunk = Mock()
        mock_chunk.text = "Some general documentation content."
        mock_chunk.token_count = 10
        processor.sentence_chunker.chunk = Mock(return_value=[mock_chunk])

        chunks = processor._chunk_general_content(doc_data)

        assert len(chunks) > 0
        assert chunks[0]["text"] == "Some general documentation content."

        # Verify sentence chunker was called
        processor.sentence_chunker.chunk.assert_called_once()
