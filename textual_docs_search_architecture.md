# Textual Documentation Search Architecture

## Overview

This document outlines the architecture for a semantic search system for Textual documentation using:
- **Embedding Model**: nomic-embed-text-v2-moe (Nomic AI)
- **Vector Database**: Qdrant (local deployment)
- **Documentation Source**: Textual GitHub repository

## System Components

### 1. Data Ingestion Pipeline

#### 1.1 Documentation Fetcher
- **Purpose**: Retrieve Textual documentation from GitHub without cloning the entire repository
- **Implementation**:
  ```python
  # Use GitHub API to fetch documentation structure
  GET https://api.github.com/repos/Textualize/textual/git/trees/main?recursive=1
  
  # Filter for docs/ directory
  # Fetch individual files using Contents API
  GET https://api.github.com/repos/Textualize/textual/contents/{file_path}
  ```
- **Features**:
  - Incremental updates (track file SHA for changes)
  - Rate limit handling (5,000 requests/hour)
  - Retry logic with exponential backoff
  - Cache mechanism for unchanged files

#### 1.2 Document Parser (Using Mistletoe)
- **Purpose**: Extract and preprocess markdown content using mistletoe parser
- **Implementation**: Leverages [mistletoe](https://github.com/miyuchina/mistletoe) - a fast, extensible and spec-compliant Markdown parser
- **Features**:
  - Parse markdown into AST (Abstract Syntax Tree) for structured processing
  - Extract metadata (file path, section headers, last modified)
  - Clean and normalize text content while preserving structure
  - Preserve code examples integrity through AST-aware processing
  - Support for CommonMark specification
- **Example**:
  ```python
  import mistletoe
  from mistletoe import Document
  from mistletoe.block_token import Heading, Paragraph, CodeFence, BlockCode
  from mistletoe.span_token import RawText, InlineCode
  
  class TextualDocParser:
      def parse_markdown(self, content):
          """Parse markdown content into structured data"""
          doc = Document(content)
          return self._extract_sections(doc)
      
      def _extract_sections(self, doc):
          """Extract sections with hierarchy from AST"""
          sections = []
          current_hierarchy = []
          
          for token in doc.children:
              if isinstance(token, Heading):
                  # Update hierarchy based on heading level
                  heading_text = self._get_text_content(token)
                  level = token.level
                  current_hierarchy = current_hierarchy[:level-1] + [heading_text]
                  
                  sections.append({
                      'type': 'heading',
                      'level': level,
                      'text': heading_text,
                      'hierarchy': current_hierarchy.copy()
                  })
              elif isinstance(token, Paragraph):
                  sections.append({
                      'type': 'paragraph',
                      'text': self._get_text_content(token),
                      'hierarchy': current_hierarchy.copy()
                  })
              elif isinstance(token, (CodeFence, BlockCode)):
                  sections.append({
                      'type': 'code',
                      'language': getattr(token, 'language', ''),
                      'code': token.children[0].content if token.children else '',
                      'hierarchy': current_hierarchy.copy()
                  })
          
          return sections
      
      def _get_text_content(self, token):
          """Recursively extract text from token"""
          if isinstance(token, RawText):
              return token.content
          elif hasattr(token, 'children'):
              return ''.join(self._get_text_content(child) for child in token.children)
          return ''
  ```

### 2. Text Processing Pipeline

#### 2.1 Document Chunker
- **Strategy**: Hybrid approach combining semantic and structural chunking using mistletoe AST
- **Implementation**:
  ```python
  import mistletoe
  from mistletoe import Document
  from mistletoe.block_token import Heading, Paragraph, CodeFence, BlockCode, List
  from mistletoe.span_token import RawText
  
  class TextualDocChunker:
      def __init__(self, chunk_size=200, overlap=20):
          self.chunk_size = chunk_size
          self.overlap = overlap
      
      def chunk_document(self, content, doc_path):
          """Chunk document using mistletoe AST for structure-aware splitting"""
          doc = Document(content)
          chunks = []
          current_hierarchy = []
          position = 0
          
          for token in doc.children:
              if isinstance(token, Heading):
                  # Update hierarchy
                  level = token.level
                  heading_text = self._get_text_content(token)
                  current_hierarchy = current_hierarchy[:level-1] + [heading_text]
              
              # Process different token types
              if isinstance(token, (CodeFence, BlockCode)):
                  # Keep code blocks as single chunks
                  chunks.append({
                      'text': token.children[0].content if token.children else '',
                      'metadata': {
                          'doc_path': doc_path,
                          'hierarchy': current_hierarchy.copy(),
                          'position': position,
                          'content_type': 'code',
                          'language': getattr(token, 'language', '')
                      }
                  })
                  position += 1
              
              elif isinstance(token, (Paragraph, List)):
                  # Chunk paragraphs and lists with overlap
                  text = self._get_text_content(token)
                  text_chunks = self._split_text_with_overlap(text)
                  
                  for chunk_text in text_chunks:
                      chunks.append({
                          'text': chunk_text,
                          'metadata': {
                              'doc_path': doc_path,
                              'hierarchy': current_hierarchy.copy(),
                              'position': position,
                              'content_type': 'text'
                          }
                      })
                      position += 1
          
          return chunks
      
      def _split_text_with_overlap(self, text):
          """Split text into chunks with overlap"""
          words = text.split()
          chunks = []
          
          for i in range(0, len(words), self.chunk_size - self.overlap):
              chunk = ' '.join(words[i:i + self.chunk_size])
              if chunk:
                  chunks.append(chunk)
          
          return chunks
      
      def _get_text_content(self, token):
          """Recursively extract text content from AST token"""
          if isinstance(token, RawText):
              return token.content
          elif hasattr(token, 'children'):
              return ' '.join(self._get_text_content(child) for child in token.children)
          return ''
  ```
- **Chunk Metadata**:
  - Document path
  - Section hierarchy (from AST structure)
  - Chunk position
  - Content type (text, code, example)
  - Language (for code blocks)

#### 2.2 Context Enrichment
- **Purpose**: Add contextual information to chunks
- **Features**:
  - Prepend parent section headers
  - Include document title
  - Add navigation breadcrumbs
  - Tag with content type (guide, API, widget, etc.)

### 3. Embedding Generation

#### 3.1 Embedding Model Setup
```python
from sentence_transformers import SentenceTransformer

class TextualEmbedder:
    def __init__(self):
        self.model = SentenceTransformer(
            "nomic-ai/nomic-embed-text-v2-moe",
            trust_remote_code=True
        )
        self.dimension = 256  # Optimal for performance/quality
    
    def embed_documents(self, texts):
        # Apply document prefix for indexing
        prefixed_texts = [f"search_document: {text}" for text in texts]
        return self.model.encode(
            prefixed_texts,
            normalize_embeddings=True,
            show_progress_bar=True
        )
    
    def embed_query(self, query):
        # Apply query prefix for search
        prefixed_query = f"search_query: {query}"
        return self.model.encode(
            prefixed_query,
            normalize_embeddings=True
        )
```

#### 3.2 Batch Processing
- Process documents in batches of 32-64
- GPU acceleration if available
- Progress tracking and checkpointing
- Error handling for malformed content

### 4. Vector Database Setup

#### 4.1 Qdrant Configuration
```yaml
# docker-compose.yml
version: '3.8'
services:
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./qdrant_storage:/qdrant/storage:z
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
```

#### 4.2 Collection Schema
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

client = QdrantClient("localhost", port=6333)

client.create_collection(
    collection_name="textual_docs",
    vectors_config=VectorParams(
        size=256,
        distance=Distance.COSINE
    ),
    on_disk_payload=True  # For large payloads
)
```

#### 4.3 Point Structure
```python
{
    "id": "hash_of_chunk",
    "vector": [...],  # 256-dimensional embedding
    "payload": {
        "text": "chunk content",
        "doc_path": "/docs/guide/widgets.md",
        "section": "Creating Custom Widgets",
        "hierarchy": ["Guide", "Widgets", "Custom Widgets"],
        "content_type": "guide",
        "position": 42,
        "last_updated": "2024-01-15T10:30:00Z"
    }
}
```

### 5. Search Interface

#### 5.1 Query Processor
```python
class SearchEngine:
    def __init__(self, embedder, qdrant_client):
        self.embedder = embedder
        self.client = qdrant_client
        self.collection = "textual_docs"
    
    def search(self, query, limit=10, filters=None):
        # 1. Embed query with proper prefix
        query_vector = self.embedder.embed_query(query)
        
        # 2. Apply filters (content_type, doc_path, etc.)
        search_filters = self._build_filters(filters)
        
        # 3. Perform vector search
        results = self.client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            limit=limit,
            query_filter=search_filters,
            with_payload=True
        )
        
        # 4. Post-process results
        return self._format_results(results)
```

#### 5.2 Result Ranking
- **Primary**: Cosine similarity score
- **Secondary**: Boost recent updates
- **Tertiary**: Prioritize certain content types (guides > API docs)
- **Re-ranking**: Apply MMR (Maximal Marginal Relevance) for diversity

#### 5.3 Context Assembly
- Retrieve surrounding chunks for context
- Merge overlapping content
- Highlight matching sections
- Generate preview snippets

## System Architecture Diagram

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  GitHub API     │────▶│ Doc Fetcher  │────▶│ Parser/Chunker  │
│  (Textual Docs) │     │              │     │                 │
└─────────────────┘     └──────────────┘     └────────┬────────┘
                                                       │
                                                       ▼
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Search Query   │────▶│ Query Embed  │     │ Document Embed  │
│                 │     │              │     │                 │
└─────────────────┘     └──────┬───────┘     └────────┬────────┘
                               │                       │
                               ▼                       ▼
                        ┌──────────────────────────────┐
                        │      Qdrant Vector DB       │
                        │  ┌────────────────────┐     │
                        │  │ textual_docs      │     │
                        │  │ collection        │     │
                        │  └────────────────────┘     │
                        └──────────┬───────────────────┘
                                   │
                                   ▼
                        ┌──────────────────┐
                        │ Search Results   │
                        │ (Ranked/Filtered)│
                        └──────────────────┘
```

## Implementation Considerations

### Performance Optimization
1. **Embedding Cache**: Cache computed embeddings to avoid re-processing
2. **Incremental Updates**: Only process changed documents
3. **Batch Operations**: Process multiple documents simultaneously
4. **Index Optimization**: Use HNSW parameters tuned for documentation size

### Scalability
1. **Horizontal Scaling**: Qdrant supports distributed deployment
2. **Sharding Strategy**: Shard by content type or document path
3. **Load Balancing**: Multiple query endpoints for high availability
4. **Backup Strategy**: Regular snapshots of vector database

### Quality Assurance
1. **Evaluation Metrics**:
   - Mean Reciprocal Rank (MRR)
   - Normalized Discounted Cumulative Gain (NDCG)
   - User feedback integration
2. **Test Suite**: Query-answer pairs for regression testing
3. **A/B Testing**: Compare chunking strategies and parameters

## API Design

### REST Endpoints
```
POST /search
{
    "query": "how to create custom widgets",
    "limit": 10,
    "filters": {
        "content_type": ["guide", "example"],
        "doc_path": "/docs/guide/*"
    }
}

GET /document/{doc_id}
Returns full document with highlighted sections

POST /feedback
{
    "query_id": "uuid",
    "result_id": "uuid",
    "relevant": true,
    "comment": "Found exactly what I needed"
}
```

### Python SDK
```python
from textual_search import TextualSearchClient

client = TextualSearchClient(host="localhost", port=8000)

# Simple search
results = client.search("custom widgets")

# Advanced search
results = client.search(
    query="event handling",
    filters={"content_type": "guide"},
    limit=20
)

# Get document context
doc = client.get_document(results[0].doc_id)
```

## Deployment Strategy

### Phase 1: Local Development
- Docker Compose setup
- In-memory Qdrant for testing
- Sample documentation subset

### Phase 2: Production Deployment
- Kubernetes deployment
- Persistent volume for Qdrant
- Monitoring and alerting
- Regular re-indexing schedule

### Phase 3: Enhancements
- Multi-language support
- Code search capabilities
- Interactive examples integration
- ChatGPT-style Q&A interface

## Next Steps

1. **Prototype Development**:
   - Implement basic ingestion pipeline
   - Test embedding generation
   - Set up Qdrant locally
   - Build simple search interface

2. **Evaluation**:
   - Create test query dataset
   - Measure search quality
   - Optimize parameters
   - Gather user feedback

3. **Production Readiness**:
   - Containerize all components
   - Add monitoring/logging
   - Implement CI/CD pipeline
   - Create deployment documentation

## Technology Stack Summary

- **Language**: Python 3.10+
- **Markdown Parser**: mistletoe (fast, extensible, CommonMark-compliant)
- **Embedding Model**: nomic-embed-text-v2-moe
- **Vector Database**: Qdrant
- **Web Framework**: FastAPI
- **Container**: Docker/Kubernetes
- **Monitoring**: Prometheus/Grafana
- **Documentation Source**: GitHub API

## Mistletoe-Specific Features

### Advanced Markdown Processing
1. **AST Manipulation**: Modify document structure before indexing
   ```python
   from mistletoe import Document
   from mistletoe.block_token import Heading
   
   def enhance_headings(doc):
       """Add document title to all section headings for better context"""
       doc_title = None
       for token in doc.children:
           if isinstance(token, Heading) and token.level == 1:
               doc_title = self._get_text_content(token)
               break
       
       if doc_title:
           for token in doc.children:
               if isinstance(token, Heading) and token.level > 1:
                   # Prepend document title to section headings
                   token.children.insert(0, RawText(f"{doc_title} - "))
   ```

2. **Custom Renderer for Search Snippets**: 
   ```python
   from mistletoe.renderers.base_renderer import BaseRenderer
   
   class SearchSnippetRenderer(BaseRenderer):
       """Custom renderer for generating search-optimized snippets"""
       
       def render_heading(self, token):
           # Include hierarchy in heading rendering
           return f"[H{token.level}] {self.render_inner(token)}"
       
       def render_code_fence(self, token):
           # Add language tag for better search filtering
           lang = token.language or "plaintext"
           return f"[CODE:{lang}] {token.children[0].content}"
       
       def render_paragraph(self, token):
           # Clean paragraph text for indexing
           return self.render_inner(token).strip()
   ```

3. **Link Resolution**: Extract and validate internal documentation links
   ```python
   from mistletoe.span_token import Link
   
   def extract_doc_links(doc):
       """Extract all internal documentation links from AST"""
       links = []
       
       def walk_token(token):
           if isinstance(token, Link):
               if token.target.startswith('/docs/') or token.target.startswith('./'):
                   links.append({
                       'text': self._get_text_content(token),
                       'target': token.target,
                       'title': token.title
                   })
           
           if hasattr(token, 'children'):
               for child in token.children:
                   walk_token(child)
       
       walk_token(doc)
       return links
   ```

This architecture provides a scalable, efficient, and maintainable solution for semantic search over Textual documentation, with mistletoe enabling advanced markdown processing capabilities.