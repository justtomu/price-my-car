"""
Abstract base class for LLM providers.

Defines the minimal interface that all LLM providers must implement.
Providers are responsible ONLY for I/O operations - no business logic.
"""

from abc import ABC, abstractmethod

from langchain_core.language_models.chat_models import BaseChatModel


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    Providers implement low-level access to LLM services (Ollama, OpenAI, etc.)
    They are responsible for:
        - Creating LangChain ChatModel instances
        - Health checking the underlying service
        - Basic error handling for network/API issues
        - Managing HTTP client lifecycle

    They are NOT responsible for:
        - Retry logic (handled by LLMService)
        - Prompt engineering (handled by LLMService)
        - Output validation (handled by LangChain OutputParser)
        - Business logic of any kind
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Get the provider identifier.

        Returns:
            str: Provider name (e.g., 'ollama', 'openai')
        """
        pass

    @abstractmethod
    def get_chat_model(self) -> BaseChatModel:
        """
        Get a LangChain ChatModel instance for this provider.

        Returns:
            BaseChatModel: Configured LangChain chat model

        Raises:
            LLMProviderError: If provider is not configured or unavailable
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the LLM service is available and responding.

        Returns:
            bool: True if service is healthy, False otherwise
        """
        pass

    async def close(self) -> None:
        """
        Clean up resources (HTTP clients, connections, etc.).

        Should be called during application shutdown.
        Default implementation does nothing - subclasses override if needed.
        """
        # Not abstract - default no-op implementation is intentional
        # Subclasses override this only if they have resources to clean up
        return None
