"""A-03: settings precedence, env mapping, key secrecy."""

from __future__ import annotations

from pathlib import Path

import pytest

from noosphere40k.cli.app import doctor_command
from noosphere40k.config.settings import (
    LLM_API_KEY_ENV,
    LOG_LEVEL_ENV,
    load_settings,
)
from noosphere40k.domain.errors import ConfigInvalidError
from noosphere40k.security.secrets import redact_text, scan_for_keys


def test_defaults_when_nothing_configured(tmp_path: Path) -> None:
    settings = load_settings(environ={}, data_dir_override=tmp_path)
    assert settings.llm.provider == "none"
    assert settings.log_level == "INFO"
    assert settings.has_api_key is False
    assert settings.db_path == tmp_path / "noosphere.db"


def test_env_overrides_defaults(tmp_path: Path) -> None:
    settings = load_settings(
        environ={"NOOSPHERE_LLM_PROVIDER": "openai_compatible", LOG_LEVEL_ENV: "DEBUG"},
        data_dir_override=tmp_path,
    )
    assert settings.llm.provider == "openai_compatible"
    assert settings.log_level == "DEBUG"


def test_cli_overrides_env(tmp_path: Path) -> None:
    settings = load_settings(
        environ={LLM_API_KEY_ENV: "sk-test-not-a-real-key"},
        cli_overrides={"llm.provider": "stub"},
        data_dir_override=tmp_path,
    )
    assert settings.llm.provider == "stub"
    assert settings.has_api_key is True
    assert settings.llm.api_key is not None
    assert settings.llm.api_key.get_secret_value() == "sk-test-not-a-real-key"


def test_empty_env_is_ignored(tmp_path: Path) -> None:
    settings = load_settings(
        environ={"NOOSPHERE_LLM_PROVIDER": "", "NOOSPHERE_LLM_API_KEY": ""},
        data_dir_override=tmp_path,
    )
    assert settings.llm.provider == "none"
    assert settings.has_api_key is False


def test_doctor_output_never_contains_key_value(tmp_path: Path) -> None:
    settings = load_settings(
        environ={LLM_API_KEY_ENV: "sk-super-secret-xyz"},
        data_dir_override=tmp_path,
    )
    result = doctor_command(settings)
    text = "\n".join(result.lines)
    assert "sk-super-secret-xyz" not in text
    assert "present" in text


def test_redact_text_and_scan(tmp_path: Path) -> None:
    text_args = "api_key=sk-super-secret-value"
    assert "[REDACTED]" in redact_text(text_args)
    assert scan_for_keys([text_args]) == 1


def test_invalid_config_file_raises_stable_error(tmp_path: Path) -> None:
    (tmp_path / "config.toml").write_text("not = [valid toml", encoding="utf-8")
    with pytest.raises(ConfigInvalidError) as exc_info:
        load_settings(environ={}, data_dir_override=tmp_path)
    assert exc_info.value.code.value == "E_CONFIG_INVALID"