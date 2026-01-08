"""
OpenAI LLM provider implementation.

Provides low-level access to OpenAI API for production use.
No business logic - only I/O operations.
"""

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.logger import get_logger
from app.providers.llm_provider import LLMProvider
from app.settings import Settings
from app.utils.exceptions import LLMProviderError

logger = get_logger("openai_provider")


class OpenAIProvider(LLMProvider):
    """
    OpenAI LLM provider for production use.

    Connects to OpenAI API using the official SDK.
    Used in production environment for reliable, high-quality
    car information extraction.

    Attributes:
        settings: Application settings
        api_key: OpenAI API key
        model: Model name to use (e.g., 'gpt-4o-mini')
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize OpenAI provider.

        Args:
            settings: Application settings with OpenAI configuration
        """
        self._settings = settings
        self._api_key = settings.openai_api_key
        self._model = settings.llm_model
        # Reusable HTTP client for health checks
        self._http_client: httpx.AsyncClient | None = None

    @property
    def provider_name(self) -> str:
        """Get provider identifier."""
        return "openai"

    def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create reusable HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=5.0)
        return self._http_client

    def get_chat_model(self) -> BaseChatModel:
        """
        Get a LangChain ChatOpenAI instance.

        Returns:
            BaseChatModel: Configured ChatOpenAI model

        Raises:
            LLMProviderError: If API key is not configured
        """
        if not self._api_key:
            raise LLMProviderError(
                "OpenAI API key not configured",
                details={"provider": self.provider_name},
            )

        logger.debug(
            "creating_chat_model",
            extra={
                "provider": self.provider_name,
                "model": self._model,
            },
        )

        return ChatOpenAI(
            model=self._model,
            api_key=self._api_key,
            temperature=0,  # Deterministic output for extraction
        )

    async def health_check(self) -> bool:
        """
        Check if OpenAI API is accessible.

        Makes a lightweight API call to verify connectivity and auth.
        Uses reusable HTTP client for efficiency.

        Returns:
            bool: True if OpenAI API is responding, False otherwise
        """
        if not self._api_key:
            return False

        try:
            client = self._get_http_client()
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            return response.status_code == 200
        except httpx.RequestError as e:
            logger.warning(
                "health_check_failed",
                extra={
                    "provider": self.provider_name,
                    "error": str(e),
                },
            )
            return False

    async def close(self) -> None:
        """Close HTTP client on shutdown."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
