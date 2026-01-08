"""
FastAPI dependency injection providers.

Provides thread-safe singleton instances of services for dependency injection.
Uses a container class to avoid race conditions with global mutable state.
"""

import threading
from dataclasses import dataclass, field

from app.providers.factory import LLMProviderFactory
from app.providers.llm_provider import LLMProvider
from app.services.agent_service import AgentService
from app.services.cache_service import CacheService
from app.services.metrics_service import MetricsService
from app.services.pricing_service import PricingService
from app.settings import Settings, get_settings


@dataclass
class ServiceContainer:
    """
    Thread-safe container for service instances.

    Encapsulates all service instances to avoid race conditions
    with global mutable variables. Uses a lock for thread-safe
    initialization and access.
    """

    cache_service: CacheService | None = None
    metrics_service: MetricsService | None = None
    pricing_service: PricingService | None = None
    agent_service: AgentService | None = None
    llm_provider: LLMProvider | None = None
    _initialized: bool = field(default=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def is_initialized(self) -> bool:
        """Check if services are initialized (thread-safe)."""
        with self._lock:
            return self._initialized

    def mark_initialized(self) -> None:
        """Mark container as initialized (thread-safe)."""
        with self._lock:
            self._initialized = True

    def mark_shutdown(self) -> None:
        """Mark container as shutdown (thread-safe)."""
        with self._lock:
            self._initialized = False


# Single container instance - immutable reference, mutable contents protected by lock
_container = ServiceContainer()


async def init_services() -> None:
    """
    Initialize all services during application startup.

    Should be called from FastAPI lifespan event.
    Thread-safe: uses lock to prevent double initialization.
    """
    # Check if already initialized (thread-safe)
    if _container.is_initialized:
        return

    with _container._lock:
        # Double-check after acquiring lock
        if _container._initialized:
            return

        settings = get_settings()

        # Initialize cache service and connect to Redis
        _container.cache_service = CacheService(settings)
        await _container.cache_service.connect()

        # Initialize metrics service (depends on cache)
        _container.metrics_service = MetricsService(settings, _container.cache_service)

        # Initialize LLM provider (store reference for cleanup)
        _container.llm_provider = LLMProviderFactory.create(settings)

        # Initialize pricing service
        _container.pricing_service = PricingService()

        # Initialize agent service (uses LangChain tool calling)
        _container.agent_service = AgentService(settings, _container.llm_provider)

        _container._initialized = True


async def shutdown_services() -> None:
    """
    Cleanup services during application shutdown.

    Should be called from FastAPI lifespan event.
    Thread-safe: uses lock to prevent race conditions during shutdown.
    """
    with _container._lock:
        # Close LLM provider HTTP client
        if _container.llm_provider:
            await _container.llm_provider.close()
            _container.llm_provider = None

        # Disconnect from Redis
        if _container.cache_service:
            await _container.cache_service.disconnect()
            _container.cache_service = None

        _container.metrics_service = None
        _container.pricing_service = None
        _container.agent_service = None
        _container._initialized = False


def get_settings_dep() -> Settings:
    """Get application settings."""
    return get_settings()


def get_cache_service() -> CacheService:
    """Get cache service instance (thread-safe)."""
    service = _container.cache_service
    if service is None:
        raise RuntimeError("Cache service not initialized")
    return service


def get_metrics_service() -> MetricsService:
    """Get metrics service instance (thread-safe)."""
    service = _container.metrics_service
    if service is None:
        raise RuntimeError("Metrics service not initialized")
    return service


def get_pricing_service() -> PricingService:
    """Get pricing service instance (thread-safe)."""
    service = _container.pricing_service
    if service is None:
        raise RuntimeError("Pricing service not initialized")
    return service


def get_agent_service() -> AgentService:
    """Get agent service instance (thread-safe)."""
    service = _container.agent_service
    if service is None:
        raise RuntimeError("Agent service not initialized")
    return service


def get_container() -> ServiceContainer:
    """Get the service container (for testing purposes)."""
    return _container
