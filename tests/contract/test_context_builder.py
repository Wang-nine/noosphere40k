"""E-05: narrator context builder — only visible state and approved facts."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path

from noosphere40k.domain.enums import EventOrigin
from noosphere40k.domain.events import INITIAL_GAME_STATE, EventEnvelope, EventType, reduce_event
from noosphere40k.llm.context_builder import NarrationContextBuilder
from noosphere40k.lore.retrieval import LoreRepository
from noosphere40k.lore.schemas import LoreFact
from noosphere40k.persistence.db import open_engine, run_migrations
from noosphere40k.persistence.migrations import MIGRATIONS


def _state():
    from datetime import datetime

    event = EventEnvelope(
        event_id="e1",
        campaign_id="camp.1",
        sequence=1,
        turn_id="t1",
        event_type=EventType.CAMPAIGN_CREATED.value,
        occurred_at_utc=datetime.now(UTC),
        correlation_id="c",
        origin=EventOrigin.SYSTEM,
        payload={
            "character_id": "pc",
            "display_name": "Ada",
            "chronological_age_days": 2920,
            "status": "active",
            "attributes": {"awareness": 35},
        },
    )
    return reduce_event(INITIAL_GAME_STATE, event)


def test_context_only_includes_allowed_approved_facts(tmp_path: Path) -> None:
    engine = open_engine(tmp_path / "lore.db")
    run_migrations(engine, MIGRATIONS)
    lore = LoreRepository(engine)
    lore.store_fact(LoreFact(
        fact_id="fact.ok.001",
        claim="帝国很庞大",
        fact_type="canon_editorial",
        review_status="approved",
        pack_id="p",
        pack_version="1.0.0",
    ))
    lore.store_fact(LoreFact(
        fact_id="fact.candidate.001",
        claim="未经批准的内容",
        fact_type="canon_editorial",
        review_status="candidate",
        pack_id="p",
        pack_version="1.0.0",
    ))

    builder = NarrationContextBuilder(lore)
    request = builder.build(
        state=_state(),
        player_input="观察",
        trace_id="trace-1",
        turn_number=1,
        scene_id="s1",
        scene_title="配给日",
        location_display="工人居住层",
        allowed_fact_ids=["fact.ok.001"],
        allowed_original_entity_ids=[],
    )
    assert [f.fact_id for f in request.allowed_lore_facts] == ["fact.ok.001"]
    assert "未经批准" not in " ".join(f.statement for f in request.allowed_lore_facts)


def test_candidate_fact_never_leaks_even_if_requested(tmp_path: Path) -> None:
    engine = open_engine(tmp_path / "lore.db")
    run_migrations(engine, MIGRATIONS)
    lore = LoreRepository(engine)
    lore.store_fact(LoreFact(
        fact_id="fact.candidate.001",
        claim="候选",
        fact_type="canon_editorial",
        review_status="candidate",
        pack_id="p",
        pack_version="1.0.0",
    ))
    builder = NarrationContextBuilder(lore)
    request = builder.build(
        state=_state(),
        player_input="x",
        trace_id="t",
        turn_number=1,
        scene_id="s",
        scene_title="S",
        location_display="l",
        allowed_fact_ids=["fact.candidate.001"],  # lore gate would block; defensive
        allowed_original_entity_ids=[],
    )
    assert request.allowed_lore_facts == []


def test_character_state_and_relationships_included(tmp_path: Path) -> None:
    engine = open_engine(tmp_path / "lore.db")
    run_migrations(engine, MIGRATIONS)
    lore = LoreRepository(engine)
    builder = NarrationContextBuilder(lore, narration_length="literary")
    request = builder.build(
        state=_state(),
        player_input="x",
        trace_id="t",
        turn_number=1,
        scene_id="s",
        scene_title="S",
        location_display="l",
        allowed_fact_ids=[],
        allowed_original_entity_ids=[],
    )
    assert request.visible_character_state.display_name == "Ada"
    assert request.visible_character_state.life_stage == "childhood"
    assert request.style_settings.length == "literary"