"""
API routes and endpoint handlers.
"""

from app.api.dependencies import (
    get_agent_service,
    get_cache_service,
    get_metrics_service,
    get_pricing_service,
    init_services,
    shutdown_services,
)
from app.api.routes import router

__all__ = [
    "router",
    "init_services",
    "shutdown_services",
    "get_agent_service",
    "get_cache_service",
    "get_metrics_service",
    "get_pricing_service",
]
