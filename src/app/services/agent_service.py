"""
Agent service for car pricing using LangChain with get_car_price tool.

Implements a two-step workflow:
1. Extract car make/model using LLM
2. Look up price using the get_car_price tool
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from app.logger import get_logger
from app.providers.llm_provider import LLMProvider
from app.services.langchain_tools import get_car_price
from app.settings import Settings
from app.utils.exceptions import (
    CarNotFoundError,
    LLMExtractionError,
    LLMProviderError,
    LLMTimeoutError,
)
from app.utils.helpers import extract_json_from_text

logger = get_logger("agent_service")

# Exponential backoff configuration
BASE_BACKOFF_SECONDS = 1.0
MAX_BACKOFF_SECONDS = 10.0
BACKOFF_MULTIPLIER = 2.0


@dataclass
class AgentResult:
    """Result from the agent containing car info and price."""

    make: str
    model: str
    price: int


# Extraction prompt - simple and direct
EXTRACTION_PROMPT = """Extract the car make and model from this listing.
Respond with ONLY JSON, no explanation.

Title: {title}
Description: {description}

Respond with ONLY this JSON format:
{{"make": "MANUFACTURER", "model": "MODEL"}}

Examples:
- "2007 Honda Accord EX-L" → {{"make": "Honda", "model": "Accord"}}
- "BMW 3 Series 328i" → {{"make": "BMW", "model": "3 Series"}}

JSON response:"""


class AgentService:
    """
    Service for pricing cars using LLM extraction + get_car_price tool.

    This implements a simple two-step workflow:
    1. LLM extracts car make/model from the listing text
    2. get_car_price tool looks up the price in the database

    This approach works with any LLM (including Ollama) without
    requiring native tool calling support.

    Attributes:
        settings: Application settings
        provider: LLM provider instance
    """

    def __init__(self, settings: Settings, provider: LLMProvider) -> None:
        """
        Initialize agent service.

        Args:
            settings: Application settings
            provider: LLM provider instance
        """
        self._settings = settings
        self._provider = provider
        self._chain: Any = None
        self._chain_lock = asyncio.Lock()  # Async lock for thread-safe chain init

    def _build_chain(self) -> Any:
        """
        Build the LangChain extraction chain.

        Returns:
            Configured LangChain chain (prompt | llm)
        """
        chat_model = self._provider.get_chat_model()
        prompt = ChatPromptTemplate.from_template(EXTRACTION_PROMPT)
        return prompt | chat_model

    def _parse_extraction(self, response: Any) -> dict[str, str]:
        """
        Parse LLM response to extract make/model.

        Args:
            response: LLM response

        Returns:
            Dict with make and model

        Raises:
            ValueError: If parsing fails
        """
        if hasattr(response, "content"):
            text = response.content
        else:
            text = str(response)

        extracted = extract_json_from_text(text)
        if extracted and "make" in extracted and "model" in extracted:
            return extracted

        raise ValueError(f"Could not parse make/model from: {text[:200]}")

    async def get_car_price(self, title: str, description: str) -> AgentResult:
        """
        Extract car info and get price using LLM + tool.

        Two-step workflow:
        1. LLM extracts make/model from listing
        2. get_car_price tool looks up price

        Args:
            title: Car listing title
            description: Car listing description

        Returns:
            AgentResult with make, model, and price

        Raises:
            LLMTimeoutError: If extraction times out
            LLMExtractionError: If extraction fails
            LLMProviderError: If provider is unavailable
            CarNotFoundError: If car is not in database
        """
        logger.info(
            "agent_started",
            extra={
                "provider": self._provider.provider_name,
                "title_length": len(title),
                "description_length": len(description),
            },
        )

        start_time = time.time()
        last_error: Exception | None = None

        # Build chain lazily with lock to prevent race conditions
        if self._chain is None:
            async with self._chain_lock:
                # Double-check after acquiring lock
                if self._chain is None:
                    try:
                        self._chain = self._build_chain()
                    except Exception as e:
                        logger.error("agent_build_failed", extra={"error": str(e)})
                        raise LLMProviderError(
                            f"Failed to build chain: {e}",
                            details={"provider": self._provider.provider_name},
                        ) from e

        # Retry loop for extraction with exponential backoff
        for attempt in range(self._settings.llm_max_retries + 1):
            try:
                # Step 1: Extract make/model using LLM
                logger.debug("extraction_started", extra={"attempt": attempt + 1})

                response = await asyncio.wait_for(
                    self._chain.ainvoke({"title": title, "description": description}),
                    timeout=self._settings.llm_timeout,
                )

                extraction = self._parse_extraction(response)
                make = extraction["make"]
                model = extraction["model"]

                logger.info(
                    "extraction_completed", extra={"make": make, "model": model}
                )

                # Step 2: Use get_car_price tool to look up price
                logger.info(
                    "tool_invoked",
                    extra={"tool": "get_car_price", "make": make, "model": model},
                )

                price = get_car_price.invoke({"make": make, "model": model})

                logger.info(
                    "tool_completed", extra={"tool": "get_car_price", "price": price}
                )

                duration_ms = (time.time() - start_time) * 1000

                logger.info(
                    "agent_completed",
                    extra={
                        "provider": self._provider.provider_name,
                        "make": make,
                        "model": model,
                        "price": price,
                        "duration_ms": round(duration_ms, 2),
                        "attempts": attempt + 1,
                    },
                )

                return AgentResult(make=make, model=model, price=price)

            except TimeoutError:
                duration_ms = (time.time() - start_time) * 1000
                logger.warning(
                    "agent_timeout",
                    extra={
                        "attempt": attempt + 1,
                        "duration_ms": round(duration_ms, 2),
                    },
                )
                last_error = LLMTimeoutError(
                    f"Agent timed out after {self._settings.llm_timeout}s",
                    details={"provider": self._provider.provider_name},
                )

            except CarNotFoundError:
                # Don't retry for car not found - tool worked correctly
                raise

            except Exception as e:
                logger.warning(
                    "agent_attempt_failed",
                    extra={
                        "attempt": attempt + 1,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                last_error = e

            # Apply exponential backoff before retry
            if attempt < self._settings.llm_max_retries:
                backoff_seconds = min(
                    BASE_BACKOFF_SECONDS * (BACKOFF_MULTIPLIER**attempt),
                    MAX_BACKOFF_SECONDS,
                )
                logger.info(
                    "agent_retry",
                    extra={
                        "attempt": attempt + 2,
                        "backoff_seconds": round(backoff_seconds, 2),
                    },
                )
                await asyncio.sleep(backoff_seconds)

        # All retries exhausted
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "agent_failed",
            extra={
                "provider": self._provider.provider_name,
                "attempts": self._settings.llm_max_retries + 1,
                "duration_ms": round(duration_ms, 2),
                "last_error": str(last_error),
            },
        )

        if isinstance(last_error, LLMTimeoutError):
            raise last_error

        raise LLMExtractionError(
            "Agent failed to get car price after all retries",
            details={
                "provider": self._provider.provider_name,
                "attempts": self._settings.llm_max_retries + 1,
                "last_error": str(last_error),
            },
        )

    async def health_check(self) -> bool:
        """Check if agent service is healthy."""
        return await self._provider.health_check()
