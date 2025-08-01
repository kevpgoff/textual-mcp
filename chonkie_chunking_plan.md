# Chonkie-Based Chunking Strategy for Textual MCP

## Executive Summary

After reviewing the Chonkie library's capabilities, I propose replacing our current manual chunking implementation with Chonkie's advanced chunking strategies. Chonkie offers semantic-aware, recursive, and specialized chunking methods that would significantly improve our documentation search quality while reducing implementation complexity.

## Current Implementation Limitations vs Chonkie Solutions

### 1. Word-Based Splitting → Semantic Chunking
**Current Issue**: Our implementation splits on arbitrary word boundaries without considering semantic meaning.

**Chonkie Solution**: Use `SemanticChunker` to group content based on semantic similarity:
```python
from chonkie import SemanticChunker

chunker = SemanticChunker(
    embedding_model="all-mpnet-base-v2",  # Lightweight model
    mode="window",
    threshold="auto",  # Automatic threshold calculation
    chunk_size=512,  # Larger chunks as recommended
    min_sentences=1,
    min_chunk_size=100,
    delim=['.', '!', '?', '\n'],
)
```

### 2. No Sentence Awareness → Sentence-Based Chunking
**Current Issue**: Chunks can split mid-sentence, breaking context.

**Chonkie Solution**: Use `SentenceChunker` as a base or fallback:
```python
from chonkie import SentenceChunker

sentence_chunker = SentenceChunker(
    tokenizer="cl100k_base",  # OpenAI tokenizer for accuracy
    chunk_size=512,
    chunk_overlap=128,
    min_sentences_per_chunk=2
)
```

### 3. Limited Markdown Support → Recursive Markdown Chunking
**Current Issue**: Basic markdown parsing without respecting document structure.

**Chonkie Solution**: Use `RecursiveChunker` with markdown-specific rules:
```python
from chonkie import RecursiveChunker

markdown_chunker = RecursiveChunker.from_recipe(
    "markdown",
    lang="en",
    chunk_size=512,
    min_characters_per_chunk=100
)
```

## Proposed Implementation Architecture

### 1. Content-Aware Chunking Pipeline

```python
from chonkie import RecursiveChunker, SemanticChunker, CodeChunker
from chonkie.experimental import CodeChunker as ExperimentalCodeChunker
from typing import List, Dict, Any

class TextualChonkieProcessor:
    """Advanced document processor using Chonkie for intelligent chunking."""

    def __init__(self, config: TextualMCPConfig):
        # Initialize different chunkers for different content types
        self.markdown_chunker = RecursiveChunker.from_recipe(
            "markdown",
            lang="en",
            chunk_size=config.search.chunk_size,
            min_characters_per_chunk=50
        )

        self.semantic_chunker = SemanticChunker(
            embedding_model="all-mpnet-base-v2",
            mode="window",
            threshold="auto",
            chunk_size=config.search.chunk_size,
            min_sentences=2,
            min_chunk_size=100
        )

        # For code examples
        self.code_chunker = ExperimentalCodeChunker(
            language="python",
            chunk_size=config.search.chunk_size
        )

    def process_document(self, doc_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process document with content-aware chunking."""
        content_type = self._determine_content_type(doc_data["path"])

        if content_type == "code":
            return self._chunk_code_content(doc_data)
        elif content_type in ["api", "widget"]:
            return self._chunk_api_documentation(doc_data)
        elif content_type == "guide":
            return self._chunk_guide_content(doc_data)
        else:
            return self._chunk_general_content(doc_data)
```

### 2. Enhanced Code Chunking

```python
def _chunk_code_content(self, doc_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Use specialized code chunking for code examples."""
    # Extract code blocks from markdown
    code_blocks = self._extract_code_blocks(doc_data["content"])
    chunks = []

    for block in code_blocks:
        # Keep code blocks intact if they fit
        if len(self.tokenizer.encode(block["code"])) <= self.chunk_size:
            chunks.append({
                "text": block["code"],
                "metadata": {
                    **doc_data,
                    "content_type": "code",
                    "language": block.get("language", "python"),
                    "context": block.get("context", "")
                }
            })
        else:
            # Use code chunker for large blocks
            code_chunks = self.code_chunker.chunk(block["code"])
            for chunk in code_chunks:
                chunks.append({
                    "text": chunk.text,
                    "metadata": {
                        **doc_data,
                        "content_type": "code",
                        "language": block.get("language", "python"),
                        "chunk_index": chunk.start_index
                    }
                })

    return chunks
```

### 3. API Documentation Chunking

```python
def _chunk_api_documentation(self, doc_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Keep API documentation coherent by class/method."""
    # Use semantic chunker with higher min_chunk_size
    api_chunker = SemanticChunker(
        embedding_model=self.semantic_chunker.embedding_model,
        chunk_size=768,  # Larger chunks for API docs
        min_chunk_size=256,
        min_sentences=3
    )

    chunks = api_chunker.chunk(doc_data["content"])

    # Enhance with API-specific metadata
    enhanced_chunks = []
    for chunk in chunks:
        # Extract class/method names from chunk
        class_name = self._extract_class_name(chunk.text)
        method_names = self._extract_method_names(chunk.text)

        enhanced_chunks.append({
            "text": chunk.text,
            "metadata": {
                **doc_data,
                "content_type": "api",
                "class_name": class_name,
                "methods": method_names,
                "token_count": chunk.token_count
            }
        })

    return enhanced_chunks
```

### 4. Late Chunking for Enhanced Retrieval

```python
from chonkie import LateChunker

class TextualLateChunkingProcessor:
    """Implements late chunking strategy for better semantic search."""

    def __init__(self, config: TextualMCPConfig):
        self.late_chunker = LateChunker(
            embedding_model="all-MiniLM-L6-v2",
            chunk_size=config.search.chunk_size,
            min_characters_per_chunk=50
        )

    def create_late_chunks(self, doc_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate chunks with document-level context embeddings."""
        # Late chunking preserves document-level semantics
        chunks = self.late_chunker.chunk(doc_data["content"])

        enhanced_chunks = []
        for chunk in chunks:
            enhanced_chunks.append({
                "text": chunk.text,
                "metadata": {
                    **doc_data,
                    "has_document_context": True,
                    "chunk_level": chunk.level if hasattr(chunk, 'level') else 0
                },
                # Late chunking provides richer embeddings
                "embedding_context": "document_aware"
            })

        return enhanced_chunks
```

## Implementation Recommendations

### 1. Configuration Updates

```yaml
# config/textual-mcp.yaml
search:
  # Chunking strategy
  chunking_strategy: "chonkie"  # "manual" | "chonkie"

  # Chonkie-specific settings
  chonkie:
    default_chunker: "semantic"  # "token" | "sentence" | "semantic" | "recursive"

    # Model for semantic chunking
    embedding_model: "all-mpnet-base-v2"

    # Content-type specific settings
    content_types:
      code:
        chunker: "experimental_code"
        chunk_size: 512
        language: "python"

      api:
        chunker: "semantic"
        chunk_size: 768
        min_chunk_size: 256

      guide:
        chunker: "recursive"
        recipe: "markdown"
        chunk_size: 512

      css_reference:
        chunker: "semantic"
        chunk_size: 384
        min_sentences: 2
```

### 3. Chunking Refinement with Overlap

```python
from chonkie import OverlapRefinery

def add_context_overlap(chunks: List[Any]) -> List[Any]:
    """Add overlapping context to chunks for better continuity."""
    refinery = OverlapRefinery(
        tokenizer_or_token_counter="cl100k_base",
        context_size=0.25,  # 25% overlap
        method="suffix",
        merge=True
    )

    return refinery(chunks)
```

## Performance Benefits

### 1. Better Semantic Coherence
- Chonkie's semantic chunking maintains topic boundaries
- Reduced information fragmentation
- Better context preservation

### 2. Improved Search Quality
- Semantic similarity-based chunking improves retrieval
- Late chunking provides document-aware embeddings
- Content-type specific chunking optimizes for different use cases

### 3. Reduced Implementation Complexity
- Leverage battle-tested chunking strategies
- Eliminate custom splitting logic
- Built-in support for various tokenizers

### 4. Scalability
- Batch processing support for efficient indexing
- Async-compatible implementations
- Memory-efficient chunk representations

## Testing Strategy

### 1. Quality Metrics
```python
# Compare chunking quality
from chonkie import Visualizer

viz = Visualizer()

# Compare old vs new chunks
old_chunks = current_processor.process_document(test_doc)
new_chunks = chonkie_processor.process_document(test_doc)

# Visualize differences
viz.save("old_chunks.html", old_chunks)
viz.save("new_chunks.html", new_chunks)
```

### 2. Search Quality Tests
- Compare search results with queries like:
  - "How to create a custom widget"
  - "CSS grid layout examples"
  - "Button click event handling"
- Measure relevance scores and user satisfaction

## Installation

```bash
uv add "chonkie --optional semantic"
```

## Conclusion

Adopting Chonkie for the Textual MCP chunking strategy will provide:
1. **Better search quality** through semantic-aware chunking
2. **Reduced complexity** by leveraging proven implementations
3. **Content-specific optimization** for different documentation types
4. **Future-proof architecture** with support for advanced techniques like late chunking

The implementation provides immediate benefits in search quality and maintainability.
