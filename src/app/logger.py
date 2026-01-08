"""
Structured JSON logging configuration.

Provides consistent logging across the application with request tracking,
component identification, and structured JSON output for production monitoring.
"""

import logging
import sys
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from pythonjsonlogger import jsonlogger

from app.settings import get_settings

# Context variable for request ID tracking across async operations
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class CustomJsonFormatter(jsonlogger.JsonFormatter):  # type: ignore[name-defined, misc]
    """
    Custom JSON formatter that adds standard fields to all log entries.

    Adds:
        - timestamp: ISO format timestamp
        - level: Log level name
        - request_id: Current request ID (from context)
        - component: Logger name (component identifier)
    """

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)

        # Standard fields
        log_record["timestamp"] = self.formatTime(record)
        log_record["level"] = record.levelname
        log_record["component"] = record.name

        # Request ID from context (if available)
        req_id = request_id_ctx.get()
        if req_id:
            log_record["request_id"] = req_id

        # Clean up default fields we don't need
        log_record.pop("levelname", None)
        log_record.pop("name", None)


def setup_logging() -> None:
    """
    Configure application-wide logging.

    Sets up:
        - JSON formatter for structured logging
        - Console handler (stdout)
        - File handler (logs/app.log)
        - Configurable log level from settings
    """
    settings = get_settings()

    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Create formatter
    formatter = CustomJsonFormatter(
        fmt="%(timestamp)s %(level)s %(component)s %(message)s"
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(settings.log_level)
    root_logger.addHandler(console_handler)

    # File handler (rotating would be better in production)
    file_handler = logging.FileHandler(logs_dir / "app.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(settings.log_level)
    root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific component.

    Args:
        name: Component name (e.g., 'llm_service', 'cache_service')

    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


def set_request_id(request_id: str) -> None:
    """
    Set the current request ID in context.

    This ID will be automatically included in all log entries
    made within the same async context.

    Args:
        request_id: Unique request identifier
    """
    request_id_ctx.set(request_id)


def get_request_id() -> str | None:
    """
    Get the current request ID from context.

    Returns:
        str | None: Current request ID or None if not set
    """
    return request_id_ctx.get()
