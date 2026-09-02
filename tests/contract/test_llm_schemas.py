"""E-03: LLM protocol schema contract tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from noosphere40k.llm.schemas import (
    ActionIntent,
    LoreClaim,
    NarrationRequest,
    NarrationResponse,
    PromptFact,
    VisibleCharacterState,
    VisibleScene,
)


def _request(**overrides) -> NarrationRequest:
    data = {
        "trace_id": "t1",
        "campaign_id": "camp.1",
        "turn_number": 3,
        "player_input": "我观察",
        "visible_scene": VisibleScene(
            scene_id="s1", title="S", location_display="loc", visible_character_ids=[]
        ),
        "visible_character_state": VisibleCharacterState(
            display_name="Ada", displayed_age="8岁", life_stage="childhood", role_summary="worker"
        ),
    }
    data.update(overrides)
    return NarrationRequest(**data)


def test_request_minimum_valid() -> None:
    request = _request()
    assert request.turn_number == 3
    assert request.style_settings.length == "standard"


def test_request_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        NarrationRequest.model_validate(_request().model_dump() | {"extra": 1})


def test_request_rejects_unknown_action_type() -> None:
    with pytest.raises(ValidationError):
        _request(action_intent=ActionIntent(
            intent_id="i", actor_id="a", action_type="frobnicate",
            free_text_summary="x",
        ))


def test_request_rejects_unknown_claim_type() -> None:
    with pytest.raises(ValidationError):
        LoreClaim(text="x", claim_type="whatever")


def test_prompt_fact_fields() -> None:
    fact = PromptFact(
        fact_id="fact.1", statement="帝国很庞大", viewpoint="editorial",
        allowed_usage="objective", source_ref_ids=["src.1"],
    )
    assert fact.allowed_usage == "objective"


def test_response_strict_unknown_field() -> None:
    with pytest.raises(ValidationError):
        NarrationResponse.model_validate(
            {"narration": "x", "made_up_field": True}
        )


def test_response_missing_narration_rejected() -> None:
    with pytest.raises(ValidationError):
        NarrationResponse.model_validate({})


def test_response_unknown_event_proposal_typed_as_string() -> None:
    resp = NarrationResponse(
        narration="ok",
        proposed_events=[{"proposal_type": "CharacterDied", "target_id": None}],
    )
    # proposal_type is a free string at the schema level; the whitelist guard
    # is responsible for rejecting forbidden types.
    assert resp.proposed_events[0].proposal_type == "CharacterDied"