"""
Metrics service for statistics tracking.

Provides Redis-based metrics collection with atomic operations
and graceful degradation.
"""

import time
from typing import Any

from app.logger import get_logger
from app.schemas.response import (
    CacheStats,
    CarStats,
    HealthMetricsResponse,
    LLMStats,
    PerformanceStats,
    RequestStats,
)
from app.services.cache_service import CacheService
from app.settings import Settings

logger = get_logger("metrics_service")


class MetricsService:
    """
    Service for tracking and aggregating application metrics.

    Uses Redis for persistent storage of counters and percentile data.
    Implements graceful degradation - metrics failures don't
    affect main application flow.

    Attributes:
        settings: Application settings
        cache: CacheService instance for Redis access
    """

    # Redis key prefixes
    REQUESTS_TOTAL = "stats:requests:total"
    REQUESTS_SUCCESS = "stats:requests:success"
    REQUESTS_ERRORS = "stats:requests:errors"
    CACHE_HITS = "stats:cache:hits"
    CACHE_MISSES = "stats:cache:misses"
    LLM_CALLS_TOTAL = "stats:llm:calls:total"
    LLM_CALLS_SUCCESS = "stats:llm:calls:success"
    LLM_FAILURES = "stats:llm:failures"
    LLM_RETRIES = "stats:llm:retries"
    LLM_PROVIDER_OLLAMA = "stats:llm:provider:ollama:calls"
    LLM_PROVIDER_OPENAI = "stats:llm:provider:openai:calls"
    CAR_FOUND = "stats:car:found"
    CAR_NOT_FOUND = "stats:car:not_found"
    CAR_MAKE_PREFIX = "stats:car:make:"
    RESPONSE_TIMES = "stats:response_times"
    LLM_LATENCIES = "stats:llm_latencies"

    def __init__(self, settings: Settings, cache: CacheService) -> None:
        """
        Initialize metrics service.

        Args:
            settings: Application settings
            cache: CacheService instance for Redis access
        """
        self._settings = settings
        self._cache = cache
        self._retention_seconds = settings.stats_retention_days * 24 * 60 * 60

    async def _incr(self, key: str) -> None:
        """Increment a counter (graceful on failure)."""
        try:
            await self._cache.incr(key)
        except Exception as e:
            logger.debug("metrics_incr_failed", extra={"key": key, "error": str(e)})

    async def _get_count(self, key: str) -> int:
        """Get counter value."""
        try:
            value = await self._cache.get_raw(key)
            return int(value) if value else 0
        except Exception:
            return 0

    async def record_request(self) -> None:
        """Record incoming request."""
        await self._incr(self.REQUESTS_TOTAL)

    async def record_success(self) -> None:
        """Record successful request."""
        await self._incr(self.REQUESTS_SUCCESS)

    async def record_error(self) -> None:
        """Record failed request."""
        await self._incr(self.REQUESTS_ERRORS)

    async def record_cache_hit(self) -> None:
        """Record cache hit."""
        await self._incr(self.CACHE_HITS)

    async def record_cache_miss(self) -> None:
        """Record cache miss."""
        await self._incr(self.CACHE_MISSES)

    async def record_llm_call(self, provider: str) -> None:
        """
        Record LLM call.

        Args:
            provider: Provider name ('ollama' or 'openai')
        """
        await self._incr(self.LLM_CALLS_TOTAL)
        if provider == "ollama":
            await self._incr(self.LLM_PROVIDER_OLLAMA)
        elif provider == "openai":
            await self._incr(self.LLM_PROVIDER_OPENAI)

    async def record_llm_success(self) -> None:
        """Record successful LLM extraction."""
        await self._incr(self.LLM_CALLS_SUCCESS)

    async def record_llm_failure(self) -> None:
        """Record failed LLM extraction."""
        await self._incr(self.LLM_FAILURES)

    async def record_llm_retry(self) -> None:
        """Record LLM retry attempt."""
        await self._incr(self.LLM_RETRIES)

    async def record_car_found(self, make: str) -> None:
        """
        Record successful car lookup.

        Args:
            make: Car make that was found
        """
        await self._incr(self.CAR_FOUND)
        # Track per-make stats with TTL
        make_key = f"{self.CAR_MAKE_PREFIX}{make.lower()}"
        await self._incr(make_key)

    async def record_car_not_found(self) -> None:
        """Record car not found."""
        await self._incr(self.CAR_NOT_FOUND)

    async def record_response_time(self, duration_ms: float) -> None:
        """
        Record response time for percentile calculation.

        Args:
            duration_ms: Response time in milliseconds
        """
        member = f"{time.time()}:{duration_ms}"
        await self._cache.zadd(
            self.RESPONSE_TIMES,
            duration_ms,
            member,
            ttl=self._retention_seconds,
        )

    async def record_llm_latency(self, duration_ms: float) -> None:
        """
        Record LLM latency for percentile calculation.

        Args:
            duration_ms: LLM call duration in milliseconds
        """
        member = f"{time.time()}:{duration_ms}"
        await self._cache.zadd(
            self.LLM_LATENCIES,
            duration_ms,
            member,
            ttl=self._retention_seconds,
        )

    async def _calculate_percentiles(
        self, key: str
    ) -> tuple[float, float, float]:
        """
        Calculate p50, p95, p99 percentiles from sorted set.

        Args:
            key: Sorted set key

        Returns:
            Tuple of (p50, p95, p99) values
        """
        try:
            data = await self._cache.zrange_with_scores(key)
            if not data:
                return 0.0, 0.0, 0.0

            # Extract scores (latencies) and sort
            values = sorted([score for _, score in data])
            n = len(values)

            if n == 0:
                return 0.0, 0.0, 0.0

            p50_idx = int(n * 0.50) - 1
            p95_idx = int(n * 0.95) - 1
            p99_idx = int(n * 0.99) - 1

            p50 = values[max(0, p50_idx)]
            p95 = values[max(0, p95_idx)]
            p99 = values[max(0, p99_idx)]

            return round(p50, 2), round(p95, 2), round(p99, 2)
        except Exception:
            return 0.0, 0.0, 0.0

    async def _get_top_makes(self, limit: int = 10) -> dict[str, int]:
        """
        Get top car makes by request count.

        Uses SCAN instead of KEYS and MGET for batch fetching
        to avoid blocking Redis in production.

        Args:
            limit: Maximum number of makes to return

        Returns:
            Dictionary of make -> count
        """
        try:
            # Use scan_keys instead of keys to avoid blocking Redis
            keys = await self._cache.scan_keys(f"{self.CAR_MAKE_PREFIX}*")
            if not keys:
                return {}

            # Use MGET for batch fetching instead of individual gets
            values = await self._cache.mget(keys)

            makes: dict[str, int] = {}
            for key, value in zip(keys, values):
                make = key.replace(self.CAR_MAKE_PREFIX, "")
                count = int(value) if value else 0
                makes[make.title()] = count

            # Sort by count and take top N
            sorted_makes = dict(
                sorted(makes.items(), key=lambda x: x[1], reverse=True)[:limit]
            )
            return sorted_makes
        except Exception:
            return {}

    async def get_metrics(self) -> HealthMetricsResponse:
        """
        Get comprehensive metrics for the health endpoint.

        Returns:
            HealthMetricsResponse with all statistics
        """
        # Request stats
        total_requests = await self._get_count(self.REQUESTS_TOTAL)
        success_requests = await self._get_count(self.REQUESTS_SUCCESS)
        error_requests = await self._get_count(self.REQUESTS_ERRORS)
        success_rate = (
            round(success_requests / total_requests * 100, 2)
            if total_requests > 0
            else 0.0
        )

        # Cache stats
        cache_hits = await self._get_count(self.CACHE_HITS)
        cache_misses = await self._get_count(self.CACHE_MISSES)
        total_cache = cache_hits + cache_misses
        hit_rate = (
            round(cache_hits / total_cache * 100, 2) if total_cache > 0 else 0.0
        )

        # LLM stats
        llm_total = await self._get_count(self.LLM_CALLS_TOTAL)
        llm_success = await self._get_count(self.LLM_CALLS_SUCCESS)
        llm_failures = await self._get_count(self.LLM_FAILURES)
        llm_retries = await self._get_count(self.LLM_RETRIES)
        ollama_calls = await self._get_count(self.LLM_PROVIDER_OLLAMA)
        openai_calls = await self._get_count(self.LLM_PROVIDER_OPENAI)

        # Car stats
        car_found = await self._get_count(self.CAR_FOUND)
        car_not_found = await self._get_count(self.CAR_NOT_FOUND)
        top_makes = await self._get_top_makes()

        # Performance percentiles
        resp_p50, resp_p95, resp_p99 = await self._calculate_percentiles(
            self.RESPONSE_TIMES
        )
        llm_p50, llm_p95, llm_p99 = await self._calculate_percentiles(
            self.LLM_LATENCIES
        )

        return HealthMetricsResponse(
            status="healthy" if await self._cache.health_check() else "degraded",
            environment=self._settings.environment,
            llm_provider=self._settings.llm_provider,
            requests=RequestStats(
                total=total_requests,
                success=success_requests,
                errors=error_requests,
                success_rate=success_rate,
            ),
            cache=CacheStats(
                hits=cache_hits,
                misses=cache_misses,
                hit_rate=hit_rate,
            ),
            llm=LLMStats(
                total_calls=llm_total,
                successful_calls=llm_success,
                failures=llm_failures,
                retries=llm_retries,
                ollama_calls=ollama_calls,
                openai_calls=openai_calls,
            ),
            cars=CarStats(
                found=car_found,
                not_found=car_not_found,
                top_makes=top_makes,
            ),
            performance=PerformanceStats(
                response_time_p50_ms=resp_p50,
                response_time_p95_ms=resp_p95,
                response_time_p99_ms=resp_p99,
                llm_latency_p50_ms=llm_p50,
                llm_latency_p95_ms=llm_p95,
                llm_latency_p99_ms=llm_p99,
            ),
        )
