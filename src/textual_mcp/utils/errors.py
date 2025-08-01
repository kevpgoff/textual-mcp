"""Custom error classes for Textual MCP Server."""

from typing import Optional, Dict, Any, List


class TextualMCPError(Exception):
    """Base exception class for Textual MCP Server."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(TextualMCPError):
    """Exception raised when CSS validation fails."""

    def __init__(
        self,
        message: str,
        line: Optional[int] = None,
        column: Optional[int] = None,
        selector: Optional[str] = None,
        property_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.line = line
        self.column = column
        self.selector = selector
        self.property_name = property_name


class ConfigurationError(TextualMCPError):
    """Exception raised when configuration is invalid."""

    pass


class VectorStoreError(TextualMCPError):
    """Exception raised when vector store operations fail."""

    pass


class ToolExecutionError(TextualMCPError):
    """Exception raised when MCP tool execution fails."""

    def __init__(self, tool_name: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.tool_name = tool_name


class ParsingError(ValidationError):
    """Exception raised when CSS parsing fails."""

    pass


class SelectorError(ValidationError):
    """Exception raised when selector validation fails."""

    pass


def format_validation_errors(errors: List[ValidationError]) -> str:
    """Format a list of validation errors into a readable string."""
    if not errors:
        return "No errors"

    formatted_errors = []
    for error in errors:
        parts = []

        if error.line is not None:
            parts.append(f"Line {error.line}")
            if error.column is not None:
                parts.append(f"Column {error.column}")

        if error.selector:
            parts.append(f"Selector: {error.selector}")

        if error.property_name:
            parts.append(f"Property: {error.property_name}")

        location = ", ".join(parts)
        if location:
            formatted_errors.append(f"{location}: {error.message}")
        else:
            formatted_errors.append(error.message)

    return "\n".join(formatted_errors)
