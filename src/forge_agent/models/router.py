from __future__ import annotations

from forge_agent.config import Settings
from forge_agent.core.errors import UnsupportedProviderError
from .compatible import OpenAICompatibleProvider
from .openai import OpenAIProvider


def create_provider(settings: Settings):
    if settings.provider == "openai":
        return OpenAIProvider(
            api_key=settings.api_key, base_url=settings.api_base_url, model_name=settings.model,
            timeout=settings.command_timeout, retry_attempts=settings.retry_attempts, retry_backoff=settings.retry_backoff,
            api_key_env="OPENAI_API_KEY",
        )
    if settings.provider == "groq":
        return OpenAICompatibleProvider(
            api_key=settings.api_key, base_url=settings.api_base_url, model_name=settings.model,
            timeout=settings.command_timeout, retry_attempts=settings.retry_attempts, retry_backoff=settings.retry_backoff,
            api_key_env="GROQ_API_KEY",
        )
    if settings.provider == "compatible":
        return OpenAICompatibleProvider(
            api_key=settings.api_key, base_url=settings.api_base_url, model_name=settings.model,
            timeout=settings.command_timeout, retry_attempts=settings.retry_attempts, retry_backoff=settings.retry_backoff,
            api_key_env="FORGE_API_KEY",
        )
    if settings.provider in {"anthropic", "gemini"}:
        raise UnsupportedProviderError(
            f"{settings.provider} is recognized but not implemented yet. Use provider=openai or compatible."
        )
    raise UnsupportedProviderError(f"Unknown provider '{settings.provider}'.")