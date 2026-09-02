"""Provider factory (E-02/G-01).

Creates a provider from AppSettings. Never exposes the key to logs;
``doctor`` reports presence only. Falls back to the offline Stub provider
when no key/provider is configured.
"""

from __future__ import annotations

from noosphere40k.config.settings import AppSettings
from noosphere40k.llm.base import LLMProvider
from noosphere40k.llm.openai_compatible import OpenAICompatibleProvider
from noosphere40k.llm.stub import StubProvider


def build_provider(settings: AppSettings) -> LLMProvider:
    """Build the configured provider, or an offline stub as fallback."""
    if settings.has_api_key and settings.llm.base_url and settings.llm.model:
        key = settings.llm.api_key
        assert key is not None
        return OpenAICompatibleProvider(
            base_url=settings.llm.base_url,
            model=settings.llm.model,
            api_key=key.get_secret_value(),
        )
    # Offline mode: deterministic stub (no network, no key).
    return StubProvider()


__all__ = ["build_provider"]