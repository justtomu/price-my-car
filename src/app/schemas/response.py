"""
Response schemas for API endpoints.

Defines Pydantic models for structuring API responses.
"""

from pydantic import BaseModel, Field


class PriceCarResponse(BaseModel):
    """
    Successful response model for /price-car endpoint.

    Attributes:
        make: Extracted car manufacturer
        model: Extracted car model
        price: Estimated market price in dollars
        request_id: Unique request identifier for tracking

    Example:
        {
            "make": "Honda",
            "model": "Accord",
            "price": 12500,
            "request_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    """

    make: str = Field(
        ...,
        description="Car manufacturer (extracted by LLM)",
        examples=["Honda", "Toyota", "BMW"],
    )
    model: str = Field(
        ...,
        description="Car model (extracted by LLM)",
        examples=["Accord", "Camry", "3 Series"],
    )
    price: int = Field(
        ...,
        ge=0,
        description="Estimated market price in dollars",
        examples=[12500, 25000, 45000],
    )
    request_id: str = Field(
        ...,
        description="Unique request identifier for tracking",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )


class ErrorResponse(BaseModel):
    """
    Error response model for failed requests.

    Attributes:
        error: Human-readable error message
        request_id: Unique request identifier for tracking

    Example:
        {
            "error": "Failed to extract car info",
            "request_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    """

    error: str = Field(
        ...,
        description="Human-readable error message",
        examples=["Failed to extract car info", "Car make/model not found"],
    )
    request_id: str = Field(
        ...,
        description="Unique request identifier for tracking",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )


class CacheStats(BaseModel):
    """Cache statistics."""

    hits: int = Field(default=0, description="Number of cache hits")
    misses: int = Field(default=0, description="Number of cache misses")
    hit_rate: float = Field(default=0.0, description="Cache hit rate percentage")


class LLMStats(BaseModel):
    """LLM provider statistics."""

    total_calls: int = Field(default=0, description="Total LLM calls")
    successful_calls: int = Field(default=0, description="Successful LLM calls")
    failures: int = Field(default=0, description="Failed LLM calls")
    retries: int = Field(default=0, description="Total retry attempts")
    ollama_calls: int = Field(default=0, description="Ollama provider calls")
    openai_calls: int = Field(default=0, description="OpenAI provider calls")


class RequestStats(BaseModel):
    """Request statistics."""

    total: int = Field(default=0, description="Total requests received")
    success: int = Field(default=0, description="Successful requests")
    errors: int = Field(default=0, description="Failed requests")
    success_rate: float = Field(default=0.0, description="Success rate percentage")


class CarStats(BaseModel):
    """Car lookup statistics."""

    found: int = Field(default=0, description="Cars successfully found")
    not_found: int = Field(default=0, description="Cars not found in database")
    top_makes: dict[str, int] = Field(
        default_factory=dict,
        description="Top car makes with request counts",
    )


class PerformanceStats(BaseModel):
    """Performance metrics."""

    response_time_p50_ms: float = Field(
        default=0.0, description="50th percentile response time"
    )
    response_time_p95_ms: float = Field(
        default=0.0, description="95th percentile response time"
    )
    response_time_p99_ms: float = Field(
        default=0.0, description="99th percentile response time"
    )
    llm_latency_p50_ms: float = Field(
        default=0.0, description="50th percentile LLM latency"
    )
    llm_latency_p95_ms: float = Field(
        default=0.0, description="95th percentile LLM latency"
    )
    llm_latency_p99_ms: float = Field(
        default=0.0, description="99th percentile LLM latency"
    )


class HealthMetricsResponse(BaseModel):
    """
    Response model for /health/metrics endpoint.

    Provides comprehensive statistics about API usage,
    cache performance, LLM provider metrics, and car analytics.
    """

    status: str = Field(
        default="healthy",
        description="Overall service status",
        examples=["healthy", "degraded", "unhealthy"],
    )
    environment: str = Field(
        ...,
        description="Current environment",
        examples=["development", "production"],
    )
    llm_provider: str = Field(
        ...,
        description="Active LLM provider",
        examples=["ollama", "openai"],
    )
    requests: RequestStats = Field(
        default_factory=RequestStats,
        description="Request statistics",
    )
    cache: CacheStats = Field(
        default_factory=CacheStats,
        description="Cache statistics",
    )
    llm: LLMStats = Field(
        default_factory=LLMStats,
        description="LLM provider statistics",
    )
    cars: CarStats = Field(
        default_factory=CarStats,
        description="Car lookup statistics",
    )
    performance: PerformanceStats = Field(
        default_factory=PerformanceStats,
        description="Performance metrics",
    )
