"""Life chronicle and recap generation from committed events (B-08, E-07).

Only summarizes already-committed events. Never invents people, causes or
endings. Death always ends the campaign in TERMINAL and a consistent
timeline can be generated from the event log.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from noosphere40k.domain.events import EventEnvelope
from noosphere40k.domain.models import GameState

ORDER = {
    "CampaignCreated": 0,
    "VocationStarted": 1,
    "SkillProgressed": 2,
    "TimeAdvanced": 3,
    "LifeStageChanged": 4,
    "WoundApplied": 5,
    "CharacterDied": 6,
    "CampaignTerminated": 7,
    "GoalAdded": 8,
    "GoalUpdated": 9,
}


@dataclass
class ChronicleEntry:
    sequence: int
    event_type: str
    summary: str
    world_time: str = ""


@dataclass
class Chronicle:
    campaign_id: str
    entries: list[ChronicleEntry] = field(default_factory=list)
    ended: bool = False
    death_reason: str | None = None

    def to_lines(self) -> list[str]:
        lines = [f"一生纪事：{self.campaign_id}"]
        for entry in self.entries:
            prefix = f"[{entry.world_time}]" if entry.world_time else f"#{entry.sequence}"
            lines.append(f"  {prefix} {entry.summary}")
        if self.ended and self.death_reason:
            lines.append(f"  终局：{self.death_reason}")
        return lines


def build_chronicle(
    campaign_id: str,
    events: list[EventEnvelope],
    state: GameState,
) -> Chronicle:
    """Generate a consistent timeline from committed events (E-07 rule).
    No new facts are introduced beyond what the events already state."""
    entries: list[ChronicleEntry] = []
    death_reason: str | None = None

    for event in sorted(events, key=lambda e: e.sequence):
        summary = _summarize(event)
        if summary is None:
            continue
        world_time = ""
        if event.world_time:
            world_time = f"{event.world_time.local_year}" if event.world_time.local_year else ""
        entries.append(
            ChronicleEntry(
                sequence=event.sequence,
                event_type=event.event_type,
                summary=summary,
                world_time=world_time,
            )
        )
        if event.event_type == "CharacterDied":
            death_reason = str(event.payload.get("reason", "死亡"))

    return Chronicle(
        campaign_id=campaign_id,
        entries=entries,
        ended=state.status == "terminal",
        death_reason=death_reason,
    )


def _summarize(event: EventEnvelope) -> str | None:
    payload = event.payload
    if event.event_type == "CampaignCreated":
        name = payload.get("display_name", "角色")
        return f"诞生：{name}"
    if event.event_type == "LifeStageChanged":
        return f"进入阶段：{payload.get('life_stage')}"
    if event.event_type == "TimeAdvanced":
        days = payload.get("days", 0)
        return f"时间推进 {days} 天"
    if event.event_type == "VocationStarted":
        return f"开始职业：{payload.get('vocation_id')}"
    if event.event_type == "VocationEnded":
        return f"结束职业：{payload.get('vocation_id')}"
    if event.event_type == "SkillProgressed":
        return f"技能进步：{payload.get('skill_id')} +{payload.get('progress', 0)}"
    if event.event_type == "AttributeChanged":
        return f"属性变化：{payload.get('attribute_id')} = {payload.get('value')}"
    if event.event_type == "WoundApplied":
        return f"受伤：{payload.get('location')}（{payload.get('severity')}）"
    if event.event_type == "ConditionApplied":
        return f"状态：{payload.get('condition_id')}"
    if event.event_type == "GoalAdded":
        return f"新目标：{payload.get('description')}"
    if event.event_type == "GoalCompleted":
        return f"目标完成：{payload.get('goal_id')}"
    if event.event_type == "CharacterDied":
        return f"死亡：{payload.get('reason', '原因未记录')}"
    if event.event_type == "CampaignTerminated":
        return "战役终结"
    return None


def generate_recap(events: list[EventEnvelope], *, limit: int = 8) -> str:
    """E-07 offline recap: a compact summary of the most recent events only.
    Never adds context the events do not contain."""
    raw_entries = [_summarize(e) for e in sorted(events, key=lambda e: e.sequence)]
    entries: list[str] = [e for e in raw_entries if e is not None]
    if not entries:
        return "还没有已提交的事件。"
    recent = entries[-limit:]
    return "；".join(recent)


__all__ = ["build_chronicle", "generate_recap", "Chronicle", "ChronicleEntry"]