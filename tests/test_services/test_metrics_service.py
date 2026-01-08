"""
Tests for MetricsService.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.cache_service import CacheService
from app.services.metrics_service import MetricsService
from app.settings import Settings


class TestMetricsService:
    """Tests for MetricsService."""

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Create mock settings."""
        return Settings(
            environment="development",
            ollama_base_url="http://localhost:11434",
            redis_url="redis://localhost:6379",
            stats_retention_days=7,
        )

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Create mock cache service."""
        cache = MagicMock(spec=CacheService)
        cache.incr = AsyncMock(return_value=1)
        cache.get_raw = AsyncMock(return_value="10")
        cache.health_check = AsyncMock(return_value=True)
        cache.zadd = AsyncMock(return_value=True)
        cache.zrange_with_scores = AsyncMock(return_value=[])
        cache.scan_keys = AsyncMock(return_value=[])
        cache.mget = AsyncMock(return_value=[])
        return cache

    @pytest.fixture
    def service(self, mock_settings: Settings, mock_cache: MagicMock) -> MetricsService:
        """Create metrics service instance."""
        return MetricsService(mock_settings, mock_cache)

    @pytest.mark.asyncio
    async def test_record_request(
        self, service: MetricsService, mock_cache: MagicMock
    ) -> None:
        """Test recording request increments counter."""
        await service.record_request()
        mock_cache.incr.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_success(
        self, service: MetricsService, mock_cache: MagicMock
    ) -> None:
        """Test recording success increments counter."""
        await service.record_success()
        mock_cache.incr.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_cache_hit(
        self, service: MetricsService, mock_cache: MagicMock
    ) -> None:
        """Test recording cache hit increments counter."""
        await service.record_cache_hit()
        mock_cache.incr.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_llm_call(
        self, service: MetricsService, mock_cache: MagicMock
    ) -> None:
        """Test recording LLM call increments counters."""
        await service.record_llm_call("ollama")
        assert mock_cache.incr.call_count == 2  # total + provider

    @pytest.mark.asyncio
    async def test_get_metrics(
        self, service: MetricsService, mock_cache: MagicMock
    ) -> None:
        """Test getting metrics returns response."""
        metrics = await service.get_metrics()
        assert metrics.status in ["healthy", "degraded"]
        assert metrics.environment == "development"
