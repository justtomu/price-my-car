"""
LLM provider factory for creating provider instances.

Implements the Factory pattern for provider selection based on configuration.
"""

from app.logger import get_logger
from app.providers.llm_provider import LLMProvider
from app.providers.ollama_provider import OllamaProvider
from app.providers.openai_provider import OpenAIProvider
from app.settings import Settings

logger = get_logger("provider_factory")


class LLMProviderFactory:
    """
    Factory for creating LLM provider instances.

    Selects and instantiates the appropriate provider based on
    environment configuration (development -> Ollama, production -> OpenAI).
    """

    @staticmethod
    def create(settings: Settings) -> LLMProvider:
        """
        Create an LLM provider based on settings.

        Args:
            settings: Application settings with provider configuration

        Returns:
            LLMProvider: Configured provider instance (Ollama or OpenAI)

        Raises:
            ValueError: If provider type is not supported
        """
        provider_type = settings.llm_provider

        logger.info(
            "creating_provider",
            extra={
                "provider": provider_type,
                "environment": settings.environment,
                "model": settings.llm_model,
            },
        )

        if provider_type == "ollama":
            return OllamaProvider(settings)
        elif provider_type == "openai":
            return OpenAIProvider(settings)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider_type}")
