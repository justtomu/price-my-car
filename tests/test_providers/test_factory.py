"""
Tests for LLMProviderFactory.
"""

from app.providers.factory import LLMProviderFactory
from app.providers.ollama_provider import OllamaProvider
from app.providers.openai_provider import OpenAIProvider
from app.settings import Settings


class TestLLMProviderFactory:
    """Tests for LLMProviderFactory."""

    def test_create_ollama_provider(self) -> None:
        """Test creating Ollama provider for development."""
        settings = Settings(
            environment="development",
            ollama_base_url="http://localhost:11434",
        )
        provider = LLMProviderFactory.create(settings)
        assert isinstance(provider, OllamaProvider)
        assert provider.provider_name == "ollama"

    def test_create_openai_provider(self) -> None:
        """Test creating OpenAI provider for production."""
        settings = Settings(
            environment="production",
            openai_api_key="sk-test-key",
        )
        provider = LLMProviderFactory.create(settings)
        assert isinstance(provider, OpenAIProvider)
        assert provider.provider_name == "openai"
