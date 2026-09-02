"""D-06: claim guard — canon without fact, out-of-scope original, decorative assertions."""

from __future__ import annotations

from noosphere40k.canon_guard.claim_guard import ClaimGuard
from noosphere40k.llm.schemas import (
    LoreClaim,
    NarrationRequest,
    PromptFact,
    VisibleCharacterState,
    VisibleScene,
)


def _request(fact_ids=None, original_ids=None, **overrides) -> NarrationRequest:
    data = {
        "trace_id": "t",
        "campaign_id": "c",
        "turn_number": 1,
        "player_input": "x",
        "visible_scene": VisibleScene(scene_id="s", title="S", location_display="l"),
        "visible_character_state": VisibleCharacterState(
            display_name="Ada", displayed_age="8", life_stage="childhood", role_summary="r"
        ),
        "allowed_lore_facts": [
            PromptFact(fact_id=f, statement="s", viewpoint="editorial", allowed_usage="objective")
            for f in (fact_ids or [])
        ],
        "allowed_original_entity_ids": list(original_ids or []),
    }
    data.update(overrides)
    return NarrationRequest(**data)


def test_canon_claim_without_fact_rejected() -> None:
    guard = ClaimGuard()
    decision = guard.validate(_request(fact_ids=["fact.1"]), [
        LoreClaim(text="帝国存在", claim_type="canon", supporting_fact_ids=[])
    ])
    assert decision.ok is False


def test_canon_claim_with_approved_fact_ok() -> None:
    guard = ClaimGuard()
    decision = guard.validate(_request(fact_ids=["fact.1"]), [
        LoreClaim(text="帝国存在", claim_type="canon", supporting_fact_ids=["fact.1"])
    ])
    assert decision.ok is True


def test_canon_claim_referencing_unallowed_fact_rejected() -> None:
    guard = ClaimGuard()
    decision = guard.validate(_request(fact_ids=["fact.1"]), [
        LoreClaim(text="帝国存在", claim_type="canon", supporting_fact_ids=["fact.2"])
    ])
    assert decision.ok is False


def test_game_original_outside_allowlist_rejected() -> None:
    guard = ClaimGuard()
    decision = guard.validate(_request(original_ids=["game_original.local_01"]), [
        LoreClaim(
            text="本地村庄",
            claim_type="game_original",
            supporting_entity_ids=["game_original.somewhere_else"],
        )
    ])
    assert decision.ok is False


def test_game_original_within_allowlist_ok() -> None:
    guard = ClaimGuard()
    decision = guard.validate(_request(original_ids=["game_original.local_01"]), [
        LoreClaim(
            text="本地村庄",
            claim_type="game_original",
            supporting_entity_ids=["game_original.local_01"],
        )
    ])
    assert decision.ok is True


def test_decorative_with_assertion_rejected() -> None:
    guard = ClaimGuard()
    decision = guard.validate(_request(), [
        LoreClaim(
            text="阿斯塔特军团存在",
            claim_type="decorative",
            supporting_entity_ids=["entity.astartes"],
        )
    ])
    assert decision.ok is False


def test_unknown_claim_type_rejected() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        LoreClaim(text="x", claim_type="weird")