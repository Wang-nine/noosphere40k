"""A-02: stable error types."""

from __future__ import annotations

from noosphere40k.domain.errors import (
    MigrationFailedError,
    NoosphereError,
    ProviderUnavailableError,
    UnknownEventError,
)


def test_error_code_attribute_stable() -> None:
    assert ProviderUnavailableError("x").code.value == "E_PROVIDER_UNAVAILABLE"
    assert MigrationFailedError("x").code.value == "E_MIGRATION_FAILED"
    assert UnknownEventError("x").code.value == "E_UNKNOWN_EVENT"


def test_error_to_json_contains_code_message_context() -> None:
    err = NoosphereError("boom", context={"k": 1})
    data = err.to_json()
    assert data["code"] == "E_CONFIG_INVALID"
    assert data["message"] == "boom"
    assert data["context"] == {"k": 1}