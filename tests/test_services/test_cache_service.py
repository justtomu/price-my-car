"""
Tests for CacheService.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.llm import CachedResult
from app.services.cache_service import CacheService
from app.settings import Settings


class TestCacheService:
    """Tests for CacheService."""

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Create mock settings."""
        return Settings(
            environment="development",
            ollama_base_url="http://localhost:11434",
            redis_url="redis://localhost:6379",
            cache_ttl=3600,
        )

    @pytest.fixture
    def service(self, mock_settings: Settings) -> CacheService:
        """Create cache service instance."""
        return CacheService(mock_settings)

    def test_not_connected_by_default(self, service: CacheService) -> None:
        """Test service is not connected by default."""
        assert not service.is_connected

    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_connected(
        self, service: CacheService
    ) -> None:
        """Test get returns None when Redis is not connected."""
        result = await service.get("title", "description")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_returns_false_when_not_connected(
        self, service: CacheService
    ) -> None:
        """Test set returns False when Redis is not connected."""
        result = await service.set(
            "title",
            "description",
            CachedResult(make="Honda", model="Accord", price=12500),
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_returns_false_when_not_connected(
        self, service: CacheService
    ) -> None:
        """Test health_check returns False when not connected."""
        result = await service.health_check()
        assert result is False
