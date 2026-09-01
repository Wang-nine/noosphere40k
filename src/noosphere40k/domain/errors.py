"""Stable error types with machine-readable codes (TECHNICAL_SPEC §13; A-02)."""

from __future__ import annotations

from noosphere40k.domain.enums import ErrorCode


class NoosphereError(Exception):
    """Base error carrying a stable error code."""

    code: ErrorCode = ErrorCode.E_CONFIG_INVALID

    def __init__(self, message: str, *, context: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def to_json(self) -> dict[str, object]:
        return {"code": self.code.value, "message": self.message, "context": self.context}


class ConfigInvalidError(NoosphereError):
    code = ErrorCode.E_CONFIG_INVALID


class ProviderUnavailableError(NoosphereError):
    code = ErrorCode.E_PROVIDER_UNAVAILABLE


class ProviderTimeoutError(NoosphereError):
    code = ErrorCode.E_PROVIDER_TIMEOUT


class ProviderSchemaError(NoosphereError):
    code = ErrorCode.E_PROVIDER_SCHEMA


class LoreUncoveredError(NoosphereError):
    code = ErrorCode.E_LORE_UNCOVERED


class LoreConflictError(NoosphereError):
    code = ErrorCode.E_LORE_CONFLICT


class CanonViolationError(NoosphereError):
    code = ErrorCode.E_CANON_VIOLATION


class RuleInvalidActionError(NoosphereError):
    code = ErrorCode.E_RULE_INVALID_ACTION


class SaveConflictError(NoosphereError):
    code = ErrorCode.E_SAVE_CONFLICT


class SaveCorruptError(NoosphereError):
    code = ErrorCode.E_SAVE_CORRUPT


class ContentMissingError(NoosphereError):
    code = ErrorCode.E_CONTENT_MISSING


class MigrationFailedError(NoosphereError):
    code = ErrorCode.E_MIGRATION_FAILED


class UnknownEventError(NoosphereError):
    code = ErrorCode.E_UNKNOWN_EVENT