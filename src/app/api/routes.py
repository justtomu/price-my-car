"""
API route handlers for the Price My Car service.

Implements endpoint handlers that orchestrate services
and handle request/response formatting.
"""

import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.dependencies import (
    get_agent_service,
    get_cache_service,
    get_metrics_service,
)
from app.logger import get_logger, set_request_id
from app.schemas.llm import CachedResult
from app.schemas.request import PriceCarRequest
from app.schemas.response import ErrorResponse, HealthMetricsResponse, PriceCarResponse
from app.services.agent_service import AgentService
from app.services.cache_service import CacheService
from app.services.metrics_service import MetricsService
from app.utils.exceptions import (
    CarNotFoundError,
    LLMExtractionError,
    LLMProviderError,
    LLMTimeoutError,
)
from app.utils.helpers import generate_request_id

logger = get_logger("api_routes")

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/price-car",
    response_model=PriceCarResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Failed to extract car info"},
        404: {"model": ErrorResponse, "description": "Car make/model not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        503: {"model": ErrorResponse, "description": "LLM service unavailable"},
        504: {"model": ErrorResponse, "description": "LLM request timeout"},
    },
    summary="Get car price from listing",
    description="Extract car make/model from listing and return estimated price using LangChain agent with tools",
)
@limiter.limit("100/minute")
async def price_car(
    request: Request,
    body: PriceCarRequest,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
    metrics_service: Annotated[MetricsService, Depends(get_metrics_service)],
) -> PriceCarResponse:
    """
    Process car listing to extract make/model and return price.

    Uses LangChain agent with get_car_price tool for end-to-end processing.

    Workflow:
    1. Check cache for existing result
    2. If cache miss, use agent to extract info AND get price via tool
    3. Cache successful result
    4. Record metrics

    Args:
        request: HTTP request (for rate limiting)
        body: Car listing with title and description
        agent_service: LangChain agent service with tools
        cache_service: Cache service
        metrics_service: Metrics service

    Returns:
        PriceCarResponse with make, model, price, and request_id
    """
    start_time = time.time()
    request_id = generate_request_id()
    set_request_id(request_id)

    logger.info(
        "request_received",
        extra={
            "endpoint": "/price-car",
            "title_length": len(body.title),
            "description_length": len(body.description),
        },
    )

    # Record incoming request
    await metrics_service.record_request()

    try:
        # Check cache first
        cached = await cache_service.get(body.title, body.description)

        if cached:
            await metrics_service.record_cache_hit()
            await metrics_service.record_success()

            duration_ms = (time.time() - start_time) * 1000
            await metrics_service.record_response_time(duration_ms)

            logger.info(
                "response_from_cache",
                extra={
                    "make": cached.make,
                    "model": cached.model,
                    "price": cached.price,
                    "duration_ms": round(duration_ms, 2),
                },
            )

            return PriceCarResponse(
                make=cached.make,
                model=cached.model,
                price=cached.price,
                request_id=request_id,
            )

        # Cache miss - use agent with tool calling
        await metrics_service.record_cache_miss()

        # Agent extracts car info AND calls get_car_price tool
        agent_start = time.time()
        result = await agent_service.get_car_price(body.title, body.description)
        agent_duration_ms = (time.time() - agent_start) * 1000

        await metrics_service.record_llm_latency(agent_duration_ms)
        await metrics_service.record_llm_success()
        await metrics_service.record_car_found(result.make)

        # Cache the successful result
        await cache_service.set(
            body.title,
            body.description,
            CachedResult(make=result.make, model=result.model, price=result.price),
        )

        # Record success metrics
        await metrics_service.record_success()
        duration_ms = (time.time() - start_time) * 1000
        await metrics_service.record_response_time(duration_ms)

        logger.info(
            "response_sent",
            extra={
                "make": result.make,
                "model": result.model,
                "price": result.price,
                "duration_ms": round(duration_ms, 2),
                "cached": False,
            },
        )

        return PriceCarResponse(
            make=result.make,
            model=result.model,
            price=result.price,
            request_id=request_id,
        )

    except LLMTimeoutError as e:
        await metrics_service.record_error()
        await metrics_service.record_llm_failure()
        logger.error("llm_timeout", extra={"error": str(e)})
        raise HTTPException(
            status_code=504,
            detail=ErrorResponse(
                error="LLM request timeout",
                request_id=request_id,
            ).model_dump(),
        ) from e

    except LLMProviderError as e:
        await metrics_service.record_error()
        await metrics_service.record_llm_failure()
        logger.error("llm_provider_error", extra={"error": str(e)})
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse(
                error="LLM service unavailable",
                request_id=request_id,
            ).model_dump(),
        ) from e

    except LLMExtractionError as e:
        await metrics_service.record_error()
        await metrics_service.record_llm_failure()
        logger.error("llm_extraction_error", extra={"error": str(e)})
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="Failed to extract car info",
                request_id=request_id,
            ).model_dump(),
        ) from e

    except CarNotFoundError as e:
        await metrics_service.record_error()
        await metrics_service.record_car_not_found()
        logger.warning("car_not_found", extra={"error": str(e)})
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="Car make/model not found",
                request_id=request_id,
            ).model_dump(),
        ) from e

    except Exception as e:
        await metrics_service.record_error()
        logger.error(
            "unexpected_error",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal service error",
                request_id=request_id,
            ).model_dump(),
        ) from e


@router.get(
    "/health",
    summary="Health check",
    description="Basic health check endpoint",
)
async def health_check() -> dict[str, str]:
    """
    Basic health check endpoint.

    Returns:
        dict with status "ok"
    """
    return {"status": "ok"}


@router.get(
    "/health/metrics",
    response_model=HealthMetricsResponse,
    summary="Get service metrics",
    description="Get comprehensive service metrics and statistics",
)
async def get_metrics(
    metrics_service: Annotated[MetricsService, Depends(get_metrics_service)],
) -> HealthMetricsResponse:
    """
    Get comprehensive service metrics.

    Returns:
        HealthMetricsResponse with request, cache, LLM, car, and performance stats
    """
    return await metrics_service.get_metrics()
