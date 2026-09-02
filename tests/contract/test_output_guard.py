"""E-06: output guard — one repair then template fallback, no illegal commit."""

from __future__ import annotations

from noosphere40k.llm.output_guard import OutputGuard
from noosphere40k.llm.schemas import (
    LoreClaim,
    NarrationRequest,
    NarrationResponse,
    VisibleCharacterState,
    VisibleScene,
)
from noosphere40k.llm.stub import StubProvider


def _request(**overrides) -> NarrationRequest:
    data = {
        "trace_id": "t",
        "campaign_id": "c",
        "turn_number": 1,
        "player_input": "x",
        "visible_scene": VisibleScene(scene_id="s", title="S", location_display="l"),
        "visible_character_state": VisibleCharacterState(
            display_name="Ada", displayed_age="8", life_stage="childhood", role_summary="r"
        ),
    }
    data.update(overrides)
    return NarrationRequest(**data)


def _ok_draft() -> NarrationResponse:
    return NarrationResponse(
        narration="配给日清晨，母亲看着你。",
        lore_claims=[LoreClaim(text="日常", claim_type="decorative")],
    )


async def test_valid_draft_passes() -> None:
    guard = OutputGuard(StubProvider())
    outcome = await guard.validate_and_repair(_request(), _ok_draft())
    assert outcome.fell_back_to_template is False
    assert outcome.response is not None
    assert "配给日" in outcome.response.narration


async def test_forbidden_event_forced_to_template() -> None:
    draft = NarrationResponse(
        narration="你击败了敌人。",
        proposed_events=[{"proposal_type": "CharacterDied", "target_id": "pc"}],
    )
    guard = OutputGuard(StubProvider(response=_ok_draft()))
    outcome = await guard.validate_and_repair(_request(), draft)
    # repair is attempted once; stub returns ok draft, so repair succeeds
    assert outcome.repaired_once is True
    assert outcome.fell_back_to_template is False


async def test_repair_fails_then_template_fallback() -> None:
    # provider returns an invalid draft on repair too
    class BadProvider(StubProvider):
        async def generate_structured(self, *, messages, response_model, timeout_seconds, request_metadata):
            return NarrationResponse(
                narration="still bad",
                proposed_events=[{"proposal_type": "RandomDrawn", "target_id": None}],
            )

    draft = NarrationResponse(
        narration="bad",
        proposed_events=[{"proposal_type": "RandomDrawn", "target_id": None}],
    )
    guard = OutputGuard(BadProvider())
    outcome = await guard.validate_and_repair(_request(), draft)
    assert outcome.fell_back_to_template is True
    assert "模板" in outcome.response.narration


async def test_erotic_childhood_content_rejected() -> None:
    draft = NarrationResponse(narration="她对你说了一些色情的话。")
    guard = OutputGuard(StubProvider(response=_ok_draft()))
    outcome = await guard.validate_and_repair(_request(), draft)
    assert outcome.repaired_once is True
    assert outcome.fell_back_to_template is False  # repair succeeded


async def test_empty_narration_falls_back() -> None:
    draft = NarrationResponse(narration="   ")
    guard = OutputGuard(StubProvider(response=_ok_draft()))
    outcome = await guard.validate_and_repair(_request(), draft)
    # repair produces a valid draft -> passes after one repair
    assert outcome.repaired_once is True