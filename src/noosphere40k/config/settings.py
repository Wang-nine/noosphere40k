"""Application settings (TECHNICAL_SPEC §12; A-03).

Precedence: CLI arguments > environment variables > user config file > defaults.
User config is TOML under the platform data directory; keys only via env.
"""

from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path
from typing import Any

from pydantic import SecretStr

from noosphere40k.domain.errors import ConfigInvalidError
from noosphere40k.domain.models import StrictModel

DATA_DIR_ENV = "NOOSPHERE_DATA_DIR"
LOG_LEVEL_ENV = "NOOSPHERE_LOG_LEVEL"
LLM_PROVIDER_ENV = "NOOSPHERE_LLM_PROVIDER"
LLM_BASE_URL_ENV = "NOOSPHERE_LLM_BASE_URL"
LLM_MODEL_ENV = "NOOSPHERE_LLM_MODEL"
LLM_API_KEY_ENV = "NOOSPHERE_LLM_API_KEY"

ENV_MAP: dict[str, str] = {
    DATA_DIR_ENV: "data_dir",
    LOG_LEVEL_ENV: "log_level",
    LLM_PROVIDER_ENV: "llm.provider",
    LLM_BASE_URL_ENV: "llm.base_url",
    LLM_MODEL_ENV: "llm.model",
    LLM_API_KEY_ENV: "llm.api_key",
}


def platform_data_dir() -> Path:
    """Default per-platform data directory (never the current working dir)."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("USERPROFILE")
        if base:
            return Path(base) / "Noosphere"
    elif sys.platform == "darwin":
        base = os.environ.get("HOME")
        if base:
            return Path(base) / "Library" / "Application Support" / "Noosphere"
    base = os.environ.get("XDG_DATA_HOME") or os.environ.get("HOME") or str(Path.home())
    return Path(base) / "noosphere40k"


class LLMSettings(StrictModel):
    provider: str = "none"
    base_url: str | None = None
    model: str | None = None
    api_key: SecretStr | None = None


class AppSettings(StrictModel):
    data_dir: Path
    log_level: str = "INFO"
    llm: LLMSettings = LLMSettings()

    @property
    def db_path(self) -> Path:
        return self.data_dir / "noosphere.db"

    @property
    def config_path(self) -> Path:
        return self.data_dir / "config.toml"

    @property
    def has_api_key(self) -> bool:
        return bool(self.llm.api_key and self.llm.api_key.get_secret_value())


def _read_user_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    try:
        with config_path.open("rb") as fh:
            return tomllib.load(fh)
    except (tomllib.TOMLDecodeError, OSError) as exc:
        raise ConfigInvalidError(
            f"invalid user config at {config_path}",
            context={"path": str(config_path)},
        ) from exc


def _apply_paths(base: dict[str, Any], parts: list[str], value: Any) -> dict[str, Any]:
    node = base
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value
    return base


def load_settings(
    *,
    cli_overrides: dict[str, str] | None = None,
    environ: dict[str, str] | None = None,
    data_dir_override: Path | None = None,
) -> AppSettings:
    """Merge configs with precedence CLI > env > user file > platform defaults."""
    env = environ if environ is not None else dict(os.environ)
    if data_dir_override is not None:
        resolved_data_dir = data_dir_override
    else:
        raw = env.get(DATA_DIR_ENV)
        resolved_data_dir = Path(raw) if raw else platform_data_dir()

    merged: dict[str, Any] = _read_user_config(resolved_data_dir / "config.toml")

    for env_key, env_val in env.items():
        if env_val == "" or env_key not in ENV_MAP:
            continue
        _apply_paths(merged, ENV_MAP[env_key].split("."), env_val)

    for key, value in (cli_overrides or {}).items():
        if value is None or str(value) == "":
            continue
        _apply_paths(merged, key.split("."), str(value))

    data_dir = merged.get("data_dir", resolved_data_dir)
    try:
        Path(data_dir).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ConfigInvalidError(
            f"cannot create data directory: {data_dir}",
            context={"path": str(data_dir)},
        ) from exc

    llm_raw = merged.get("llm", {})
    return AppSettings(
        data_dir=Path(data_dir),
        log_level=str(merged.get("log_level", "INFO")),
        llm=LLMSettings(
            provider=str(llm_raw.get("provider", "none")),
            base_url=llm_raw.get("base_url"),
            model=llm_raw.get("model"),
            api_key=SecretStr(str(llm_raw["api_key"])) if llm_raw.get("api_key") else None,
        ),
    )