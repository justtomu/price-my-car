"""
Pytest configuration and fixtures.

Provides shared fixtures for testing the Price My Car API.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.providers.llm_provider import LLMProvider
from app.schemas.llm import CarExtraction
from app.services.cache_service import CacheService
from app.services.metrics_service import MetricsService
from app.services.pricing_service import PricingService
from app.settings import Settings


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    return Settings(
        environment="development",
        llm_model="llama3",
        ollama_base_url="http://localhost:11434",
        redis_url="redis://localhost:6379",
        log_level="DEBUG",
        cache_ttl=3600,
        llm_timeout=5,
        llm_max_retries=2,
    )


@pytest.fixture
def mock_llm_provider() -> MagicMock:
    """Create mock LLM provider."""
    provider = MagicMock(spec=LLMProvider)
    provider.provider_name = "mock"
    provider.health_check = AsyncMock(return_value=True)
    provider.close = AsyncMock()
    return provider


@pytest.fixture
def mock_cache_service() -> MagicMock:
    """Create mock cache service."""
    cache = MagicMock(spec=CacheService)
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.delete = AsyncMock(return_value=True)
    cache.health_check = AsyncMock(return_value=True)
    cache.is_connected = True
    cache.incr = AsyncMock(return_value=1)
    cache.get_raw = AsyncMock(return_value="0")
    cache.zadd = AsyncMock(return_value=True)
    cache.zrange_with_scores = AsyncMock(return_value=[])
    cache.scan_keys = AsyncMock(return_value=[])
    cache.mget = AsyncMock(return_value=[])
    return cache


@pytest.fixture
def mock_metrics_service(
    mock_settings: Settings, mock_cache_service: MagicMock
) -> MetricsService:
    """Create metrics service with mock cache."""
    return MetricsService(mock_settings, mock_cache_service)


@pytest.fixture
def mock_pricing_service() -> PricingService:
    """Create pricing service."""
    return PricingService()


@pytest.fixture
def sample_car_extraction() -> CarExtraction:
    """Sample successful car extraction."""
    return CarExtraction(make="Honda", model="Accord")


@pytest.fixture
def sample_request_data() -> dict[str, str]:
    """Sample request data for /price-car endpoint."""
    return {
        "title": "2007 Honda Accord EX-L V6",
        "description": "Clean title, one owner, 150k miles, leather seats, runs great",
    }


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create synchronous test client."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
