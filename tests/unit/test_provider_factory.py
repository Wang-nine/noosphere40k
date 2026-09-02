"""E-02 factory: stub fallback vs configured provider."""

from __future__ import annotations

from pathlib import Path

from noosphere40k.config.settings import load_settings
from noosphere40k.llm.factory import build_provider
from noosphere40k.llm.openai_compatible import OpenAICompatibleProvider
from noosphere40k.llm.stub import StubProvider


def test_builds_stub_without_key(tmp_path: Path) -> None:
    settings = load_settings(environ={}, data_dir_override=tmp_path)
    provider = build_provider(settings)
    assert isinstance(provider, StubProvider)


def test_builds_openai_with_key_and_url(tmp_path: Path) -> None:
    settings = load_settings(
        environ={
            "NOOSPHERE_LLM_API_KEY": "sk-test-not-real",
            "NOOSPHERE_LLM_BASE_URL": "https://api.example.test/v1",
            "NOOSPHERE_LLM_MODEL": "gpt-test",
        },
        data_dir_override=tmp_path,
    )
    provider = build_provider(settings)
    assert isinstance(provider, OpenAICompatibleProvider)


def test_partial_config_falls_back_to_stub(tmp_path: Path) -> None:
    # key present but no base_url/model -> stub (never call network)
    settings = load_settings(
        environ={"NOOSPHERE_LLM_API_KEY": "sk-test-not-real"},
        data_dir_override=tmp_path,
    )
    provider = build_provider(settings)
    assert isinstance(provider, StubProvider)