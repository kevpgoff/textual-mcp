"""Process Textual documentation for indexing."""

from mistletoe import Document
from mistletoe.block_token import (
    Heading,
    Paragraph,
    CodeFence,
    BlockCode,
    List as ListToken,
)
import httpx
from typing import List, Dict, Any, AsyncIterator, Optional, Union
from datetime import datetime
import base64

from ..utils.logging_config import get_logger


class TextualDocumentProcessor:
    """Process Textual documentation for indexing."""

    def __init__(self, chunk_size: int = 200, chunk_overlap: int = 20):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.github_token: Optional[str] = None  # Optional GitHub token for higher rate limits
        self.logger = get_logger("document_processor")

    def set_github_token(self, token: Optional[str]) -> None:
        """Set GitHub token for API access."""
        self.github_token = token
        if token:
            self.logger.info("GitHub token configured")

    async def check_rate_limit(self) -> Dict[str, Any]:
        """Check current GitHub API rate limit status."""
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get("https://api.github.com/rate_limit", headers=headers)
            response.raise_for_status()
            data = response.json()

            core_limits = data.get("rate", {})
            return {
                "limit": core_limits.get("limit", 0),
                "remaining": core_limits.get("remaining", 0),
                "reset": core_limits.get("reset", 0),
                "authenticated": self.github_token is not None,
            }

    async def fetch_documentation(self) -> AsyncIterator[Dict[str, Any]]:
        """Fetch Textual documentation from GitHub."""
        base_url = "https://api.github.com/repos/Textualize/textual"
        headers = {"Accept": "application/vnd.github.v3+json"}

        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        else:
            self.logger.warning(
                "No GitHub token configured. API rate limits may cause failures. "
                "Set GITHUB_TOKEN environment variable or github_token in config."
            )

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get documentation tree
            self.logger.info("Fetching documentation tree from GitHub")
            try:
                response = await client.get(
                    f"{base_url}/git/trees/main?recursive=1", headers=headers
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise ValueError(
                        "GitHub API authentication failed. Please provide a valid GitHub token.\n"
                        "You can:\n"
                        "1. Set GITHUB_TOKEN environment variable\n"
                        "2. Add 'github_token' to your config/textual-mcp.yaml\n"
                        "3. Create a token at: https://github.com/settings/tokens\n"
                        "   (No special permissions needed, just for rate limits)"
                    ) from e
                elif e.response.status_code == 403:
                    raise ValueError(
                        "GitHub API rate limit exceeded. Please provide a GitHub token.\n"
                        "Without authentication, you're limited to 60 requests/hour.\n"
                        "Set GITHUB_TOKEN environment variable or add to config."
                    ) from e
                elif e.response.status_code == 429:
                    # Check if we have a token
                    if self.github_token:
                        # Get rate limit info from headers
                        reset_timestamp = e.response.headers.get("X-RateLimit-Reset", "unknown")
                        remaining = e.response.headers.get("X-RateLimit-Remaining", "unknown")

                        # Convert timestamp to readable format
                        if reset_timestamp != "unknown":
                            import time

                            try:
                                reset_time = time.strftime(
                                    "%Y-%m-%d %H:%M:%S",
                                    time.localtime(int(reset_timestamp)),
                                )
                            except (ValueError, TypeError):
                                reset_time = reset_timestamp
                        else:
                            reset_time = "unknown"

                        raise ValueError(
                            "GitHub API rate limit exceeded (429) even with authentication.\n"
                            f"Remaining requests: {remaining}\n"
                            f"Rate limit resets at: {reset_time}\n"
                            "This might happen if:\n"
                            "1. You've made many requests recently\n"
                            "2. The token is invalid or has insufficient permissions\n"
                            "Try again later"
                        ) from e
                    else:
                        raise ValueError(
                            "GitHub API rate limit exceeded (429). Please provide a GitHub token.\n"
                            "Without authentication, you're limited to 60 requests/hour.\n"
                            "Set GITHUB_TOKEN environment variable or add to config."
                        ) from e
                else:
                    raise
            tree = response.json()

            # Filter for documentation files (excluding blog folder)
            doc_files = [
                item
                for item in tree["tree"]
                if item["path"].startswith("docs/")
                and item["path"].endswith(".md")
                and item["type"] == "blob"
                and not item["path"].startswith("docs/blog/")
            ]

            # Count excluded blog files for logging
            blog_files = [
                item
                for item in tree["tree"]
                if item["path"].startswith("docs/blog/")
                and item["path"].endswith(".md")
                and item["type"] == "blob"
            ]

            self.logger.info(
                f"Found {len(doc_files)} documentation files (excluded {len(blog_files)} blog files)"
            )

            # Fetch each file
            for file_info in doc_files:
                try:
                    response = await client.get(
                        f"{base_url}/contents/{file_info['path']}", headers=headers
                    )
                    response.raise_for_status()

                    content_data = response.json()
                    content = base64.b64decode(content_data["content"]).decode("utf-8")

                    yield {
                        "path": file_info["path"],
                        "content": content,
                        "sha": file_info["sha"],
                        "last_modified": datetime.now().isoformat(),
                    }

                    self.logger.debug(f"Fetched: {file_info['path']}")

                except Exception as e:
                    self.logger.error(f"Failed to fetch {file_info['path']}: {e}")
                    continue

    def process_document(self, doc_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process a single document into chunks."""
        try:
            doc = Document(doc_data["content"])
            chunks = []
            current_hierarchy: List[str] = []
            position = 0

            # Determine content type from path
            content_type = self._determine_content_type(doc_data["path"])

            # Handle case where doc.children might be None
            if not doc.children:
                self.logger.warning(f"Document {doc_data['path']} has no content")
                return []

            for token in doc.children:
                if isinstance(token, Heading):
                    # Update hierarchy
                    level = token.level
                    heading_text = self._get_text_content(token)
                    current_hierarchy = current_hierarchy[: level - 1] + [heading_text]

                # Process different token types
                if isinstance(token, (CodeFence, BlockCode)):
                    # Keep code blocks as single chunks
                    code_content = ""
                    if isinstance(token, CodeFence):
                        code_content = token.children[0].content if token.children else ""
                    elif isinstance(token, BlockCode):
                        code_content = token.children[0].content if token.children else ""

                    if code_content.strip():
                        chunks.append(
                            {
                                "text": code_content,
                                "metadata": {
                                    "doc_path": doc_data["path"],
                                    "hierarchy": current_hierarchy.copy(),
                                    "position": position,
                                    "content_type": "code",
                                    "language": getattr(token, "language", "python"),
                                    "sha": doc_data["sha"],
                                    "last_modified": doc_data["last_modified"],
                                },
                            }
                        )
                        position += 1

                elif isinstance(token, (Paragraph, ListToken)):
                    # Chunk text content
                    text = self._get_text_content(token)
                    if not text.strip():
                        continue

                    text_chunks = self._split_text_with_overlap(text)

                    for chunk_text in text_chunks:
                        chunks.append(
                            {
                                "text": chunk_text,
                                "metadata": {
                                    "doc_path": doc_data["path"],
                                    "hierarchy": current_hierarchy.copy(),
                                    "position": position,
                                    "content_type": content_type,
                                    "sha": doc_data["sha"],
                                    "last_modified": doc_data["last_modified"],
                                },
                            }
                        )
                        position += 1

            self.logger.debug(f"Processed {doc_data['path']} into {len(chunks)} chunks")
            return chunks

        except Exception as e:
            self.logger.error(f"Failed to process {doc_data['path']}: {e}")
            return []

    def _determine_content_type(self, path: str) -> str:
        """Determine content type from file path."""
        path_lower = path.lower()

        if "/guide/" in path_lower:
            return "guide"
        elif "/api/" in path_lower:
            return "api"
        elif "/widgets/" in path_lower:
            return "widget"
        elif "/examples/" in path_lower or "example" in path_lower:
            return "example"
        elif "/css/" in path_lower or "styles" in path_lower:
            return "css_reference"
        else:
            return "documentation"

    def _split_text_with_overlap(self, text: str) -> List[str]:
        """Split text into chunks with overlap."""
        words = text.split()
        chunks = []

        if len(words) <= self.chunk_size:
            # Text is small enough to be a single chunk
            return [text]

        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk = " ".join(words[i : i + self.chunk_size])
            if chunk:
                chunks.append(chunk)

        return chunks

    def _get_text_content(self, token: Any) -> str:
        """Recursively extract text content from AST token."""
        if hasattr(token, "content"):
            return str(token.content)
        elif hasattr(token, "children") and token.children is not None:
            text_parts = []
            for child in token.children:
                child_text = self._get_text_content(child)
                if child_text:
                    text_parts.append(child_text)
            return " ".join(text_parts)
        return ""


async def index_documentation(
    memory: Any, processor: Optional[TextualDocumentProcessor] = None
) -> Dict[str, Any]:
    """Index Textual documentation into VectorDB."""
    if processor is None:
        processor = TextualDocumentProcessor()

    logger = get_logger("index_documentation")
    logger.info("Starting documentation indexing")

    total_docs = 0
    total_chunks = 0
    start_time = datetime.now()

    # Process documents in batches
    batch = []
    batch_size = 50

    async for doc_data in processor.fetch_documentation():
        # Process document into chunks
        chunks = processor.process_document(doc_data)
        batch.extend(chunks)

        total_docs += 1
        total_chunks += len(chunks)

        # Index batch when it reaches the size limit
        if len(batch) >= batch_size:
            await memory.index_documents(batch)
            logger.info(f"Indexed batch: {len(batch)} chunks from {total_docs} documents")
            batch = []

    # Index remaining documents
    if batch:
        await memory.index_documents(batch)
        logger.info(f"Indexed final batch: {len(batch)} chunks")

    duration = (datetime.now() - start_time).total_seconds()

    result: Dict[str, Union[str, int, float]] = {
        "documents_processed": total_docs,
        "chunks_created": total_chunks,
        "indexing_duration": duration,
        "indexing_time": datetime.now().isoformat(),
    }

    logger.info(f"Indexing complete: {result}")
    return result
