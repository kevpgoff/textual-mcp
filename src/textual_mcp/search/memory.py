"""VectorDB memory management for Textual documentation search."""

from typing import List, Dict, Any, Optional, TYPE_CHECKING
import asyncio
from pathlib import Path
import fnmatch

from ..utils.logging_config import get_logger

if TYPE_CHECKING:
    pass


class TextualDocsMemory:
    """Manages Textual documentation embeddings using VectorDB."""

    def __init__(
        self,
        embeddings: str = "BAAI/bge-base-en-v1.5",
        persist_path: Optional[Path] = None,
    ):
        """
        Initialize the VectorDB memory for Textual docs.

        Args:
            embeddings: Model name for embeddings
            persist_path: Optional path to persist the database
        """
        try:
            from vectordb import Memory
        except ImportError as e:
            raise ImportError(
                "VectorDB is required for documentation search. Install it with: uv add vectordb2"
            ) from e

        self.logger = get_logger("textual_docs_memory")

        # Initialize VectorDB with proper parameters
        memory_file = str(persist_path) if persist_path else None
        self.memory: Memory = Memory(memory_file=memory_file, embeddings=embeddings)
        self.embeddings = embeddings
        self.persist_path = persist_path

        if memory_file:
            self.logger.info(
                f"Initialized VectorDB with embeddings: {embeddings}, persisting to: {memory_file}"
            )
        else:
            self.logger.info(f"Initialized VectorDB with embeddings: {embeddings} (in-memory only)")

    def is_indexed(self) -> bool:
        """
        Check if the VectorDB memory has been indexed with documents.

        Returns:
            bool: True if documents have been indexed, False otherwise
        """
        try:
            # Check if memory has any entries
            has_docs = len(self.memory.memory) > 0
            if has_docs and self.persist_path:
                self.logger.debug(f"Found {len(self.memory.memory)} documents in persisted index")
            return has_docs
        except Exception as e:
            self.logger.debug(f"Database not indexed: {e}")
            # If there's an exception, assume the database is not indexed
            return False

    async def index_documents(self, documents: List[Dict[str, Any]], batch_size: int = 100) -> None:
        """
        Index documents into VectorDB.

        Args:
            documents: List of document chunks with metadata
            batch_size: Number of documents to process at once
        """
        self.logger.info(f"Indexing {len(documents)} documents in batches of {batch_size}")

        texts = []
        metadata = []

        for doc in documents:
            # Prepare text with context
            text = self._prepare_text_for_indexing(doc)
            texts.append(text)
            metadata.append(doc["metadata"])

        # Index in batches for better performance
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_metadata = metadata[i : i + batch_size]

            # VectorDB handles embedding internally
            await asyncio.to_thread(
                self.memory.save,
                batch_texts,
                batch_metadata,
            )
            self.logger.debug(
                f"Indexed batch {i // batch_size + 1}/{(len(texts) + batch_size - 1) // batch_size}"
            )

        self.logger.info(f"Successfully indexed {len(documents)} documents")

    def _prepare_text_for_indexing(self, doc: Dict[str, Any]) -> str:
        """Prepare document text with contextual information."""
        metadata = doc["metadata"]
        hierarchy = metadata.get("hierarchy", [])

        # Build contextual text
        context_parts = []

        # Add hierarchy as context
        if hierarchy:
            context_parts.append(" > ".join(hierarchy))

        # Add document path
        if "doc_path" in metadata:
            context_parts.append(f"File: {metadata['doc_path']}")

        # Add content type
        if metadata.get("content_type") == "code":
            lang = metadata.get("language", "python")
            context_parts.append(f"Code ({lang}):")

        # Combine context with actual text
        if context_parts:
            return "\n".join(context_parts) + "\n\n" + str(doc["text"])
        return str(doc["text"])

    async def search(
        self, query: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents.

        Args:
            query: Search query
            limit: Maximum results to return
            filters: Optional metadata filters

        Returns:
            List of search results with metadata and scores
        """
        self.logger.debug(f"Searching for: '{query}' with limit={limit}")

        # VectorDB handles query embedding internally
        raw_results = await asyncio.to_thread(
            self.memory.search,
            query,
            top_n=limit * 2 if filters else limit,  # Get more if filtering
            unique=True,
        )

        # Debug: Log raw results structure
        if raw_results:
            self.logger.debug(
                f"Raw VectorDB result sample: {raw_results[0] if raw_results else 'No results'}"
            )

        # Convert VectorDB results to our expected format
        results: List[Dict[str, Any]] = []
        if raw_results:
            for result in raw_results:
                # VectorDB returns {'chunk': text, 'metadata': metadata, 'distance': float}
                results.append(
                    {
                        "text": result.get("chunk", ""),
                        "metadata": result.get("metadata", {}),
                        "distance": result.get("distance", 0.0),
                    }
                )

        # Apply filters if provided
        if filters:
            results = self._apply_filters(results, filters)
            results = results[:limit]  # Trim to requested limit after filtering

        self.logger.debug(f"Found {len(results)} results")
        return results

    def _apply_filters(
        self, results: List[Dict[str, Any]], filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply metadata filters to search results."""
        filtered = []

        for result in results:
            metadata = result.get("metadata", {})
            match = True

            for key, value in filters.items():
                if key == "doc_path_pattern":
                    # Special handling for path pattern matching
                    doc_path = metadata.get("doc_path", "")
                    if not fnmatch.fnmatch(doc_path, value):
                        match = False
                        break
                elif key not in metadata:
                    match = False
                    break
                elif isinstance(value, list):
                    # For list values, check if metadata value is in the list
                    if metadata[key] not in value:
                        match = False
                        break
                elif metadata[key] != value:
                    match = False
                    break

            if match:
                filtered.append(result)

        return filtered

    async def clear(self) -> None:
        """Clear all indexed documents from memory."""
        try:
            # VectorDB has a clear method
            self.memory.clear()
            self.logger.info("Cleared all indexed documents")
        except Exception as e:
            self.logger.error(f"Failed to clear index: {e}")
            raise
