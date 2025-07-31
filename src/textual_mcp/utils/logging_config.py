"""Logging configuration for Textual MCP Server."""

import logging
import logging.handlers
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, UTC

from ..config import LoggingConfig


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.now(UTC),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "exc_info",
                "exc_text",
                "stack_info",
            }:
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter."""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def setup_logging(config: LoggingConfig) -> None:
    """Set up logging configuration."""
    # Get root logger
    root_logger = logging.getLogger()

    # Clear existing handlers
    root_logger.handlers.clear()

    # Set log level
    log_level = getattr(logging, config.level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    # Create console handler - use stderr for MCP servers to avoid interfering with protocol
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)

    # Create file handler if specified
    file_handler = None
    if config.file:
        log_file = Path(config.file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setLevel(log_level)

    # Set formatters based on format type
    formatter: logging.Formatter
    if config.format.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()

    console_handler.setFormatter(formatter)
    if file_handler:
        file_handler.setFormatter(formatter)

    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    if file_handler:
        root_logger.addHandler(file_handler)

    # Set up specific loggers
    _setup_library_loggers()


def _setup_library_loggers() -> None:
    """Configure logging for third-party libraries."""
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("torch").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(f"textual_mcp.{name}")


class LoggerMixin:
    """Mixin class to add logging capabilities to other classes."""

    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(self.__class__.__name__)


def log_tool_execution(tool_name: str, parameters: Dict[str, Any]) -> None:
    """Log tool execution with parameters."""
    logger = get_logger("tools")
    logger.info(
        "Tool execution started",
        extra={"tool_name": tool_name, "parameters": parameters, "event": "tool_start"},
    )


def log_tool_completion(
    tool_name: str, success: bool, duration: float, error: Optional[str] = None
) -> None:
    """Log tool completion with results."""
    logger = get_logger("tools")

    extra = {
        "tool_name": tool_name,
        "success": success,
        "duration_ms": round(duration * 1000, 2),
        "event": "tool_complete",
    }

    if error:
        extra["error"] = error

    if success:
        logger.info("Tool execution completed", extra=extra)
    else:
        logger.error("Tool execution failed", extra=extra)


def log_validation_result(
    css_content_length: int, errors_count: int, warnings_count: int, duration: float
) -> None:
    """Log CSS validation results."""
    logger = get_logger("validation")
    logger.info(
        "CSS validation completed",
        extra={
            "css_length": css_content_length,
            "errors": errors_count,
            "warnings": warnings_count,
            "duration_ms": round(duration * 1000, 2),
            "event": "validation_complete",
        },
    )
