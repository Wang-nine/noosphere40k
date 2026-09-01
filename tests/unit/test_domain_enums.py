"""A-02: enum value stability contracts; unknown values are strictly rejected."""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from noosphere40k.domain.enums import (
    AttributeId,
    CampaignStatus,
    ConfidenceLevel,
    ErrorCode,
    LifeStage,
    ReviewStatus,
)


@pytest.mark.parametrize(
    "enum_cls, expected",
    [
        (CampaignStatus, {"creating", "active", "paused", "terminal", "archived", "read_only"}),
        (LifeStage, {"childhood", "adolescence", "youth", "adulthood", "late_life", "terminal"}),
        (AttributeId, {"melee", "ranged", "body", "agility", "intellect", "awareness", "willpower", "presence"}),
        (ConfidenceLevel, {"confirmed", "disputed", "perspective_only"}),
        (ReviewStatus, {"candidate", "approved", "rejected", "superseded"}),
        (ErrorCode, {
            "E_CONFIG_INVALID", "E_PROVIDER_UNAVAILABLE", "E_PROVIDER_TIMEOUT",
            "E_PROVIDER_SCHEMA", "E_LORE_UNCOVERED", "E_LORE_CONFLICT",
            "E_CANON_VIOLATION", "E_RULE_INVALID_ACTION", "E_SAVE_CONFLICT",
            "E_SAVE_CORRUPT", "E_CONTENT_MISSING", "E_MIGRATION_FAILED",
        }),
    ],
)
def test_enum_values_frozen(enum_cls, expected) -> None:
    actual = {m.value for m in enum_cls}
    assert expected <= actual


def test_serialized_values_are_stable_strings() -> None:
    assert CampaignStatus.ACTIVE.value == "active"
    assert LifeStage.CHILDHOOD.value == "childhood"
    assert AttributeId.WILLPOWER.value == "willpower"


def test_unknown_enum_value_strictly_rejected() -> None:
    adapter = TypeAdapter(CampaignStatus)
    with pytest.raises(ValidationError):
        adapter.validate_python("exploding")
    with pytest.raises(ValidationError):
        adapter.validate_python("Active")


def test_error_codes_are_unique() -> None:
    values = [m.value for m in ErrorCode]
    assert len(values) == len(set(values))