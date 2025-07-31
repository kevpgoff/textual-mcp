"""Pytest configuration and fixtures for Textual MCP Server tests."""

import pytest
import tempfile
import os
from pathlib import Path
from typing import Generator
import asyncio

from fastmcp import Client

from textual_mcp.config import TextualMCPConfig, ValidatorConfig
from textual_mcp.validators.tcss_validator import TCSSValidator
from textual_mcp.validators.inline_validator import InlineValidator
from textual_mcp.validators.selector_validator import SelectorValidator
from textual_mcp.server import TextualMCPServer


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_css() -> str:
    """Sample CSS content for testing."""
    return """
Button {
    background: $primary;
    color: $text;
    border: solid $accent;
    padding: 1 2;
}

Button:hover {
    background: $primary-darken-1;
}

.custom-button {
    width: 100%;
    height: 3;
}

#main-button {
    dock: top;
    margin: 1;
}
"""


@pytest.fixture
def invalid_css() -> str:
    """Invalid CSS content for testing."""
    return """
Button {
    background: invalid-color;
    unknown-property: value;
    padding: ;
}

.invalid-selector- {
    color: red
}
"""


@pytest.fixture
def test_config() -> TextualMCPConfig:
    """Test configuration."""
    return TextualMCPConfig(
        validators=ValidatorConfig(
            strict_mode=False,
            cache_enabled=False,  # Disable cache for tests
            max_file_size=1024 * 1024,  # 1MB
            timeout=10,
        )
    )


@pytest.fixture
def tcss_validator(test_config: TextualMCPConfig) -> TCSSValidator:
    """TCSS validator instance for testing."""
    return TCSSValidator(test_config.validators)


@pytest.fixture
def inline_validator() -> InlineValidator:
    """Inline validator instance for testing."""
    return InlineValidator()


@pytest.fixture
def selector_validator() -> SelectorValidator:
    """Selector validator instance for testing."""
    return SelectorValidator()


@pytest.fixture
def sample_css_file(temp_dir: Path, sample_css: str) -> Path:
    """Create a temporary CSS file with sample content."""
    css_file = temp_dir / "test.tcss"
    css_file.write_text(sample_css)
    return css_file


@pytest.fixture
def invalid_css_file(temp_dir: Path, invalid_css: str) -> Path:
    """Create a temporary CSS file with invalid content."""
    css_file = temp_dir / "invalid.tcss"
    css_file.write_text(invalid_css)
    return css_file


# Test data fixtures
@pytest.fixture
def sample_selectors() -> list[str]:
    """Sample CSS selectors for testing."""
    return [
        "Button",
        ".custom-class",
        "#unique-id",
        "Button.active",
        "Container > Button",
        "Button:hover",
        "Button::before",
        "[data-test='value']",
        "Button.primary:hover",
        "#main .sidebar Button.active",
    ]


@pytest.fixture
def sample_inline_styles() -> list[str]:
    """Sample inline style strings for testing."""
    return [
        "color: red; background: blue;",
        "padding: 1 2; margin: 0;",
        "width: 100%; height: auto;",
        "border: solid $primary;",
        "display: none;",
        "color: red",  # Missing semicolon
        "invalid-property: value;",  # Invalid property
        "",  # Empty string
    ]


# Mock fixtures for external dependencies
@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client for testing."""

    class MockQdrantClient:
        def __init__(self):
            self.collections = {}

        async def search(self, collection_name: str, query_vector, limit: int = 5):
            return []

        async def upsert(self, collection_name: str, points):
            pass

        def get_collection(self, collection_name: str):
            return self.collections.get(collection_name)

    return MockQdrantClient()


@pytest.fixture
def mock_embedding_model():
    """Mock embedding model for testing."""

    class MockEmbeddingModel:
        def encode(self, texts, batch_size=32):
            import numpy as np

            if isinstance(texts, str):
                return np.random.rand(384)  # Mock embedding dimension
            return np.random.rand(len(texts), 384)

    return MockEmbeddingModel()


# FastMCP Server fixtures
@pytest.fixture
def mcp_server(test_config: TextualMCPConfig) -> TextualMCPServer:
    """Create a TextualMCPServer instance for testing."""
    server = TextualMCPServer(test_config)
    return server


@pytest.fixture
def mcp_client(mcp_server: TextualMCPServer) -> Client:
    """Create a FastMCP Client connected to the test server."""
    # Return the client directly for use with async with in tests
    return Client(mcp_server.mcp)


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Environment setup
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    # Disable logging during tests
    os.environ["LOG_LEVEL"] = "CRITICAL"

    # Use test configuration
    os.environ["TEXTUAL_MCP_TEST_MODE"] = "1"

    yield

    # Clean up
    os.environ.pop("LOG_LEVEL", None)
    os.environ.pop("TEXTUAL_MCP_TEST_MODE", None)
