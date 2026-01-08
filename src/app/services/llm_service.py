"""
LLM service for car information extraction.

Implements business logic for LLM-based extraction using LangChain
chains with OutputParser for structured output.

Note: This service provides an alternative implementation to AgentService.
Use AgentService for production as it integrates with the get_car_price tool.
"""

import asyncio
import time
from typing import Any

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.logger import get_logger
from app.providers.llm_provider import LLMProvider
from app.schemas.llm import CarExtraction
from app.settings import Settings
from app.utils.exceptions import LLMExtractionError, LLMProviderError, LLMTimeoutError
from app.utils.helpers import extract_json_from_text

logger = get_logger("llm_service")

# Exponential backoff configuration
BASE_BACKOFF_SECONDS = 1.0
MAX_BACKOFF_SECONDS = 10.0
BACKOFF_MULTIPLIER = 2.0

# Extraction prompt template - optimized for llama3
EXTRACTION_PROMPT = """Extract the car make and model from this listing. Respond ONLY with JSON, no explanation.

Title: {title}
Description: {description}

Respond with ONLY this JSON format, nothing else:
{{"make": "MANUFACTURER", "model": "MODEL"}}

Examples:
- "2007 Honda Accord EX-L" → {{"make": "Honda", "model": "Accord"}}
- "BMW 3 Series 328i" → {{"make": "BMW", "model": "3 Series"}}
- "Tesla Model Y" → {{"make": "Tesla", "model": "Model Y"}}

JSON response:"""


class LLMService:
    """
    Service for extracting car information using LLM.

    Uses LangChain chains with PydanticOutputParser for structured
    extraction. Implements retry logic, timeout handling, and
    comprehensive error handling.

    Attributes:
        settings: Application settings
        provider: LLM provider instance
        parser: Pydantic output parser for CarExtraction
    """

    def __init__(self, settings: Settings, provider: LLMProvider) -> None:
        """
        Initialize LLM service.

        Args:
            settings: Application settings
            provider: LLM provider instance
        """
        self._settings = settings
        self._provider = provider
        self._parser: PydanticOutputParser[CarExtraction] = PydanticOutputParser(
            pydantic_object=CarExtraction
        )
        self._chain: Any = None
        self._chain_lock = asyncio.Lock()  # Async lock for thread-safe chain init

    def _build_chain(self) -> Any:
        """
        Build the LangChain extraction chain.

        Returns:
            Configured LangChain chain (prompt | llm)
        """
        # Get chat model from provider
        chat_model = self._provider.get_chat_model()

        # Build simple prompt without Pydantic format instructions
        # llama3 works better with simpler prompts
        prompt = ChatPromptTemplate.from_template(EXTRACTION_PROMPT)

        # Return chain without parser - we'll parse manually with fallback
        chain = prompt | chat_model

        return chain
    
    def _parse_response(self, response: Any) -> CarExtraction:
        """
        Parse LLM response with fallback for non-JSON responses.
        
        Args:
            response: LLM response (AIMessage or string)
            
        Returns:
            CarExtraction object
            
        Raises:
            ValueError: If parsing fails
        """
        # Get text content
        if hasattr(response, "content"):
            text = response.content
        else:
            text = str(response)
        
        # Try standard Pydantic parsing first
        try:
            return self._parser.parse(text)
        except Exception:
            pass
        
        # Try fallback JSON extraction
        extracted = extract_json_from_text(text)
        if extracted:
            return CarExtraction(
                make=extracted["make"],
                model=extracted["model"]
            )
        
        raise ValueError(f"Could not parse response: {text[:200]}")

    async def extract_car_info(
        self, title: str, description: str
    ) -> CarExtraction:
        """
        Extract car make and model from listing.

        Uses LangChain chain with OutputParser for structured extraction.
        Implements timeout and retry logic.

        Args:
            title: Car listing title
            description: Car listing description

        Returns:
            CarExtraction: Extracted car information

        Raises:
            LLMTimeoutError: If extraction times out
            LLMExtractionError: If extraction fails after retries
            LLMProviderError: If provider is unavailable
        """
        logger.info(
            "extraction_started",
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
                        logger.error(
                            "chain_build_failed",
                            extra={"error": str(e)},
                        )
                        raise LLMProviderError(
                            f"Failed to build LLM chain: {e}",
                            details={"provider": self._provider.provider_name},
                        ) from e

        # Retry loop with exponential backoff
        for attempt in range(self._settings.llm_max_retries + 1):
            try:
                # Execute with timeout
                response = await asyncio.wait_for(
                    self._chain.ainvoke({"title": title, "description": description}),
                    timeout=self._settings.llm_timeout,
                )
                
                # Parse response with fallback
                result = self._parse_response(response)

                duration_ms = (time.time() - start_time) * 1000

                logger.info(
                    "extraction_completed",
                    extra={
                        "provider": self._provider.provider_name,
                        "make": result.make,
                        "model": result.model,
                        "duration_ms": round(duration_ms, 2),
                        "attempts": attempt + 1,
                    },
                )

                return result

            except asyncio.TimeoutError:
                duration_ms = (time.time() - start_time) * 1000
                logger.warning(
                    "extraction_timeout",
                    extra={
                        "attempt": attempt + 1,
                        "timeout_seconds": self._settings.llm_timeout,
                        "duration_ms": round(duration_ms, 2),
                    },
                )
                last_error = LLMTimeoutError(
                    f"LLM extraction timed out after {self._settings.llm_timeout}s",
                    details={
                        "provider": self._provider.provider_name,
                        "timeout": self._settings.llm_timeout,
                    },
                )

            except Exception as e:
                logger.warning(
                    "extraction_attempt_failed",
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
                    BASE_BACKOFF_SECONDS * (BACKOFF_MULTIPLIER ** attempt),
                    MAX_BACKOFF_SECONDS
                )
                logger.info(
                    "extraction_retry",
                    extra={
                        "attempt": attempt + 2,
                        "max_retries": self._settings.llm_max_retries,
                        "backoff_seconds": round(backoff_seconds, 2),
                    },
                )
                await asyncio.sleep(backoff_seconds)

        # All retries exhausted
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "extraction_failed",
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
            "Failed to extract car information after all retries",
            details={
                "provider": self._provider.provider_name,
                "attempts": self._settings.llm_max_retries + 1,
                "last_error": str(last_error),
            },
        )

    async def health_check(self) -> bool:
        """
        Check if LLM service is healthy.

        Returns:
            bool: True if provider is available
        """
        return await self._provider.health_check()
