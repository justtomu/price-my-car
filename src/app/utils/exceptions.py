"""
Custom exception classes for the application.

Provides a hierarchy of exceptions for different error scenarios,
enabling precise error handling and appropriate HTTP responses.
"""

from typing import Any


class PriceMyCarError(Exception):
    """
    Base exception for all application errors.

    All custom exceptions should inherit from this class
    to enable catching all application-specific errors.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """
        Initialize base exception.

        Args:
            message: Human-readable error message
            details: Optional dictionary with additional error context
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class LLMProviderError(PriceMyCarError):
    """
    Exception raised when LLM provider is unavailable or returns an error.

    This indicates infrastructure issues with the LLM service
    (Ollama/OpenAI) rather than extraction logic failures.
    """

    pass


class LLMTimeoutError(PriceMyCarError):
    """
    Exception raised when LLM request exceeds timeout limit.

    Default timeout is 5 seconds, configurable via LLM_TIMEOUT setting.
    """

    pass


class LLMExtractionError(PriceMyCarError):
    """
    Exception raised when LLM fails to extract valid car information.

    This occurs when:
        - LLM response cannot be parsed as valid JSON
        - Required fields (make/model) are missing
        - Extraction fails after all retries
    """

    pass


class CarNotFoundError(PriceMyCarError):
    """
    Exception raised when car make/model is not found in pricing database.

    This is a business logic error, not a system error.
    The extraction succeeded but the car doesn't exist in our database.
    """

    pass


class CacheError(PriceMyCarError):
    """
    Exception raised when cache operations fail.

    Cache errors should be handled gracefully - the application
    should continue without caching rather than failing completely.
    """

    pass


class RateLimitError(PriceMyCarError):
    """
    Exception raised when rate limit is exceeded.

    Clients should retry after the rate limit window resets.
    """

    pass
