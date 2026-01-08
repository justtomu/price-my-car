"""
Ollama LLM provider implementation.

Provides low-level access to Ollama API for local development.
No business logic - only I/O operations.
"""

import httpx
from langchain_community.chat_models import ChatOllama
from langchain_core.language_models.chat_models import BaseChatModel

from app.logger import get_logger
from app.providers.llm_provider import LLMProvider
from app.settings import Settings
from app.utils.exceptions import LLMProviderError

logger = get_logger("ollama_provider")


class OllamaProvider(LLMProvider):
    """
    Ollama LLM provider for local development.

    Connects to locally running Ollama service via HTTP API.
    Primarily used in development environment for testing
    without incurring cloud API costs.

    Attributes:
        settings: Application settings
        base_url: Ollama API base URL
        model: Model name to use (e.g., 'llama3')
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize Ollama provider.

        Args:
            settings: Application settings with Ollama configuration
        """
        self._settings = settings
        self._base_url = settings.ollama_base_url
        self._model = settings.llm_model
        # Reusable HTTP client for health checks
        self._http_client: httpx.AsyncClient | None = None

    @property
    def provider_name(self) -> str:
        """Get provider identifier."""
        return "ollama"

    def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create reusable HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=5.0)
        return self._http_client

    def get_chat_model(self) -> BaseChatModel:
        """
        Get a LangChain ChatOllama instance.

        Returns:
            BaseChatModel: Configured ChatOllama model

        Raises:
            LLMProviderError: If Ollama is not configured
        """
        if not self._base_url:
            raise LLMProviderError(
                "Ollama base URL not configured",
                details={"provider": self.provider_name},
            )

        logger.debug(
            "creating_chat_model",
            extra={
                "provider": self.provider_name,
                "model": self._model,
                "base_url": self._base_url,
            },
        )

        return ChatOllama(
            model=self._model,
            base_url=self._base_url,
            temperature=0,  # Deterministic output for extraction
        )

    async def health_check(self) -> bool:
        """
        Check if Ollama service is available.

        Pings the Ollama API to verify connectivity.
        Uses reusable HTTP client for efficiency.

        Returns:
            bool: True if Ollama is responding, False otherwise
        """
        try:
            client = self._get_http_client()
            response = await client.get(f"{self._base_url}/api/tags")
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
