"""
Mock provider fixtures for testing.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage

from app.providers.llm_provider import LLMProvider


def create_mock_provider(
    provider_name: str = "mock",
    health_status: bool = True,
) -> MagicMock:
    """
    Create a mock LLM provider for testing.

    Args:
        provider_name: Name of the mock provider
        health_status: Health check return value

    Returns:
        MagicMock configured as LLMProvider
    """
    provider = MagicMock(spec=LLMProvider)
    provider.provider_name = provider_name
    provider.health_check = AsyncMock(return_value=health_status)

    # Create mock chat model
    mock_chat_model = MagicMock(spec=BaseChatModel)
    mock_chat_model.ainvoke = AsyncMock(
        return_value=AIMessage(content='{"make": "Honda", "model": "Accord"}')
    )
    provider.get_chat_model.return_value = mock_chat_model

    return provider


def create_failing_provider() -> MagicMock:
    """
    Create a mock provider that fails health checks.

    Returns:
        MagicMock configured to fail
    """
    provider = MagicMock(spec=LLMProvider)
    provider.provider_name = "failing"
    provider.health_check = AsyncMock(return_value=False)
    provider.get_chat_model.side_effect = Exception("Provider unavailable")
    return provider
