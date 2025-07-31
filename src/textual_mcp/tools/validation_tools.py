"""MCP tools for CSS validation using Textual's native parser."""

import time
from typing import Dict, Any, Optional
from pathlib import Path

from ..validators.tcss_validator import TCSSValidator
from ..validators.inline_validator import InlineValidator
from ..validators.selector_validator import SelectorValidator
from ..config import TextualMCPConfig
from ..utils.logging_config import log_tool_execution, log_tool_completion, get_logger
from ..utils.errors import ToolExecutionError


def register_validation_tools(mcp: Any, config: TextualMCPConfig) -> None:
    """Register all validation tools with the MCP server."""

    # Initialize validators
    tcss_validator = TCSSValidator(config.validators)
    inline_validator = InlineValidator()
    selector_validator = SelectorValidator()

    logger = get_logger("validation_tools")

    @mcp.tool()
    async def validate_tcss(
        css_content: str,
        filename: Optional[str] = None,
        strict_mode: bool = False,
        check_performance: bool = True,
        check_selectors: bool = True,
    ) -> Dict[str, Any]:
        """
        Validate Textual CSS content using the native parser.

        Args:
            css_content: The CSS content to validate
            filename: Optional filename for error reporting
            strict_mode: Enable strict validation mode
            check_performance: Check for performance issues
            check_selectors: Validate selectors

        Returns:
            Dictionary with validation results
        """
        start_time = time.time()
        tool_name = "validate_tcss"

        try:
            log_tool_execution(
                tool_name,
                {
                    "css_length": len(css_content),
                    "filename": filename,
                    "strict_mode": strict_mode,
                },
            )

            # Override validator config if needed
            if strict_mode != tcss_validator.strict_mode:
                tcss_validator.strict_mode = strict_mode

            # Validate CSS
            result = tcss_validator.validate(css_content, filename)

            # Convert to MCP response format
            response = {
                "valid": result.valid,
                "errors": [
                    {
                        "message": error.message,
                        "line": error.line,
                        "column": error.column,
                        "selector": error.selector,
                        "property": error.property_name,
                    }
                    for error in result.errors
                ],
                "warnings": [
                    {
                        "message": warning.message,
                        "line": warning.line,
                        "column": warning.column,
                        "selector": warning.selector,
                        "property": warning.property_name,
                    }
                    for warning in result.warnings
                ],
                "suggestions": result.suggestions,
                "summary": result.summary,
                "stats": {
                    "parse_time_ms": result.parse_time_ms,
                    "rule_count": result.rule_count,
                    "selector_count": result.selector_count,
                },
            }

            duration = time.time() - start_time
            log_tool_completion(tool_name, True, duration)

            return response

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"CSS validation failed: {str(e)}"
            log_tool_completion(tool_name, False, duration, error_msg)
            raise ToolExecutionError(tool_name, error_msg)

    @mcp.tool()
    async def validate_tcss_file(
        file_path: str, strict_mode: bool = False, check_performance: bool = True
    ) -> Dict[str, Any]:
        """
        Validate a TCSS file.

        Args:
            file_path: Path to the TCSS file
            strict_mode: Enable strict validation mode
            check_performance: Check for performance issues

        Returns:
            Dictionary with validation results
        """
        start_time = time.time()
        tool_name = "validate_tcss_file"

        try:
            log_tool_execution(
                tool_name, {"file_path": file_path, "strict_mode": strict_mode}
            )

            # Check if file exists
            if not Path(file_path).exists():
                # Return error result instead of raising
                return {
                    "valid": False,
                    "errors": [
                        {
                            "message": f"File not found: {file_path}",
                            "line": None,
                            "column": None,
                            "selector": None,
                            "property": None,
                        }
                    ],
                    "warnings": [],
                    "suggestions": [],
                    "summary": f"File not found: {file_path}",
                    "rule_count": 0,
                    "selector_count": 0,
                    "parse_time_ms": 0.0,
                }

            # Override validator config if needed
            if strict_mode != tcss_validator.strict_mode:
                tcss_validator.strict_mode = strict_mode

            # Validate file
            result = tcss_validator.validate_file(file_path)

            # Convert to MCP response format (same as validate_tcss)
            response = {
                "valid": result.valid,
                "errors": [
                    {
                        "message": error.message,
                        "line": error.line,
                        "column": error.column,
                        "selector": error.selector,
                        "property": error.property_name,
                    }
                    for error in result.errors
                ],
                "warnings": [
                    {
                        "message": warning.message,
                        "line": warning.line,
                        "column": warning.column,
                        "selector": warning.selector,
                        "property": warning.property_name,
                    }
                    for warning in result.warnings
                ],
                "suggestions": result.suggestions,
                "summary": result.summary,
                "stats": {
                    "parse_time_ms": result.parse_time_ms,
                    "rule_count": result.rule_count,
                    "selector_count": result.selector_count,
                },
            }

            duration = time.time() - start_time
            log_tool_completion(tool_name, True, duration)

            return response

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"File validation failed: {str(e)}"
            log_tool_completion(tool_name, False, duration, error_msg)
            raise ToolExecutionError(tool_name, error_msg)

    @mcp.tool()
    async def validate_inline_styles(style_string: str) -> Dict[str, Any]:
        """
        Validate inline style declarations.

        Args:
            style_string: CSS declarations string (e.g., "color: red; margin: 10px;")

        Returns:
            Dictionary with validation results
        """
        start_time = time.time()
        tool_name = "validate_inline_styles"

        try:
            log_tool_execution(tool_name, {"style_length": len(style_string)})

            # Validate inline styles
            result = inline_validator.validate(style_string)

            # Convert to MCP response format
            response = {
                "valid": result.valid,
                "errors": [
                    {
                        "message": error.message,
                        "line": error.line,
                        "column": error.column,
                        "property": error.property_name,
                    }
                    for error in result.errors
                ],
                "warnings": [
                    {
                        "message": warning.message,
                        "line": warning.line,
                        "column": warning.column,
                        "property": warning.property_name,
                    }
                    for warning in result.warnings
                ],
            }

            duration = time.time() - start_time
            log_tool_completion(tool_name, True, duration)

            return response

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Inline style validation failed: {str(e)}"
            log_tool_completion(tool_name, False, duration, error_msg)
            raise ToolExecutionError(tool_name, error_msg)

    @mcp.tool()
    async def check_selector(selector: str) -> Dict[str, Any]:
        """
        Validate a single CSS selector.

        Args:
            selector: CSS selector string

        Returns:
            Dictionary with selector validation results
        """
        start_time = time.time()
        tool_name = "check_selector"

        try:
            log_tool_execution(tool_name, {"selector": selector})

            # Validate selector
            result = selector_validator.validate_selector(selector)

            # Convert to MCP response format
            response = {
                "valid": result.valid,
                "selector": selector,
                "error": result.error,
                "type": result.selector_type,
                "specificity": list(
                    result.specificity
                ),  # Convert tuple to list for JSON
            }

            duration = time.time() - start_time
            log_tool_completion(tool_name, True, duration)

            return response

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Selector validation failed: {str(e)}"
            log_tool_completion(tool_name, False, duration, error_msg)
            raise ToolExecutionError(tool_name, error_msg)

    logger.info(
        "Registered validation tools: validate_tcss, validate_tcss_file, validate_inline_styles, check_selector"
    )
