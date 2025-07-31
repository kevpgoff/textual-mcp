#!/usr/bin/env python3
"""Script to index Textual documentation for vector search."""

import asyncio
import argparse
import sys
from pathlib import Path

# Add parent directory to path to import textual_mcp
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.textual_mcp.config import load_config
from src.textual_mcp.search.memory import TextualDocsMemory
from src.textual_mcp.search.document_processor import (
    TextualDocumentProcessor,
    index_documentation,
)
from src.textual_mcp.utils.logging_config import setup_logging, get_logger


async def main_async(args: argparse.Namespace) -> int:
    """Main async function for indexing documentation."""
    try:
        # Load configuration
        config = load_config(args.config)
        setup_logging(config.logging)
        logger = get_logger("index_documentation_script")

        logger.info("Starting Textual documentation indexing")

        # Override configuration with command line arguments
        if args.embeddings_model:
            config.search.embeddings_model = args.embeddings_model
        if args.persist_path:
            config.search.persist_path = args.persist_path
        if args.chunk_size:
            config.search.chunk_size = args.chunk_size
        if args.chunk_overlap:
            config.search.chunk_overlap = args.chunk_overlap
        if args.github_token:
            config.search.github_token = args.github_token

        # Create memory instance
        persist_path = (
            Path(config.search.persist_path) if config.search.persist_path else None
        )
        if persist_path and not persist_path.parent.exists():
            persist_path.parent.mkdir(parents=True, exist_ok=True)

        memory = TextualDocsMemory(
            embeddings=config.search.embeddings_model, persist_path=persist_path
        )

        # Check if already indexed
        if not args.force and memory.is_indexed():
            logger.info("Documentation is already indexed. Use --force to reindex.")
            return 0

        # Clear existing index if forcing
        if args.force and memory.is_indexed():
            logger.info("Clearing existing index")
            await memory.clear()

        # Create document processor
        processor = TextualDocumentProcessor(
            chunk_size=config.search.chunk_size,
            chunk_overlap=config.search.chunk_overlap,
        )

        if config.search.github_token:
            processor.set_github_token(config.search.github_token)
            logger.info("Using GitHub token for API access")
        else:
            logger.warning("No GitHub token configured. May hit rate limits.")

        # Check rate limit before indexing
        try:
            logger.info("Checking GitHub API rate limit...")
            rate_info = await processor.check_rate_limit()
            print(
                f"\nGitHub API Rate Limit: {rate_info['remaining']}/{rate_info['limit']} requests"
            )

            if rate_info["remaining"] < 300:
                import time

                reset_time = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(rate_info["reset"])
                )
                print("⚠️  WARNING: Insufficient rate limit for indexing")
                print(
                    f"   Need ~300 requests, but only {rate_info['remaining']} remaining"
                )
                print(f"   Rate limit resets at: {reset_time}")

                if not args.force:
                    print("\nAborting. Use --force to proceed anyway.")
                    return 1
                else:
                    print("\nProceeding anyway due to --force flag...")
        except Exception as e:
            logger.warning(f"Could not check rate limit: {e}")

        # Index documentation
        logger.info("Starting indexing process...")
        stats = await index_documentation(memory, processor)

        # Print results
        print("\n" + "=" * 50)
        print("Indexing Complete!")
        print("=" * 50)
        print(f"Documents processed: {stats['documents_processed']}")
        print(f"Chunks created: {stats['chunks_created']}")
        print(f"Duration: {stats['indexing_duration']:.2f} seconds")
        print(f"Embeddings model: {config.search.embeddings_model}")
        if persist_path:
            print(f"Index saved to: {persist_path}")
        print("=" * 50 + "\n")

        return 0

    except Exception as e:
        logger = get_logger("index_documentation_script")
        logger.error(f"Indexing failed: {e}")
        print(f"\nError: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point for the indexing script."""
    parser = argparse.ArgumentParser(
        description="Index Textual documentation for vector search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Index with default settings
  python -m scripts.index_documentation
  
  # Force reindex with custom embeddings model
  python -m scripts.index_documentation --force --embeddings-model "BAAI/bge-small-en-v1.5"
  
  # Use fast embeddings for quick testing
  python -m scripts.index_documentation --embeddings-model "fast" --persist-path "./test_index.db"
  
  # Provide GitHub token for higher API rate limits
  python -m scripts.index_documentation --github-token "ghp_..." --force
""",
    )

    parser.add_argument("--config", "-c", type=str, help="Path to configuration file")

    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force reindexing even if index exists",
    )

    parser.add_argument(
        "--embeddings-model",
        type=str,
        help="Embeddings model to use (e.g., 'fast', 'TaylorAI/bge-micro-v2')",
    )

    parser.add_argument(
        "--persist-path", type=str, help="Path to persist the vector database"
    )

    parser.add_argument(
        "--chunk-size", type=int, help="Size of text chunks for indexing"
    )

    parser.add_argument("--chunk-overlap", type=int, help="Overlap between text chunks")

    parser.add_argument(
        "--github-token", type=str, help="GitHub token for higher API rate limits"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level",
    )

    args = parser.parse_args()

    # Set log level
    import os

    os.environ["LOG_LEVEL"] = args.log_level

    # Run async main
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
