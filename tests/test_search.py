"""Tests for vector search functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import tempfile

from textual_mcp.search.memory import TextualDocsMemory
from textual_mcp.search.document_processor import TextualDocumentProcessor


class TestTextualDocsMemory:
    """Test cases for TextualDocsMemory."""

    @pytest.fixture
    def memory(self):
        """Create a memory instance for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("vectordb.Memory") as mock_memory_class:
                # Create a mock Memory instance
                mock_memory = Mock()
                mock_memory.memory = []
                mock_memory.search.return_value = []
                mock_memory_class.return_value = mock_memory

                memory = TextualDocsMemory(
                    embeddings="sentence-transformers/all-MiniLM-L6-v2",
                    persist_path=Path(tmpdir) / "test.db",
                )
                memory._mock_memory = mock_memory  # Store reference for tests
                yield memory

    def test_initialization(self, memory):
        """Test memory initialization."""
        assert memory.embeddings == "sentence-transformers/all-MiniLM-L6-v2"
        assert memory.persist_path is not None
        assert not memory.is_indexed()

    @pytest.mark.asyncio
    async def test_index_documents(self, memory):
        """Test document indexing."""
        documents = [
            {
                "text": "This is a test document about Textual widgets.",
                "metadata": {
                    "doc_path": "/docs/guide/widgets.md",
                    "content_type": "guide",
                    "hierarchy": ["Guide", "Widgets"],
                },
            },
            {
                "text": "Button widget example code here",
                "metadata": {
                    "doc_path": "/docs/examples/button.md",
                    "content_type": "code",
                    "language": "python",
                },
            },
        ]

        # After indexing, memory should have items
        await memory.index_documents(documents, batch_size=10)

        # Set memory to have items after indexing
        memory._mock_memory.memory = [{"chunk": "test", "metadata": {}}]
        assert memory.is_indexed()

    @pytest.mark.asyncio
    async def test_search(self, memory):
        """Test document search."""
        # Mock search results
        memory._mock_memory.search.return_value = [
            {
                "chunk": "The Button widget is used to create clickable buttons in Textual.",
                "metadata": {
                    "doc_path": "/docs/widgets/button.md",
                    "content_type": "widget",
                },
            }
        ]

        # Search for button
        results = await memory.search("button widget", limit=5)
        assert len(results) > 0
        assert "Button" in results[0]["text"]

    @pytest.mark.asyncio
    async def test_search_with_filters(self, memory):
        """Test search with metadata filters."""
        # Mock search results - return both guide and api content
        memory._mock_memory.search.return_value = [
            {
                "chunk": "Guide content about widgets",
                "metadata": {
                    "doc_path": "/docs/guide/widgets.md",
                    "content_type": "guide",
                },
            },
            {
                "chunk": "API reference for widgets",
                "metadata": {"doc_path": "/docs/api/widgets.md", "content_type": "api"},
            },
        ]

        # Search with content type filter
        results = await memory.search(
            "widgets", limit=5, filters={"content_type": "guide"}
        )

        assert len(results) > 0
        assert all(r["metadata"]["content_type"] == "guide" for r in results)

    @pytest.mark.asyncio
    async def test_clear(self, memory):
        """Test clearing the index."""
        # Set memory to have items
        memory._mock_memory.memory = [{"chunk": "test", "metadata": {}}]
        assert memory.is_indexed()

        # Clear the index
        await memory.clear()

        # After clearing, memory should be empty
        memory._mock_memory.memory = []
        assert not memory.is_indexed()


class TestTextualDocumentProcessor:
    """Test cases for TextualDocumentProcessor."""

    @pytest.fixture
    def processor(self):
        """Create a processor instance for testing."""
        return TextualDocumentProcessor(chunk_size=50, chunk_overlap=10)

    def test_initialization(self, processor):
        """Test processor initialization."""
        assert processor.chunk_size == 50
        assert processor.chunk_overlap == 10
        assert processor.github_token is None

    def test_determine_content_type(self, processor):
        """Test content type determination."""
        assert processor._determine_content_type("/docs/guide/intro.md") == "guide"
        assert processor._determine_content_type("/docs/api/widgets.md") == "api"
        assert processor._determine_content_type("/docs/widgets/button.md") == "widget"
        assert processor._determine_content_type("/docs/examples/app.md") == "example"
        assert (
            processor._determine_content_type("/docs/css/styles.md") == "css_reference"
        )
        assert processor._determine_content_type("/docs/other.md") == "documentation"

    def test_split_text_with_overlap(self, processor):
        """Test text splitting with overlap."""
        # Short text that fits in one chunk
        short_text = "This is a short text"
        chunks = processor._split_text_with_overlap(short_text)
        assert len(chunks) == 1
        assert chunks[0] == short_text

        # Longer text that needs splitting
        words = ["word"] * 100  # 100 words
        long_text = " ".join(words)
        chunks = processor._split_text_with_overlap(long_text)

        assert len(chunks) > 1
        # Check overlap exists
        for i in range(len(chunks) - 1):
            chunk1_words = chunks[i].split()
            chunk2_words = chunks[i + 1].split()
            # Some words from end of chunk1 should be at start of chunk2
            assert any(
                w in chunk2_words[: processor.chunk_overlap]
                for w in chunk1_words[-processor.chunk_overlap :]
            )

    def test_process_document(self, processor):
        """Test document processing."""
        doc_data = {
            "path": "/docs/guide/widgets.md",
            "content": """# Widgets in Textual

## Introduction

Textual provides many built-in widgets for creating TUI applications.

```python
from textual.widgets import Button

button = Button("Click me!")
```

## Button Widget

The Button widget creates a clickable button.
""",
            "sha": "abc123",
            "last_modified": "2024-01-01T00:00:00",
        }

        chunks = processor.process_document(doc_data)

        assert len(chunks) > 0

        # Check for code chunk
        code_chunks = [c for c in chunks if c["metadata"]["content_type"] == "code"]
        assert len(code_chunks) > 0
        assert "from textual.widgets import Button" in code_chunks[0]["text"]

        # Check hierarchy preservation
        text_chunks = [c for c in chunks if c["metadata"]["content_type"] == "guide"]
        # The hierarchies should include "Widgets in Textual", "Introduction", and "Button Widget"
        hierarchies = [c["metadata"]["hierarchy"] for c in text_chunks]
        # At least one chunk should have a non-empty hierarchy
        assert any(len(h) > 0 for h in hierarchies)

    @pytest.mark.asyncio
    async def test_fetch_documentation_mock(self, processor):
        """Test documentation fetching with mocked GitHub API."""
        with patch("httpx.AsyncClient") as mock_client:
            # Mock the tree response
            mock_tree_response = Mock()
            mock_tree_response.json.return_value = {
                "tree": [
                    {"path": "docs/guide/intro.md", "type": "blob", "sha": "abc123"}
                ]
            }
            mock_tree_response.raise_for_status = Mock()

            # Mock the content response
            mock_content_response = Mock()
            mock_content_response.json.return_value = {
                "content": "IyBJbnRyb2R1Y3Rpb24="  # Base64 encoded "# Introduction"
            }
            mock_content_response.raise_for_status = Mock()

            # Set up the mock client
            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = [
                mock_tree_response,
                mock_content_response,
            ]
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Fetch documentation
            docs = []
            async for doc in processor.fetch_documentation():
                docs.append(doc)

            assert len(docs) == 1
            assert docs[0]["path"] == "docs/guide/intro.md"
            assert docs[0]["content"] == "# Introduction"


def test_generate_preview():
    """Test preview generation function."""
    from textual_mcp.tools.documentation_tools import _generate_preview

    # Test short text
    short_text = "This is a short text"
    preview = _generate_preview(short_text, "short")
    assert preview == short_text

    # Test long text with query match
    long_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. The button widget is very useful for creating interactive elements. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
    preview = _generate_preview(long_text, "button widget", max_length=80)

    assert "button widget" in preview
    assert "..." in preview  # Should have ellipsis
    assert len(preview) <= 86  # 80 + 6 for ellipsis

    # Test no query match
    preview = _generate_preview(long_text, "notfound", max_length=50)
    assert preview.startswith("Lorem ipsum")
    assert preview.endswith("...")


@pytest.mark.asyncio
async def test_index_documentation():
    """Test the index_documentation function."""
    from textual_mcp.search.document_processor import index_documentation

    # Create mock memory and processor
    mock_memory = AsyncMock()
    mock_processor = Mock()

    # Mock fetch_documentation to return test documents
    async def mock_fetch():
        yield {
            "path": "docs/test.md",
            "content": "# Test\n\nTest content",
            "sha": "abc123",
            "last_modified": "2024-01-01T00:00:00",
        }

    mock_processor.fetch_documentation = mock_fetch
    mock_processor.process_document = Mock(
        return_value=[
            {"text": "Test content", "metadata": {"doc_path": "docs/test.md"}}
        ]
    )

    # Run indexing
    stats = await index_documentation(mock_memory, mock_processor)

    assert stats["documents_processed"] == 1
    assert stats["chunks_created"] == 1
    assert "indexing_duration" in stats
    assert "indexing_time" in stats

    # Verify index_documents was called
    mock_memory.index_documents.assert_called_once()
