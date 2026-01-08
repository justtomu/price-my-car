"""
Metrics service for statistics tracking.

Provides Redis-based metrics collection with atomic operations
and graceful degradation.
"""

import random
import time

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

# Cleanup configuration
CLEANUP_PROBABILITY = 0.01  # 1% chance to cleanup on each record operation
MAX_METRICS_ENTRIES = 10000  # Maximum entries to keep in sorted sets


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

        Probabilistically triggers cleanup of old entries.

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
        # Probabilistic cleanup to avoid checking on every request
        await self._maybe_cleanup_sorted_set(self.RESPONSE_TIMES)

    async def record_llm_latency(self, duration_ms: float) -> None:
        """
        Record LLM latency for percentile calculation.

        Probabilistically triggers cleanup of old entries.

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
        # Probabilistic cleanup to avoid checking on every request
        await self._maybe_cleanup_sorted_set(self.LLM_LATENCIES)

    async def _maybe_cleanup_sorted_set(self, key: str) -> None:
        """
        Probabilistically clean up old entries from sorted set.

        Removes oldest entries when set exceeds MAX_METRICS_ENTRIES.
        Only runs with CLEANUP_PROBABILITY chance to avoid overhead.

        Args:
            key: Sorted set key to clean up
        """
        # Only run cleanup with configured probability
        if random.random() > CLEANUP_PROBABILITY:
            return

        try:
            count = await self._cache.zcard(key)
            if count > MAX_METRICS_ENTRIES:
                # Remove oldest entries (lowest ranks = oldest timestamps in member)
                # Keep the most recent MAX_METRICS_ENTRIES entries
                to_remove = count - MAX_METRICS_ENTRIES
                removed = await self._cache.zremrangebyrank(key, 0, to_remove - 1)
                if removed > 0:
                    logger.debug(
                        "metrics_cleanup",
                        extra={
                            "key": key,
                            "removed": removed,
                            "remaining": count - removed,
                        },
                    )
        except Exception as e:
            logger.debug(
                "metrics_cleanup_failed",
                extra={"key": key, "error": str(e)},
            )

    async def cleanup_old_metrics(self) -> dict[str, int]:
        """
        Force cleanup of old metrics entries.

        Can be called manually or from a scheduled task.
        Removes entries exceeding MAX_METRICS_ENTRIES from all sorted sets.

        Returns:
            Dictionary with cleanup results per key
        """
        results: dict[str, int] = {}

        for key in [self.RESPONSE_TIMES, self.LLM_LATENCIES]:
            try:
                count = await self._cache.zcard(key)
                if count > MAX_METRICS_ENTRIES:
                    to_remove = count - MAX_METRICS_ENTRIES
                    removed = await self._cache.zremrangebyrank(key, 0, to_remove - 1)
                    results[key] = removed
                    logger.info(
                        "metrics_cleanup_forced",
                        extra={
                            "key": key,
                            "removed": removed,
                            "remaining": count - removed,
                        },
                    )
                else:
                    results[key] = 0
            except Exception as e:
                logger.warning(
                    "metrics_cleanup_forced_failed",
                    extra={"key": key, "error": str(e)},
                )
                results[key] = -1

        return results

    async def _calculate_percentiles(self, key: str) -> tuple[float, float, float]:
        """
        Calculate p50, p95, p99 percentiles from sorted set.

        Uses nearest-rank method for percentile calculation.
        Handles edge cases where n=1 or very small datasets.

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

            # Use nearest-rank method: percentile index = ceil(P/100 * N) - 1
            # This ensures index is always in valid range [0, n-1]
            def percentile_index(p: float, length: int) -> int:
                """Calculate percentile index using nearest-rank method."""
                if length == 1:
                    return 0
                # For p=50, n=2: ceil(0.5*2)-1 = ceil(1)-1 = 0
                # For p=99, n=2: ceil(0.99*2)-1 = ceil(1.98)-1 = 1
                import math

                idx = math.ceil(p / 100.0 * length) - 1
                return max(0, min(idx, length - 1))

            p50_idx = percentile_index(50, n)
            p95_idx = percentile_index(95, n)
            p99_idx = percentile_index(99, n)

            p50 = values[p50_idx]
            p95 = values[p95_idx]
            p99 = values[p99_idx]

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
            for key, value in zip(keys, values, strict=False):
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
        hit_rate = round(cache_hits / total_cache * 100, 2) if total_cache > 0 else 0.0

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
