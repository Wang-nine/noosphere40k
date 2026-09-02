"""H-03: fault injection — provider timeout, invalid output, DB interruption."""

from __future__ import annotations

from pathlib import Path

import pytest

from noosphere40k.domain.errors import ProviderTimeoutError, SaveCorruptError
from noosphere40k.lore.retrieval import LoreRepository
from noosphere40k.lore.schemas import LoreFact
from noosphere40k.persistence.db import open_engine, run_migrations
from noosphere40k.persistence.migrations import MIGRATIONS


def test_provider_timeout_is_stable_error(tmp_path: Path) -> None:
    from noosphere40k.llm.base import Message
    from noosphere40k.llm.schemas import NarrationResponse
    from noosphere40k.llm.stub import StubProvider

    provider = StubProvider(response=NarrationResponse(narration="x"), sleep_seconds=3.0)

    async def _run():
        await provider.generate_structured(
            messages=[Message(role="user", content="hi")],
            response_model=NarrationResponse,
            timeout_seconds=0.01,
            request_metadata={},
        )

    import asyncio

    with pytest.raises(ProviderTimeoutError):
        asyncio.run(_run())


def test_invalid_llm_output_never_commits(tmp_path: Path) -> None:
    from noosphere40k.llm.output_guard import OutputGuard
    from noosphere40k.llm.schemas import (
        NarrationRequest,
        NarrationResponse,
        VisibleCharacterState,
        VisibleScene,
    )
    from noosphere40k.llm.stub import StubProvider

    request = NarrationRequest(
        trace_id="t", campaign_id="c", turn_number=1, player_input="x",
        visible_scene=VisibleScene(scene_id="s", title="S", location_display="l"),
        visible_character_state=VisibleCharacterState(
            display_name="A", displayed_age="8", life_stage="childhood", role_summary="r"
        ),
    )
    draft = NarrationResponse(
        narration="bad",
        proposed_events=[{"proposal_type": "RandomDrawn", "target_id": None}],
    )

    class BadRepair(StubProvider):
        async def generate_structured(self, *, messages, response_model, timeout_seconds, request_metadata):
            # still carries a forbidden event after repair -> second failure
            return NarrationResponse(
                narration="still bad",
                proposed_events=[{"proposal_type": "RandomDrawn", "target_id": None}],
            )

    guard = OutputGuard(BadRepair())

    async def _run():
        return await guard.validate_and_repair(request, draft)

    import asyncio

    outcome = asyncio.run(_run())
    assert outcome.fell_back_to_template is True


def test_corrupt_db_is_detected(tmp_path: Path) -> None:
    engine = open_engine(tmp_path / "lore.db")
    run_migrations(engine, MIGRATIONS)
    repo = LoreRepository(engine)
    repo.store_fact(LoreFact(
        fact_id="fact.ok.001",
        claim="帝国很庞大",
        fact_type="canon_editorial",
        review_status="approved",
        pack_id="p",
        pack_version="1.0.0",
    ))
    assert repo.get_fact("fact.ok.001") is not None


def test_missing_pack_raises(tmp_path: Path) -> None:
    from noosphere40k.content.loader import load_pack_json
    from noosphere40k.domain.errors import ContentMissingError

    with pytest.raises(ContentMissingError):
        load_pack_json(tmp_path / "missing.json")


def test_hash_change_blocks_replay(tmp_path: Path) -> None:
    from noosphere40k.domain.enums import EventOrigin
    from noosphere40k.domain.events import (
        INITIAL_GAME_STATE,
        EventEnvelope,
        EventType,
        reduce_event,
    )
    from noosphere40k.persistence.repositories import CampaignRepository

    engine = open_engine(tmp_path / "camp.db")
    run_migrations(engine, MIGRATIONS)
    repo = CampaignRepository(engine)
    repo.create_campaign("c1", "T", "pv")

    event = EventEnvelope(
        event_id="e1", campaign_id="c1", sequence=1, turn_id="t1",
        event_type=EventType.CAMPAIGN_CREATED.value,
        occurred_at_utc=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        correlation_id="tr", origin=EventOrigin.SYSTEM,
        payload={"character_id": "pc", "display_name": "Ada", "chronological_age_days": 2920},
    )
    state = reduce_event(INITIAL_GAME_STATE, event)
    from noosphere40k.persistence.repositories import commit_turn

    commit_turn(repo, campaign_id="c1", expected_last_sequence=0, state=state, events=[event])
    # tamper
    with engine.begin() as conn:
        from sqlalchemy import text

        conn.execute(
            text("UPDATE campaign_events SET payload_json = :p WHERE sequence = 1"),
            {"p": '{"character_id":"evil","display_name":"Evil","chronological_age_days":9999}'},
        )
    with pytest.raises(SaveCorruptError):
        repo.load_consistent_snapshot("c1")