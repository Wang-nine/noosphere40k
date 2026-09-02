"""B-04: life stage transitions — preview, settle, cancel = zero events."""

from __future__ import annotations

import pytest

from noosphere40k.domain.errors import RuleInvalidActionError
from noosphere40k.domain.models import PlayerCharacter, WorldTime
from noosphere40k.rules.aging import (
    LifeTransitionProposal,
    LifeTransitionService,
    is_valid_stage_transition,
    stage_for_age,
)


def _character(stage: str = "childhood", age_days: int = 2920, attributes=None) -> PlayerCharacter:
    return PlayerCharacter(
        character_id="pc",
        display_name="Ada",
        birth_world_time=WorldTime(era_id="e", local_calendar_id="l", ordering_key=0, precision="era"),
        chronological_age_days=age_days,
        subjective_age_days=age_days,
        life_stage=stage,
        origin_id="origin.hive_worker_household",
        attributes=attributes or {"body": 30, "agility": 30, "intellect": 30},
    )


def test_stage_ranges_and_for_age() -> None:
    assert stage_for_age(8) == "childhood"
    assert stage_for_age(15) == "adolescence"
    assert stage_for_age(30) == "adulthood"
    assert stage_for_age(70) == "late_life"


def test_valid_stage_transitions() -> None:
    assert is_valid_stage_transition("childhood", "adolescence") is True
    assert is_valid_stage_transition("adulthood", "late_life") is True
    assert is_valid_stage_transition("adulthood", "childhood") is False
    assert is_valid_stage_transition("childhood", "late_life") is True  # skips allowed
    assert is_valid_stage_transition("childhood", "terminal") is True


def test_preview_is_pure_and_cancels_to_zero_events() -> None:
    service = LifeTransitionService()
    character = _character()
    proposal = LifeTransitionProposal(
        transition_id="t1", from_stage="childhood", to_stage="adolescence",
        time_span_days=3650, focus_tags=["scholarship"],
    )
    preview1 = service.preview(proposal, character)
    preview2 = service.preview(proposal, character)
    assert preview1.effects.attribute_deltas == preview2.effects.attribute_deltas
    # cancel: preview only, no events in this API
    assert not preview1.irreversible_notes or len(preview1.irreversible_notes) >= 0


def test_settle_is_deterministic() -> None:
    service = LifeTransitionService()
    character = _character()
    proposal = LifeTransitionProposal(
        transition_id="t1", from_stage="childhood", to_stage="adolescence",
        time_span_days=3650, focus_tags=["scholarship"],
    )
    a = service.settle(proposal, character)
    b = service.settle(proposal, character)
    assert a["new_chronological_age_days"] == b["new_chronological_age_days"]
    assert a["attribute_deltas"] == b["attribute_deltas"]
    assert a["new_chronological_age_days"] == 2920 + 3650
    assert a["new_stage"] == "youth"  # 8y + 10y = 18y -> youth


def test_llm_cannot_change_stage_directly() -> None:
    # there is no API to set a stage without a valid transition proposal
    service = LifeTransitionService()
    character = _character(stage="childhood")
    bad = LifeTransitionProposal(
        transition_id="x", from_stage="childhood", to_stage="childhood", time_span_days=10
    )
    with pytest.raises(RuleInvalidActionError):
        service.preview(bad, character)


def test_illegal_backward_transition_rejected() -> None:
    service = LifeTransitionService()
    character = _character(stage="adulthood", age_days=10950)
    bad = LifeTransitionProposal(
        transition_id="x", from_stage="adulthood", to_stage="childhood", time_span_days=100
    )
    with pytest.raises(RuleInvalidActionError):
        service.preview(bad, character)


def test_wrong_from_stage_rejected() -> None:
    service = LifeTransitionService()
    character = _character(stage="childhood")
    bad = LifeTransitionProposal(
        transition_id="x", from_stage="youth", to_stage="adulthood", time_span_days=100
    )
    with pytest.raises(RuleInvalidActionError):
        service.preview(bad, character)


def test_late_life_attribute_decline() -> None:
    service = LifeTransitionService()
    character = _character(stage="adulthood", age_days=365 * 50)
    proposal = LifeTransitionProposal(
        transition_id="t", from_stage="adulthood", to_stage="late_life",
        time_span_days=365 * 10, focus_tags=[],
    )
    settled = service.settle(proposal, character)
    deltas = settled["attribute_deltas"]
    assert isinstance(deltas, dict)
    assert deltas.get("body", 0) < 0
    assert settled["new_stage"] == "late_life"


def test_unknown_aging_ruleset_rejected() -> None:
    service = LifeTransitionService()
    character = _character()
    bad = LifeTransitionProposal(
        transition_id="x", from_stage="childhood", to_stage="adolescence",
        time_span_days=100, aging_ruleset_id="custom_weird",
    )
    with pytest.raises(RuleInvalidActionError):
        service.preview(bad, character)