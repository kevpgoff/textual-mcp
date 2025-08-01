# Chonkie Chunking Setup

The Textual MCP now uses Chonkie for advanced document chunking, which provides better semantic coherence and content-aware processing. However, Chonkie requires embedding models for semantic chunking.

## Avoiding Model Download Errors

If you see errors like:
```
"model2vec.hf_utils" - "Folder does not exist locally, attempting to use huggingface hub."
```

This happens when Chonkie's SemanticChunker tries to download embedding models. The system will gracefully fall back to simpler chunking methods, but for optimal performance:

### Option 1: Pre-download Models (Recommended)

Run the initialization script to download and prepare models:

```bash
python scripts/init_embeddings.py
```

This will download the Potion model which provides excellent semantic chunking performance.

### Option 2: Use Cached Models

The system automatically checks for common embedding models in your cache:
- `~/.cache/huggingface/hub/`
- `~/.cache/sentence_transformers/`

If you have `sentence-transformers/all-MiniLM-L6-v2` already cached from other projects, it will be used automatically.

### Option 3: Disable Semantic Chunking

If you prefer not to use embedding models, you can set the chunking strategy to "manual" in your configuration:

```yaml
# config/textual-mcp.yaml
search:
  chunking_strategy: 'manual'  # Use 'manual' instead of 'chonkie'
```

## How It Works

When using Chonkie chunking:

1. **Code Examples**: Uses specialized code chunker that preserves code structure
2. **API Documentation**: Uses semantic chunking with larger chunks to keep class/method documentation together
3. **Guides**: Uses recursive markdown chunking that respects document structure
4. **CSS Reference**: Uses semantic chunking with smaller chunks for individual properties

The system automatically falls back to simpler methods if semantic models aren't available, ensuring the system always works even without pre-downloaded models.
