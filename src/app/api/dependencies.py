"""
FastAPI dependency injection providers.

Provides singleton instances of services for dependency injection.
"""

from app.providers.factory import LLMProviderFactory
from app.providers.llm_provider import LLMProvider
from app.services.agent_service import AgentService
from app.services.cache_service import CacheService
from app.services.metrics_service import MetricsService
from app.services.pricing_service import PricingService
from app.settings import Settings, get_settings

# Global service instances (initialized during app startup)
_cache_service: CacheService | None = None
_metrics_service: MetricsService | None = None
_pricing_service: PricingService | None = None
_agent_service: AgentService | None = None
_llm_provider: LLMProvider | None = None


async def init_services() -> None:
    """
    Initialize all services during application startup.

    Should be called from FastAPI lifespan event.
    """
    global _cache_service, _metrics_service, _pricing_service, _agent_service, _llm_provider

    settings = get_settings()

    # Initialize cache service and connect to Redis
    _cache_service = CacheService(settings)
    await _cache_service.connect()

    # Initialize metrics service (depends on cache)
    _metrics_service = MetricsService(settings, _cache_service)

    # Initialize LLM provider (store reference for cleanup)
    _llm_provider = LLMProviderFactory.create(settings)

    # Initialize pricing service
    _pricing_service = PricingService()

    # Initialize agent service (uses LangChain tool calling)
    _agent_service = AgentService(settings, _llm_provider)


async def shutdown_services() -> None:
    """
    Cleanup services during application shutdown.

    Should be called from FastAPI lifespan event.
    """
    global _cache_service, _llm_provider

    # Close LLM provider HTTP client
    if _llm_provider:
        await _llm_provider.close()

    # Disconnect from Redis
    if _cache_service:
        await _cache_service.disconnect()


def get_settings_dep() -> Settings:
    """Get application settings."""
    return get_settings()


def get_cache_service() -> CacheService:
    """Get cache service instance."""
    if _cache_service is None:
        raise RuntimeError("Cache service not initialized")
    return _cache_service


def get_metrics_service() -> MetricsService:
    """Get metrics service instance."""
    if _metrics_service is None:
        raise RuntimeError("Metrics service not initialized")
    return _metrics_service


def get_pricing_service() -> PricingService:
    """Get pricing service instance."""
    if _pricing_service is None:
        raise RuntimeError("Pricing service not initialized")
    return _pricing_service


def get_agent_service() -> AgentService:
    """Get agent service instance."""
    if _agent_service is None:
        raise RuntimeError("Agent service not initialized")
    return _agent_service
