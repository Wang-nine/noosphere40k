"""C-05+: campaign deletion — atomic, cross-table, idempotent."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path

import pytest
from sqlalchemy import text

from noosphere40k.domain.enums import EventOrigin
from noosphere40k.domain.events import (
    INITIAL_GAME_STATE,
    EventEnvelope,
    EventType,
    reduce_event,
)
from noosphere40k.persistence.db import open_engine, run_migrations
from noosphere40k.persistence.migrations import MIGRATIONS
from noosphere40k.persistence.repositories import CampaignRepository, commit_turn


def _created(campaign_id: str, seq: int = 1) -> EventEnvelope:
    from datetime import datetime

    return EventEnvelope(
        event_id=f"e{seq}",
        campaign_id=campaign_id,
        sequence=seq,
        turn_id=f"t{seq}",
        event_type=EventType.CAMPAIGN_CREATED.value,
        occurred_at_utc=datetime.now(UTC),
        correlation_id="tr",
        origin=EventOrigin.SYSTEM,
        payload={
            "character_id": "pc",
            "display_name": "Ada",
            "chronological_age_days": 2920,
        },
    )


@pytest.fixture
def repo(tmp_path: Path) -> CampaignRepository:
    engine = open_engine(tmp_path / "test.db")
    run_migrations(engine, MIGRATIONS)
    repository = CampaignRepository(engine)
    repository.create_campaign("camp.a", "A", "pv")
    repository.create_campaign("camp.b", "B", "pv")
    # seed an event + snapshot for camp.a
    state = reduce_event(INITIAL_GAME_STATE, _created("camp.a"))
    commit_turn(repository, campaign_id="camp.a", expected_last_sequence=0, state=state,
                events=[_created("camp.a")])
    repository.save_snapshot("camp.a", state)
    return repository


def test_delete_campaign_removes_all_rows(repo: CampaignRepository) -> None:
    assert repo.delete_campaign("camp.a") is True
    with repo.engine.connect() as conn:
        events = conn.execute(text(
            "SELECT COUNT(*) FROM campaign_events WHERE campaign_id='camp.a'"
        )).scalar()
        snaps = conn.execute(text(
            "SELECT COUNT(*) FROM campaign_snapshots WHERE campaign_id='camp.a'"
        )).scalar()
        chars = conn.execute(text(
            "SELECT COUNT(*) FROM characters WHERE campaign_id='camp.a'"
        )).scalar()
        camps = conn.execute(text(
            "SELECT COUNT(*) FROM campaigns WHERE campaign_id='camp.a'"
        )).scalar()
    assert events == 0
    assert snaps == 0
    assert chars == 0
    assert camps == 0


def test_delete_other_campaign_untouched(repo: CampaignRepository) -> None:
    repo.delete_campaign("camp.a")
    with repo.engine.connect() as conn:
        count = conn.execute(text(
            "SELECT COUNT(*) FROM campaigns WHERE campaign_id='camp.b'"
        )).scalar()
    assert count == 1


def test_delete_missing_campaign_returns_false(repo: CampaignRepository) -> None:
    assert repo.delete_campaign("camp.nope") is False
    # nothing deleted, others intact
    with repo.engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM campaigns")).scalar()
    assert count == 2