"""
Price My Car API - Main Application Entry Point.

FastAPI application with LLM-based car information extraction
and pricing lookup functionality.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app import __version__
from app.api.dependencies import init_services, shutdown_services
from app.api.routes import router
from app.logger import get_logger, setup_logging
from app.settings import get_settings

# Initialize logging
setup_logging()
logger = get_logger("main")

# Get settings
settings = get_settings()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan event handler.

    Initializes services on startup and cleans up on shutdown.
    """
    logger.info(
        "application_starting",
        extra={
            "version": __version__,
            "environment": settings.environment,
            "llm_provider": settings.llm_provider,
            "llm_model": settings.llm_model,
        },
    )

    # Initialize services
    await init_services()
    logger.info("services_initialized")

    yield

    # Cleanup
    logger.info("application_shutting_down")
    await shutdown_services()
    logger.info("services_shutdown")


# Create FastAPI application
app = FastAPI(
    title="Price My Car API",
    description="AI-powered car pricing API using LLM for make/model extraction",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add rate limiter to app state
app.state.limiter = limiter

# Add rate limit exceeded handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# Add CORS middleware
# NOTE: allow_credentials=True with allow_origins=["*"] is a security risk
# In production, always set explicit origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
)


# Include API routes
app.include_router(router)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """
    Root endpoint redirect to documentation.
    """
    return {
        "message": "Price My Car API",
        "version": __version__,
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
