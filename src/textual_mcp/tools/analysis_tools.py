"""MCP tools for CSS analysis and code inspection."""

import time
from typing import Dict, Any, Annotated
from pydantic import Field

from ..config import TextualMCPConfig
from ..utils.logging_config import log_tool_execution, log_tool_completion, get_logger
from ..utils.errors import ToolExecutionError
from ..validators.conflict_detector import ConflictDetector


def register_analysis_tools(mcp: Any, config: TextualMCPConfig) -> None:
    """Register all analysis tools with the MCP server."""

    logger = get_logger("analysis_tools")

    @mcp.tool()
    async def detect_style_conflicts(
        css_content: Annotated[
            str,
            Field(
                description="The Textual CSS content to analyze for potential conflicts, overlapping selectors, and specificity issues that may cause unexpected styling behavior.",
                min_length=1,
            ),
        ],
    ) -> Dict[str, Any]:
        """
        Detect potential style conflicts in CSS.

        Args:
            css_content: The CSS content to analyze

        Returns:
            Dictionary with conflict detection results
        """
        start_time = time.time()
        tool_name = "detect_style_conflicts"

        try:
            log_tool_execution(tool_name, {"css_length": len(css_content)})

            # Use ConflictDetector to analyze the CSS
            detector = ConflictDetector()
            analysis_result = detector.analyze_conflicts(css_content)

            # Convert conflicts to serializable format
            conflicts = []
            for conflict in analysis_result.conflicts:
                conflicts.append(
                    {
                        "selector1": conflict.selector1,
                        "selector2": conflict.selector2,
                        "conflicting_properties": conflict.conflicting_properties,
                        "specificity1": conflict.specificity1,
                        "specificity2": conflict.specificity2,
                        "line1": conflict.line1,
                        "line2": conflict.line2,
                        "resolution": conflict.resolution_suggestion,
                    }
                )

            # Convert overlapping selectors to serializable format
            overlapping_selectors = []
            for overlap in analysis_result.overlapping_selectors:
                overlapping_selectors.append(
                    {
                        "selectors": overlap.selectors,
                        "overlap_type": overlap.overlap_type,
                        "specificity_scores": overlap.specificity_scores,
                    }
                )

            # Build response
            response: Dict[str, Any] = {
                "conflicts": conflicts,
                "overlapping_selectors": overlapping_selectors,
                "resolution_suggestions": analysis_result.resolution_suggestions,
                "property_conflicts": analysis_result.property_conflicts,
                "specificity_issues": analysis_result.specificity_issues,
                "summary": {
                    "total_conflicts": len(conflicts),
                    "total_overlaps": len(overlapping_selectors),
                    "has_issues": len(conflicts) > 0 or len(overlapping_selectors) > 0,
                },
            }

            duration = time.time() - start_time
            log_tool_completion(tool_name, True, duration)

            return response

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Style conflict detection failed: {str(e)}"
            log_tool_completion(tool_name, False, duration, error_msg)
            raise ToolExecutionError(tool_name, error_msg)

    logger.info(
        "Registered analysis tools: analyze_selectors, extract_css_variables, detect_style_conflicts"
    )
