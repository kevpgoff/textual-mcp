"""Chonkie-based document processor for intelligent chunking."""

from typing import List, Dict, Any, Optional, Union, Sequence
from pathlib import Path
from chonkie import (
    SemanticChunker,
    SentenceChunker,
    RecursiveChunker,
    OverlapRefinery,
    Chunk,
)
from chonkie.types import SemanticChunk, SentenceChunk, RecursiveChunk
from chonkie.experimental import CodeChunker
import re
from ..config import TextualMCPConfig
from ..utils.logging_config import get_logger
from .model_manager import get_model_manager


class TextualChonkieProcessor:
    """Advanced document processor using Chonkie for intelligent chunking."""

    def __init__(self, config: TextualMCPConfig):
        """Initialize the Chonkie processor with configuration."""
        self.config = config
        self.logger = get_logger("chonkie_processor")

        # Get model manager
        self.model_manager = get_model_manager()

        # Determine which embedding model to use
        self.embedding_model = self._get_embedding_model()

        # Initialize different chunkers for different content types
        self.markdown_chunker = RecursiveChunker.from_recipe(
            "markdown", lang="en", chunk_size=config.search.chunk_size, min_characters_per_chunk=50
        )

        # Try to initialize semantic chunker, but allow fallback
        self.semantic_chunker: Optional[SemanticChunker] = None
        try:
            self.semantic_chunker = SemanticChunker(
                embedding_model=self.embedding_model,
                mode="window",
                threshold="auto",
                chunk_size=config.search.chunk_size,
                min_sentences=2,
                min_chunk_size=100,
                delim=[".", "!", "?", "\n"],
            )
            self.semantic_available = True
        except Exception as e:
            self.logger.warning(
                f"Semantic chunker initialization failed: {e}. Will use sentence chunker as fallback."
            )
            self.semantic_available = False

        # Sentence chunker as fallback
        self.sentence_chunker = SentenceChunker(
            tokenizer_or_token_counter="cl100k_base",
            chunk_size=config.search.chunk_size,
            chunk_overlap=config.search.chunk_overlap,
            min_sentences_per_chunk=2,
        )

        # Code chunker for code examples
        self.code_chunker = CodeChunker(language="python", chunk_size=config.search.chunk_size)

        # Overlap refinery for better context
        self.overlap_refinery = OverlapRefinery(
            tokenizer_or_token_counter="cl100k_base",
            context_size=0.25,  # 25% overlap
            method="suffix",
            merge=True,
        )

        self.logger.info(
            f"Initialized Chonkie processors with embedding model: {self.embedding_model}"
        )

    def _get_embedding_model(self) -> str:
        """Get the embedding model to use, checking for local models first."""
        # Use a lightweight model that's more likely to be cached
        # sentence-transformers models are commonly cached and work well
        default_model = "sentence-transformers/all-MiniLM-L6-v2"

        # Check if we have a models directory with pre-downloaded models
        models_dir = Path.home() / ".cache" / "textual_mcp" / "models"
        if models_dir.exists():
            # Look for potion model first (it's the best for semantic chunking)
            potion_path = models_dir / "potion-base-8M"
            if potion_path.exists():
                self.logger.info(f"Using local Potion model from {potion_path}")
                return str(potion_path)

        # Fall back to a common model that's likely cached
        self.logger.info(
            f"Using {default_model}. For better performance, run 'python scripts/init_embeddings.py'"
        )
        return default_model

    def process_document(self, doc_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process document with content-aware chunking."""
        content_type = self._determine_content_type(doc_data["path"])

        self.logger.debug(f"Processing {doc_data['path']} as {content_type}")

        if content_type == "code":
            return self._chunk_code_content(doc_data)
        elif content_type in ["api", "widget"]:
            return self._chunk_api_documentation(doc_data)
        elif content_type == "guide":
            return self._chunk_guide_content(doc_data)
        elif content_type == "css_reference":
            return self._chunk_css_reference(doc_data)
        else:
            return self._chunk_general_content(doc_data)

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
            return "code"
        elif "/css/" in path_lower or "styles" in path_lower:
            return "css_reference"
        else:
            return "documentation"

    def _chunk_code_content(self, doc_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Use specialized code chunking for code examples."""
        # Extract code blocks from markdown
        code_blocks = self._extract_code_blocks(doc_data["content"])
        chunks = []

        for block in code_blocks:
            # Keep code blocks intact if they're small enough
            if len(block["code"]) <= self.config.search.chunk_size * 4:  # Approximate token count
                chunks.append(
                    {
                        "text": block["code"],
                        "metadata": {
                            **doc_data,
                            "content_type": "code",
                            "language": block.get("language", "python"),
                            "context": block.get("context", ""),
                            "position": block.get("position", 0),
                        },
                    }
                )
            else:
                # Use code chunker for large blocks
                try:
                    code_chunks = self.code_chunker.chunk(block["code"])
                    for idx, chunk in enumerate(code_chunks):
                        chunks.append(
                            {
                                "text": chunk.text,
                                "metadata": {
                                    **doc_data,
                                    "content_type": "code",
                                    "language": block.get("language", "python"),
                                    "chunk_index": idx,
                                    "position": block.get("position", 0),
                                },
                            }
                        )
                except Exception as e:
                    self.logger.warning(
                        f"Code chunking failed, falling back to sentence chunker: {e}"
                    )
                    # Fallback to sentence chunker
                    sentence_chunks = self.sentence_chunker.chunk(block["code"])
                    for idx, chunk in enumerate(sentence_chunks):
                        chunks.append(
                            {
                                "text": chunk.text,
                                "metadata": {
                                    **doc_data,
                                    "content_type": "code",
                                    "language": block.get("language", "python"),
                                    "chunk_index": idx,
                                    "position": block.get("position", 0),
                                },
                            }
                        )

        # Also process surrounding text
        text_content = self._extract_text_content(doc_data["content"])
        if text_content:
            text_chunks = self.sentence_chunker.chunk(text_content)
            for chunk in text_chunks:
                chunks.append(
                    {
                        "text": chunk.text,
                        "metadata": {
                            **doc_data,
                            "content_type": "code_explanation",
                            "token_count": chunk.token_count,
                        },
                    }
                )

        return chunks

    def _chunk_api_documentation(self, doc_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Keep API documentation coherent by class/method."""
        # Try semantic chunker if available
        if self.semantic_available:
            try:
                # Use semantic chunker with larger chunks for API docs
                api_chunker = SemanticChunker(
                    embedding_model=self.embedding_model,
                    chunk_size=768,  # Larger chunks for API docs
                    min_chunk_size=256,
                    min_sentences=3,
                    mode="window",
                    threshold="auto",
                )
                chunks: Sequence[Union[SemanticChunk, RecursiveChunk]] = api_chunker.chunk(
                    doc_data["content"]
                )
            except Exception as e:
                self.logger.warning(
                    f"Semantic chunking failed, falling back to markdown chunker: {e}"
                )
                chunks = self.markdown_chunker.chunk(doc_data["content"])
        else:
            # Use markdown chunker if semantic not available
            chunks = self.markdown_chunker.chunk(doc_data["content"])

        # Enhance with API-specific metadata
        enhanced_chunks = []
        for chunk in chunks:
            # Extract class/method names from chunk
            class_name = self._extract_class_name(chunk.text)
            method_names = self._extract_method_names(chunk.text)

            enhanced_chunks.append(
                {
                    "text": chunk.text,
                    "metadata": {
                        **doc_data,
                        "content_type": "api",
                        "class_name": class_name,
                        "methods": method_names,
                        "token_count": chunk.token_count,
                    },
                }
            )

        # Add overlap for better context
        enhanced_chunks = self._add_overlap_context(enhanced_chunks)

        return enhanced_chunks

    def _chunk_guide_content(self, doc_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk guide content with markdown structure awareness."""
        try:
            chunks: Sequence[Union[RecursiveChunk, SemanticChunk, SentenceChunk]] = (
                self.markdown_chunker.chunk(doc_data["content"])
            )
        except Exception as e:
            self.logger.warning(f"Markdown chunking failed, falling back to semantic chunker: {e}")
            if self.semantic_available and self.semantic_chunker:
                chunks = self.semantic_chunker.chunk(doc_data["content"])
            else:
                chunks = self.sentence_chunker.chunk(doc_data["content"])

        enhanced_chunks = []
        for idx, chunk in enumerate(chunks):
            # Extract section hierarchy
            hierarchy = self._extract_hierarchy(chunk.text)

            enhanced_chunks.append(
                {
                    "text": chunk.text,
                    "metadata": {
                        **doc_data,
                        "content_type": "guide",
                        "hierarchy": hierarchy,
                        "position": idx,
                        "token_count": chunk.token_count,
                    },
                }
            )

        return enhanced_chunks

    def _chunk_css_reference(self, doc_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk CSS reference documentation."""
        # Try semantic chunker if available
        if self.semantic_available:
            try:
                # Use semantic chunker with smaller chunks for CSS properties
                css_chunker = SemanticChunker(
                    embedding_model=self.embedding_model,
                    chunk_size=384,
                    min_chunk_size=100,
                    min_sentences=2,
                    mode="window",
                    threshold="auto",
                )
                chunks: Sequence[Union[SemanticChunk, SentenceChunk]] = css_chunker.chunk(
                    doc_data["content"]
                )
            except Exception as e:
                self.logger.warning(
                    f"CSS semantic chunking failed, falling back to sentence chunker: {e}"
                )
                chunks = self.sentence_chunker.chunk(doc_data["content"])
        else:
            # Use sentence chunker if semantic not available
            chunks = self.sentence_chunker.chunk(doc_data["content"])

        enhanced_chunks = []
        for chunk in chunks:
            # Extract CSS properties and selectors
            properties = self._extract_css_properties(chunk.text)
            selectors = self._extract_css_selectors(chunk.text)

            enhanced_chunks.append(
                {
                    "text": chunk.text,
                    "metadata": {
                        **doc_data,
                        "content_type": "css_reference",
                        "css_properties": properties,
                        "css_selectors": selectors,
                        "token_count": chunk.token_count,
                    },
                }
            )

        return enhanced_chunks

    def _chunk_general_content(self, doc_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk general documentation content."""
        try:
            chunks: Sequence[Union[SemanticChunk, SentenceChunk]] = (
                self.semantic_chunker.chunk(doc_data["content"])
                if self.semantic_available and self.semantic_chunker
                else self.sentence_chunker.chunk(doc_data["content"])
            )
        except Exception as e:
            self.logger.warning(f"Semantic chunking failed, falling back to sentence chunker: {e}")
            chunks = self.sentence_chunker.chunk(doc_data["content"])

        enhanced_chunks = []
        for idx, chunk in enumerate(chunks):
            enhanced_chunks.append(
                {
                    "text": chunk.text,
                    "metadata": {
                        **doc_data,
                        "content_type": "documentation",
                        "position": idx,
                        "token_count": chunk.token_count,
                    },
                }
            )

        return enhanced_chunks

    def _extract_code_blocks(self, content: str) -> List[Dict[str, Any]]:
        """Extract code blocks from markdown content."""
        code_blocks = []

        # Pattern for fenced code blocks
        pattern = r"```(\w+)?\n(.*?)\n```"
        matches = re.finditer(pattern, content, re.DOTALL)

        for idx, match in enumerate(matches):
            language = match.group(1) or "python"
            code = match.group(2)

            # Get surrounding context (text before the code block)
            start = max(0, match.start() - 200)
            context = content[start : match.start()].strip()

            code_blocks.append(
                {"code": code, "language": language, "context": context, "position": idx}
            )

        return code_blocks

    def _extract_text_content(self, content: str) -> str:
        """Extract non-code text from markdown."""
        # Remove code blocks
        text = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
        # Remove inline code
        text = re.sub(r"`[^`]+`", "", text)
        return text.strip()

    def _extract_class_name(self, text: str) -> Optional[str]:
        """Extract class name from API documentation chunk."""
        # Look for class definitions
        match = re.search(r"class\s+(\w+)", text)
        if match:
            return match.group(1)

        # Look for class headers in markdown
        match = re.search(r"#+\s*(?:class\s+)?(\w+)\s*(?:\(|$)", text, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def _extract_method_names(self, text: str) -> List[str]:
        """Extract method names from API documentation chunk."""
        methods = []

        # Look for method definitions
        pattern = r"def\s+(\w+)\s*\("
        methods.extend(re.findall(pattern, text))

        # Look for method documentation patterns
        pattern = r"#+\s*(?:method\s+)?`(\w+)`"
        methods.extend(re.findall(pattern, text, re.IGNORECASE))

        return list(set(methods))  # Remove duplicates

    def _extract_hierarchy(self, text: str) -> List[str]:
        """Extract heading hierarchy from markdown text."""
        hierarchy = []

        # Find all headings
        pattern = r"^(#+)\s+(.+)$"
        matches = re.finditer(pattern, text, re.MULTILINE)

        current_levels = {}
        for match in matches:
            level = len(match.group(1))
            heading = match.group(2).strip()

            # Update hierarchy
            current_levels[level] = heading
            # Clear lower levels
            for current_level in list(current_levels.keys()):
                if current_level > level:
                    del current_levels[current_level]

            # Build current hierarchy
            hierarchy = [
                current_levels[current_level] for current_level in sorted(current_levels.keys())
            ]

        return hierarchy

    def _extract_css_properties(self, text: str) -> List[str]:
        """Extract CSS properties from text."""
        # Look for CSS property patterns
        pattern = r"(?:^|\s)([a-z-]+):\s*[^;]+;"
        properties = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)

        # Also look for documented properties
        doc_pattern = r"`([a-z-]+)`\s*(?:property|:)"
        properties.extend(re.findall(doc_pattern, text, re.IGNORECASE))

        return list(set(properties))

    def _extract_css_selectors(self, text: str) -> List[str]:
        """Extract CSS selectors from text."""
        # Look for common selector patterns
        selectors = []

        # Class selectors
        selectors.extend(re.findall(r"\.[a-zA-Z][\w-]*", text))

        # ID selectors
        selectors.extend(re.findall(r"#[a-zA-Z][\w-]*", text))

        # Element selectors in CSS context
        pattern = r"(?:^|\s)([a-zA-Z]+)\s*\{"
        selectors.extend(re.findall(pattern, text, re.MULTILINE))

        return list(set(selectors))

    def _add_overlap_context(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add overlapping context to chunks for better continuity."""
        if not chunks:
            return chunks

        # Extract text from chunks for refinery
        # Create Chunk objects for the refinery
        chunk_objects = []
        for i, c in enumerate(chunks):
            # Estimate token count based on character length (approximate)
            token_count = len(c["text"]) // 4  # Rough estimate: 4 chars per token
            chunk_objects.append(
                Chunk(
                    text=c["text"],
                    start_index=i * self.config.search.chunk_size,
                    end_index=(i + 1) * self.config.search.chunk_size,
                    token_count=token_count,
                )
            )

        try:
            refined = self.overlap_refinery(chunk_objects)

            # Merge refined chunks back with metadata
            enhanced_chunks = []
            for i, refined_chunk in enumerate(refined):
                if i < len(chunks):
                    chunk = chunks[i].copy()
                    # Deep copy metadata to avoid modifying original
                    import copy

                    chunk["metadata"] = copy.deepcopy(chunk["metadata"])
                    chunk["text"] = (
                        refined_chunk.text if hasattr(refined_chunk, "text") else chunk["text"]
                    )
                    chunk["metadata"]["has_overlap_context"] = True
                    enhanced_chunks.append(chunk)

            return enhanced_chunks
        except Exception as e:
            self.logger.warning(f"Overlap refinery failed: {e}")
            return chunks
