"""
Application settings using Pydantic BaseSettings.

Configuration is loaded from environment variables with sensible defaults
for development. Production environment requires explicit configuration.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration settings.

    Attributes:
        environment: Current environment (development/production)
        llm_provider: LLM provider to use (auto-set based on environment)
        llm_model: Model name for LLM calls
        ollama_base_url: Base URL for Ollama API (development only)
        openai_api_key: OpenAI API key (production only)
        redis_url: Redis connection URL
        log_level: Logging level
        cache_ttl: Cache time-to-live in seconds
        llm_timeout: LLM request timeout in seconds
        llm_max_retries: Maximum retry attempts for LLM calls
        stats_retention_days: Days to retain metrics in Redis
        cors_origins: Allowed CORS origins
        rate_limit_per_minute: Rate limit per client per minute
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Literal["development", "production"] = Field(
        default="development",
        description="Current environment (development uses Ollama, production uses OpenAI)",
    )

    # LLM Configuration
    llm_provider: Literal["ollama", "openai"] = Field(
        default="ollama",
        description="LLM provider (auto-set based on environment)",
    )
    llm_model: str = Field(
        default="llama3",
        description="Model name for LLM calls",
    )

    # Ollama Configuration (development)
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for Ollama API",
    )

    # OpenAI Configuration (production)
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key (required for production)",
    )

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL",
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level",
    )

    # Cache Configuration
    cache_ttl: int = Field(
        default=3600,
        ge=60,
        description="Cache TTL in seconds (default: 1 hour)",
    )

    # LLM Request Configuration
    llm_timeout: int = Field(
        default=5,
        ge=1,
        le=30,
        description="LLM request timeout in seconds",
    )
    llm_max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum retry attempts for LLM calls",
    )

    # Metrics Configuration
    stats_retention_days: int = Field(
        default=7,
        ge=1,
        le=90,
        description="Days to retain metrics in Redis",
    )

    # CORS Configuration
    # NOTE: In production, set explicit origins instead of ["*"]
    # Example: ["https://myapp.com", "https://admin.myapp.com"]
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins (set explicit origins in production)",
    )
    cors_allow_credentials: bool = Field(
        default=False,
        description="Allow credentials in CORS requests (set to False with wildcard origins)",
    )

    # Rate Limiting
    rate_limit_per_minute: int = Field(
        default=100,
        ge=1,
        description="Rate limit per client per minute",
    )

    @model_validator(mode="after")
    def set_provider_and_validate(self) -> "Settings":
        """
        Auto-set LLM provider based on environment and validate required fields.

        - Development: uses Ollama, validates ollama_base_url
        - Production: uses OpenAI, validates openai_api_key
        """
        # Auto-set provider based on environment
        if self.environment == "production":
            self.llm_provider = "openai"
            # Set default production model if using dev default
            if self.llm_model == "llama3":
                self.llm_model = "gpt-4o-mini"
        else:
            self.llm_provider = "ollama"

        # Validate required fields based on environment
        if self.environment == "production" and not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required when ENVIRONMENT=production"
            )

        if self.environment == "development" and not self.ollama_base_url:
            raise ValueError(
                "OLLAMA_BASE_URL is required when ENVIRONMENT=development"
            )

        return self

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Settings: Application settings instance (cached)
    """
    return Settings()
