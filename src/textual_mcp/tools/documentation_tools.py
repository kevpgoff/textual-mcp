"""MCP tools for documentation retrieval and search."""

import time
import os
from typing import Dict, Any, List, Optional, Annotated, Union
from pathlib import Path
import asyncio
import httpx
from pydantic import Field

from ..config import TextualMCPConfig
from ..utils.logging_config import log_tool_execution, log_tool_completion, get_logger
from ..utils.errors import ToolExecutionError
from ..search.memory import TextualDocsMemory
from ..search.document_processor import TextualDocumentProcessor, index_documentation
from ..utils.style_introspector import StyleIntrospector


# Global memory instance
_docs_memory: Optional[TextualDocsMemory] = None


def get_docs_memory(config: TextualMCPConfig) -> TextualDocsMemory:
    """Get or create the documentation memory instance."""
    global _docs_memory
    if _docs_memory is None:
        # Check for EMBEDDINGS_STORE environment variable first
        embeddings_store = os.environ.get("EMBEDDINGS_STORE")
        persist_path: Optional[Path]
        if embeddings_store:
            persist_path = Path(embeddings_store)
        else:
            persist_path = Path(config.search.persist_path) if config.search.persist_path else None

        if persist_path and not persist_path.parent.exists():
            persist_path.parent.mkdir(parents=True, exist_ok=True)

        _docs_memory = TextualDocsMemory(
            embeddings=config.search.embeddings_model, persist_path=persist_path
        )

        # Check if we need to initialize the index
        if config.search.auto_index and not _docs_memory.is_indexed():
            logger = get_logger("documentation_tools")
            logger.info("Auto-indexing documentation on first use")
            asyncio.create_task(initialize_docs_index(_docs_memory, config))

    return _docs_memory


async def initialize_docs_index(memory: TextualDocsMemory, config: TextualMCPConfig) -> None:
    """Initialize the documentation index by fetching and indexing Textual documentation."""
    try:
        logger = get_logger("documentation_index")
        logger.info("Starting documentation indexing process")

        # Create processor with config
        processor = TextualDocumentProcessor(
            chunk_size=config.search.chunk_size,
            chunk_overlap=config.search.chunk_overlap,
        )

        if config.search.github_token:
            processor.set_github_token(config.search.github_token)

        # Index documentation
        stats = await index_documentation(memory, processor)

        logger.info(f"Documentation indexing completed. Stats: {stats}")

    except Exception as e:
        logger = get_logger("documentation_index")
        logger.error(f"Failed to initialize documentation index: {e}")
        raise


def _generate_preview(text: str, query: str, max_length: int = 150) -> str:
    """Generate a preview of the text content, highlighting query terms."""
    if not text:
        return ""

    # Normalize whitespace
    text = " ".join(text.split())

    # If text is shorter than max_length, return it as is
    if len(text) <= max_length:
        return text

    # Try to find the query terms in the text
    query_terms = query.lower().split()
    found_indices = []

    for term in query_terms:
        # Find all occurrences of the term
        start = 0
        while True:
            index = text.lower().find(term, start)
            if index == -1:
                break
            found_indices.append((index, index + len(term)))
            start = index + 1

    # If we found query terms, center the preview around them
    if found_indices:
        # Find the middle of all found terms
        first_index = min(idx[0] for idx in found_indices)
        last_index = max(idx[1] for idx in found_indices)
        center = (first_index + last_index) // 2

        # Calculate start and end positions for the preview
        start_pos = max(0, center - max_length // 2)
        end_pos = min(len(text), start_pos + max_length)

        # Adjust start position if we're at the end
        if end_pos - start_pos < max_length:
            start_pos = max(0, end_pos - max_length)

        preview = text[start_pos:end_pos]

        # Add ellipsis if needed
        if start_pos > 0:
            preview = "..." + preview
        if end_pos < len(text):
            preview = preview + "..."

        return preview

    # If no query terms found, return a snippet from the beginning
    preview = text[:max_length].rstrip()
    if len(text) > max_length:
        preview += "..."
    return preview


def register_documentation_tools(mcp: Any, config: TextualMCPConfig) -> None:
    """Register all documentation tools with the MCP server."""

    logger = get_logger("documentation_tools")

    @mcp.tool()
    async def search_textual_docs(
        query: Annotated[
            str,
            Field(
                description="Search query for Textual documentation. Can include widget names, CSS properties, concepts, or code patterns.",
                min_length=1,
                max_length=200,
            ),
        ],
        limit: Annotated[
            int,
            Field(description="Maximum number of search results to return.", ge=1, le=50),
        ] = 10,
        content_type: Annotated[
            Optional[List[str]],
            Field(
                description="Filter by content types: 'guide' (guides and tutorials), 'api' (API reference), 'example' (code examples), 'widget' (widget documentation).",
                min_length=1,
                max_length=4,
            ),
        ] = None,
        doc_path_pattern: Annotated[
            Optional[str],
            Field(
                description="Filter by document path pattern using wildcards (e.g., '/docs/guide/*' for guide pages, '/docs/widgets/*' for widget docs).",
                pattern=r"^[/\w\-*]+$",
            ),
        ] = None,
    ) -> Dict[str, Any]:
        """
        Search Textual documentation using semantic search powered by VectorDB.

        This tool searches through indexed Textual documentation including guides,
        API references, widget documentation, and code examples.

        Args:
            query: Search query for Textual documentation
            limit: Maximum number of results to return (default: 10)
            content_type: Filter by content types (e.g., ['guide', 'api', 'example', 'widget'])
            doc_path_pattern: Filter by document path pattern (e.g., '/docs/guide/*')

        Returns:
            Dictionary with search results including text, scores, and metadata
        """
        start_time = time.time()
        tool_name = "search_textual_docs"

        try:
            log_tool_execution(
                tool_name,
                {"query": query, "limit": limit, "content_type": content_type},
            )

            memory = get_docs_memory(config)

            # Build filters
            filters: Dict[str, Any] = {}
            if content_type:
                filters["content_type"] = content_type
            if doc_path_pattern:
                filters["doc_path_pattern"] = doc_path_pattern

            # Perform search
            results = await memory.search(query, limit=limit, filters=filters)

            # Format results for return
            formatted_results = []
            for result in results:
                formatted_results.append(
                    {
                        "text": result["text"],
                        "score": result.get("distance", 0.0),
                        "metadata": result.get("metadata", {}),
                        "preview": _generate_preview(result["text"], query),
                    }
                )

            response = {
                "query": query,
                "results": formatted_results,
                "total": len(formatted_results),
            }

            duration = time.time() - start_time
            log_tool_completion(tool_name, True, duration)

            return response

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Documentation search failed: {str(e)}"
            log_tool_completion(tool_name, False, duration, error_msg)
            raise ToolExecutionError(tool_name, error_msg)

    @mcp.tool()
    async def index_textual_docs(
        force_reindex: Annotated[
            bool,
            Field(
                description="Force reindexing even if documentation is already indexed. Use True to update with latest documentation changes."
            ),
        ] = False,
    ) -> Dict[str, Any]:
        """
        Index or reindex Textual documentation from GitHub.

        This tool fetches the latest Textual documentation from GitHub and
        indexes it for semantic search. Use force_reindex=True to update
        the index with the latest documentation.

        Args:
            force_reindex: Force reindexing even if index exists (default: False)

        Returns:
            Dictionary with indexing statistics
        """
        start_time = time.time()
        tool_name = "index_textual_docs"

        try:
            log_tool_execution(tool_name, {"force_reindex": force_reindex})

            memory = get_docs_memory(config)

            if not force_reindex and memory.is_indexed():
                response: Dict[str, Union[str, Dict[str, Union[str, int, float]]]] = {
                    "status": "already_indexed",
                    "message": "Documentation is already indexed. Use force_reindex=True to update.",
                }
            else:
                if force_reindex:
                    # Clear existing index
                    await memory.clear()

                # Create processor
                processor = TextualDocumentProcessor(
                    chunk_size=config.search.chunk_size,
                    chunk_overlap=config.search.chunk_overlap,
                )

                if config.search.github_token:
                    processor.set_github_token(config.search.github_token)

                # Check rate limit before indexing
                try:
                    rate_info = await processor.check_rate_limit()
                    logger = get_logger("index_textual_docs")
                    logger.info(
                        f"GitHub API rate limit: {rate_info['remaining']}/{rate_info['limit']}"
                    )

                    # Warn if rate limit is low
                    if rate_info["remaining"] < 300:  # Need ~300 requests for full indexing
                        reset_time = time.strftime(
                            "%Y-%m-%d %H:%M:%S", time.localtime(rate_info["reset"])
                        )
                        raise ValueError(
                            f"Insufficient GitHub API rate limit for indexing.\n"
                            f"Current limit: {rate_info['remaining']}/{rate_info['limit']} requests\n"
                            f"Need approximately 300 requests to index all documentation.\n"
                            f"Rate limit resets at: {reset_time}\n"
                            f"Please wait until the rate limit resets or use a different token."
                        )
                except httpx.HTTPStatusError as e:
                    logger.warning(f"Could not check rate limit: {e}")

                # Index documentation
                stats = await index_documentation(memory, processor)

                response = {
                    "status": "success",
                    "stats": stats,
                }

            duration = time.time() - start_time
            log_tool_completion(tool_name, True, duration)

            return response

        except ValueError as e:
            # Re-raise ValueError with original message (contains helpful instructions)
            duration = time.time() - start_time
            log_tool_completion(tool_name, False, duration, str(e))
            raise ToolExecutionError(tool_name, str(e))
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Documentation indexing failed: {str(e)}"
            log_tool_completion(tool_name, False, duration, error_msg)
            raise ToolExecutionError(tool_name, error_msg)

    @mcp.tool()
    async def search_textual_code_examples(
        query: Annotated[
            str,
            Field(
                description="Search query for code examples. Include specific patterns, methods, or functionality you're looking for.",
                min_length=1,
                max_length=200,
            ),
        ],
        widget_type: Annotated[
            Optional[str],
            Field(
                description="Filter by specific Textual widget type (e.g., 'Button', 'DataTable', 'Tree'). Case-insensitive.",
                pattern=r"^[A-Za-z][A-Za-z0-9]*$",
            ),
        ] = None,
        limit: Annotated[
            int,
            Field(description="Maximum number of code examples to return.", ge=1, le=20),
        ] = 10,
    ) -> Dict[str, Any]:
        """
        Search specifically for code examples in Textual documentation.

        This tool is optimized for finding code snippets and examples,
        particularly useful when looking for specific widget implementations
        or usage patterns.

        Args:
            query: Search query for code examples
            widget_type: Filter by Textual widget type (e.g., 'Button', 'DataTable')
            limit: Maximum number of examples to return (default: 10)

        Returns:
            Dictionary with code examples and metadata
        """
        start_time = time.time()
        tool_name = "search_textual_code_examples"

        try:
            log_tool_execution(
                tool_name, {"query": query, "widget_type": widget_type, "limit": limit}
            )

            memory = get_docs_memory(config)

            # Enhance query for code search
            enhanced_query = f"code example {query}"
            if widget_type:
                enhanced_query += f" {widget_type} widget"

            # Search with code-specific filters
            results = await memory.search(
                enhanced_query,
                limit=limit * 2,  # Get more results to filter
                filters={"content_type": "code"},
            )

            # Further filter by widget type if specified
            if widget_type:
                filtered_results = [r for r in results if widget_type.lower() in r["text"].lower()]
                results = filtered_results

            # Format code examples
            formatted_examples = []
            for result in results[:limit]:
                metadata = result.get("metadata", {})
                formatted_examples.append(
                    {
                        "code": result["text"],
                        "language": metadata.get("language", "python"),
                        "context": " > ".join(metadata.get("hierarchy", [])),
                        "source": metadata.get("doc_path", ""),
                        "score": result.get("distance", 0.0),
                    }
                )

            response = {
                "query": query,
                "widget_type": widget_type,
                "examples": formatted_examples,
                "total": len(formatted_examples),
            }

            duration = time.time() - start_time
            log_tool_completion(tool_name, True, duration)

            return response

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Code example search failed: {str(e)}"
            log_tool_completion(tool_name, False, duration, error_msg)
            raise ToolExecutionError(tool_name, error_msg)

    @mcp.tool()
    async def get_css_property_info(
        property_name: Annotated[
            str,
            Field(
                description="CSS property name to get information about (e.g., 'background', 'margin', 'display'). Use hyphens or underscores.",
                pattern=r"^[a-z][a-z0-9_-]*$",
                min_length=1,
                max_length=50,
            ),
        ],
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific Textual CSS property.

        This tool introspects Textual's actual CSS implementation to provide
        accurate, up-to-date information about CSS properties including their
        valid values, types, defaults, and usage.

        Args:
            property_name: Name of the CSS property (e.g., 'background', 'margin-top')

        Returns:
            Dictionary with comprehensive property information
        """
        start_time = time.time()
        tool_name = "get_css_property_info"

        try:
            log_tool_execution(tool_name, {"property_name": property_name})

            # Initialize introspector
            introspector = StyleIntrospector()

            # Get property info
            prop_info = introspector.get_property_info(property_name)

            response: Dict[str, Any]
            if not prop_info:
                # Try to find similar properties
                all_props = introspector.get_all_properties()
                similar = [p for p in all_props.keys() if property_name in p or p in property_name]

                response = {
                    "error": f"Property '{property_name}' not found",
                    "suggestion": "Use list_css_properties to see all available properties",
                    "similar_properties": similar[:5] if similar else [],
                }
            else:
                response = {
                    "name": prop_info.name,
                    "description": prop_info.description,
                    "type": prop_info.property_type,
                    "valid_values": prop_info.valid_values,
                    "default_value": str(prop_info.default_value)
                    if prop_info.default_value is not None
                    else None,
                    "category": prop_info.category,
                    "examples": prop_info.examples,
                    "related_properties": prop_info.related_properties,
                }

            duration = time.time() - start_time
            log_tool_completion(tool_name, True, duration)

            return response

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Failed to get CSS property info: {str(e)}"
            log_tool_completion(tool_name, False, duration, error_msg)
            raise ToolExecutionError(tool_name, error_msg)

    @mcp.tool()
    async def list_css_properties(
        category: Annotated[
            Optional[str],
            Field(
                description="Filter by category: 'layout', 'sizing', 'appearance', 'borders', 'text', 'overflow', 'grid', 'animation', or 'general'",
                pattern=r"^(layout|sizing|appearance|borders|text|overflow|grid|animation|general)$",
            ),
        ] = None,
        include_descriptions: Annotated[
            bool,
            Field(
                description="Include brief descriptions for each property. Set to False for a more compact list."
            ),
        ] = True,
    ) -> Dict[str, Any]:
        """
        List all available Textual CSS properties, optionally filtered by category.

        This tool provides a comprehensive list of all CSS properties supported
        by Textual, organized by category for easy browsing.

        Args:
            category: Optional category filter
            include_descriptions: Whether to include property descriptions

        Returns:
            Dictionary with categorized CSS properties
        """
        start_time = time.time()
        tool_name = "list_css_properties"

        try:
            log_tool_execution(
                tool_name, {"category": category, "include_descriptions": include_descriptions}
            )

            # Initialize introspector
            introspector = StyleIntrospector()

            # Get properties by category
            categorized = introspector.get_properties_by_category()

            # Build response
            response: Dict[str, Any]
            if category:
                # Filter to specific category
                if category in categorized:
                    properties = categorized[category]
                    prop_list: Union[List[str], List[Dict[str, str]]]
                    if include_descriptions:
                        prop_list = [
                            {
                                "name": prop.name,
                                "description": prop.description[:100] + "..."
                                if len(prop.description) > 100
                                else prop.description,
                                "type": prop.property_type,
                            }
                            for prop in properties
                        ]
                    else:
                        prop_list = [prop.name for prop in properties]

                    response = {
                        "category": category,
                        "properties": prop_list,
                        "total": len(properties),
                    }
                else:
                    response = {
                        "error": f"Category '{category}' not found",
                        "available_categories": list(categorized.keys()),
                    }
            else:
                # Return all categories
                result: Dict[str, Union[List[str], List[Dict[str, str]]]] = {}
                total_count = 0

                for cat, props in categorized.items():
                    if include_descriptions:
                        result[cat] = [
                            {
                                "name": prop.name,
                                "description": prop.description[:80] + "..."
                                if len(prop.description) > 80
                                else prop.description,
                            }
                            for prop in props
                        ]
                    else:
                        result[cat] = [prop.name for prop in props]
                    total_count += len(props)

                response = {
                    "categories": result,
                    "total_properties": total_count,
                    "category_counts": {cat: len(props) for cat, props in categorized.items()},
                }

            duration = time.time() - start_time
            log_tool_completion(tool_name, True, duration)

            return response

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Failed to list CSS properties: {str(e)}"
            log_tool_completion(tool_name, False, duration, error_msg)
            raise ToolExecutionError(tool_name, error_msg)

    logger.info(
        "Registered documentation tools: search_textual_docs, index_textual_docs, search_textual_code_examples, get_css_property_info, list_css_properties"
    )
