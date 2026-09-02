"""Offline tutorial campaign service (F-02/G-02).

Provides a fully deterministic, no-LLM playable flow for the tutorial pack:
create a campaign -> play scenes by choosing numbered actions or free text ->
rule checks resolve via d100 -> events are appended atomically.
Narration always uses validated templates (no LLM, no fabricated lore).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from noosphere40k.content.loader import load_pack_json
from noosphere40k.content.schemas import ActionTemplate, SceneDefinition, ScenePack
from noosphere40k.domain.enums import EventOrigin
from noosphere40k.domain.errors import RuleInvalidActionError, UnknownEventError
from noosphere40k.domain.events import (
    INITIAL_GAME_STATE,
    EventEnvelope,
    EventType,
    GameState,
    compute_state_hash,
    reduce_event,
)
from noosphere40k.persistence.repositories import (
    CampaignRepository,
    commit_turn,
)
from noosphere40k.rules.checks import CheckRequest, resolve_attribute_check
from noosphere40k.rules.rng import RngService

PROMPT_VERSION = "offline-tutorial-0.1.0"
TUTORIAL_PACK_PATH = (
    Path(__file__).resolve().parents[3] / "content" / "scenario_packs" / "tutorial_hive_worker" / "pack.json"
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class Playback:
    narration: str = ""
    scene: SceneDefinition | None = None
    actions: list[ActionTemplate] = field(default_factory=list)
    check_detail: str | None = None
    next_scene_id: str | None = None
    ended: bool = False
    messages: list[str] = field(default_factory=list)


class TutorialService:
    """Deterministic offline flow over the tutorial pack."""

    def __init__(
        self,
        repo: CampaignRepository,
        *,
        pack: ScenePack | None = None,
        rng: RngService | None = None,
    ) -> None:
        self.repo = repo
        self.pack = pack or load_pack_json(TUTORIAL_PACK_PATH)
        self.rng = rng or RngService(seed=42)
        self._scenes = {s.scene_id: s for s in self.pack.scenes}
        from noosphere40k.lore.retrieval import LoreRepository

        self.lore = LoreRepository(repo.engine)

    # ---- creation ----

    def create_campaign(self, campaign_id: str, name: str, *, display_name: str) -> GameState:
        repo = self.repo
        repo.create_campaign(campaign_id, name, PROMPT_VERSION)
        seed_events: list[EventEnvelope] = []
        self.rng = RngService(seed=42)

        created = self._new_event(
            campaign_id, 1, EventType.CAMPAIGN_CREATED, origin=EventOrigin.SYSTEM,
            payload={
                "character_id": "character.pc.tutorial",
                "display_name": display_name,
                "chronological_age_days": 2920,
                "status": "active",
                "life_stage": "childhood",
                "era_id": "era_indomitus_bounded",
                "origin_id": "origin.hive_worker_household",
                "attributes": {
                    "melee": 25, "ranged": 25, "body": 30, "agility": 30,
                    "intellect": 30, "awareness": 35, "willpower": 30, "presence": 25,
                },
            },
        )
        seed_events.append(created)
        scene_start = self._new_event(
            campaign_id, 2, EventType.SCENE_STARTED, origin=EventOrigin.CONTENT,
            payload={"scene_id": "scene.tutorial.ration_morning"},
        )
        seed_events.append(scene_start)

        state = INITIAL_GAME_STATE.model_copy()
        state = self._apply_events(state, seed_events)
        state = state.model_copy(update={"status": "active"})
        state = state.model_copy(update={"state_hash": compute_state_hash(state)})

        commit_turn(
            repo,
            campaign_id=campaign_id,
            expected_last_sequence=0,
            state=state,
            events=seed_events,
        )
        repo.mark_status(campaign_id, "active")
        return state

    # ---- play ----

    def play_scene(
        self,
        *,
        campaign_id: str,
        state: GameState,
        scene: SceneDefinition,
        choice: str | int,
    ) -> Playback:
        """Handle one action: choice index (1-based) or free text."""
        if state.character is None:
            raise RuleInvalidActionError("campaign has no player character yet")

        if isinstance(choice, int):
            action = self._action_by_index(scene, choice)
        else:
            action = self._match_free_text(scene, choice)

        events: list[EventEnvelope] = []
        base = state.sequence + 1

        intent_evt = self._new_event(
            campaign_id, base, EventType.ACTION_INTENT_RESOLVED, origin=EventOrigin.PLAYER,
            payload={"action_template_id": action.action_template_id, "scene_id": scene.scene_id},
        )
        events.append(intent_evt)
        base += 1

        check_detail: str | None = None
        if action.check_template_id is not None:
            check_detail, check_evt, drawn_evt = self._resolve_check(
                campaign_id, base, state, scene, action
            )
            events.append(drawn_evt)
            events.append(check_evt)
            base += 2

        # advance to next scene or end
        next_scene_id = self._next_scene_id(scene)
        if next_scene_id is not None:
            events.append(
                self._new_event(
                    campaign_id, base, EventType.SCENE_COMPLETED, origin=EventOrigin.CONTENT,
                    payload={"scene_id": scene.scene_id, "next_scene_id": next_scene_id},
                )
            )
            base += 1
            events.append(
                self._new_event(
                    campaign_id, base, EventType.SCENE_STARTED, origin=EventOrigin.CONTENT,
                    payload={"scene_id": next_scene_id},
                )
            )
        else:
            events.append(
                self._new_event(
                    campaign_id, base, EventType.SCENE_COMPLETED, origin=EventOrigin.CONTENT,
                    payload={"scene_id": scene.scene_id},
                )
            )

        expected_before = state.sequence
        state = self._apply_events(state, events)
        state = state.model_copy(update={"state_hash": compute_state_hash(state)})
        commit_turn(
            self.repo,
            campaign_id=campaign_id,
            expected_last_sequence=expected_before,
            state=state,
            events=events,
        )

        narration = self._template_text(scene, state)
        playback = Playback(
            narration=narration,
            check_detail=check_detail,
            next_scene_id=next_scene_id,
        )
        if next_scene_id is not None:
            next_scene = self._scenes[next_scene_id]
            playback.scene = next_scene
            playback.actions = next_scene.action_templates
        else:
            playback.ended = True
            playback.actions = []
        return playback

    # ---- helpers ----

    def _action_by_index(self, scene: SceneDefinition, index: int) -> ActionTemplate:
        if not 1 <= index <= len(scene.action_templates):
            raise RuleInvalidActionError(
                f"choice index {index} out of range 1..{len(scene.action_templates)}",
                context={"scene_id": scene.scene_id},
            )
        return scene.action_templates[index - 1]

    def _match_free_text(self, scene: SceneDefinition, text: str) -> ActionTemplate:
        """Minimal offline intent matching: keyword -> action template.

        Without an LLM we only map clearly-correlated keywords; anything else
        falls back to the first action with a 'safe' tag.
        """
        lowered = text.strip().lower()
        for action in scene.action_templates:
            tokens = action.action_template_id.lower()
            if any(k in lowered for k in self._keywords(action)):
                return action
            if tokens in lowered:
                return action
        fallback = next(
            (a for a in scene.action_templates if "safe" in a.content_tags),
            scene.action_templates[0],
        )
        return fallback

    @staticmethod
    def _keywords(action: ActionTemplate) -> list[str]:
        mapping = {
            "look": ["看", "观察", "look", "stare"],
            "ask": ["问", "ask", "询问", "问谁"],
            "split": ["分", "split"],
            "save": ["留", "save", "省"],
        }
        for prefix, keywords in mapping.items():
            if action.action_template_id.endswith(prefix):
                return keywords
        return []

    def _resolve_check(
        self,
        campaign_id: str,
        base_seq: int,
        state: GameState,
        scene: SceneDefinition,
        action: ActionTemplate,
    ) -> tuple[str, EventEnvelope, EventEnvelope]:
        assert state.character is not None
        check_id = str(action.check_template_id)
        attribute_id = "awareness"
        request = CheckRequest(
            check_id=check_id,
            actor_id=state.character.character_id,
            attribute_id=attribute_id,
            risk="standard",
        )
        roll = self.rng.draw_d100()
        rng_event = self._new_event(
            campaign_id, base_seq, EventType.RANDOM_DRAWN, origin=EventOrigin.RULES,
            payload={"d100": roll, "check_id": check_id},
        )
        result = resolve_attribute_check(
            request,
            roll,
            attributes=state.character.attributes,
            skills=state.character.skills,
            rng_event_id=rng_event.event_id,
        )
        check_event = self._new_event(
            campaign_id, base_seq + 1, EventType.CHECK_RESOLVED, origin=EventOrigin.RULES,
            payload={
                "check_id": check_id,
                "roll": result.roll,
                "target": result.target,
                "success": result.success,
                "margin_degrees": result.margin_degrees,
                "special": result.special,
            },
        )
        detail = (
            f"d100={result.roll} 目标={result.target} "
            f"{'成功' if result.success else '失败'}（幅度 {result.margin_degrees}）"
        )
        return detail, check_event, rng_event

    def _next_scene_id(self, scene: SceneDefinition) -> str | None:
        rules = sorted(scene.next_scene_rules, key=lambda r: r.priority)
        for rule in rules:
            if rule.next_scene_id is not None:
                return rule.next_scene_id
        return None

    def _template_text(self, scene: SceneDefinition, state: GameState) -> str:
        template = next(
            (t for t in self.pack.templates if t.template_id == scene.fallback_narration_template_id),
            None,
        )
        if template is None:
            raise UnknownEventError(
                f"missing fallback template for scene {scene.scene_id}"
            )
        text = template.text
        if "display_name" in template.variables and state.character is not None:
            text = text.replace("{display_name}", state.character.display_name)
        for variable in template.variables:
            text = text.replace("{" + variable + "}", "")
        return text

    def _new_event(
        self,
        campaign_id: str,
        sequence: int,
        event_type: EventType,
        *,
        origin: EventOrigin,
        payload: dict[str, object] | None = None,
    ) -> EventEnvelope:
        return EventEnvelope(
            event_id=f"evt-{uuid.uuid4().hex[:10]}",
            campaign_id=campaign_id,
            sequence=sequence,
            turn_id=f"turn-{campaign_id}-{sequence}",
            event_type=event_type.value,
            occurred_at_utc=_utcnow(),
            correlation_id=f"trace-{campaign_id}",
            origin=origin,
            payload=payload or {},
        )

    def _apply_events(self, state: GameState, events: list[EventEnvelope]) -> GameState:
        """Apply events in order, stamping prior/resulting hashes for audit."""
        for index, event in enumerate(events):
            stamped = event.model_copy(update={"prior_state_hash": state.state_hash})
            state = reduce_event(state, stamped)
            stamped = stamped.model_copy(update={"resulting_state_hash": state.state_hash})
            events[index] = stamped
        return state

    # ---- life transitions (B-04, G-06) ----

    def time_jump(
        self,
        *,
        campaign_id: str,
        state: GameState,
        days: int,
        focus_tags: list[str] | None = None,
        to_stage: str | None = None,
        confirm: bool = True,
    ) -> Playback:
        """Preview then (if confirmed) settle a time jump / life transition.

        If ``confirm`` is False only a preview is returned and NO events are
        committed (G-06: cancelling produces zero events).
        """
        from noosphere40k.rules.aging import (
            LifeTransitionProposal,
            LifeTransitionService,
            days_to_years,
            stage_for_age,
        )

        character = state.character
        if character is None:
            raise RuleInvalidActionError("campaign has no player character yet")

        current_stage = character.life_stage
        target_stage = to_stage or stage_for_age(days_to_years(character.chronological_age_days + days))
        if target_stage == current_stage:
            target_stage = _next_stage(current_stage)

        proposal = LifeTransitionProposal(
            transition_id=f"tran-{campaign_id}-{state.sequence + 1}",
            from_stage=current_stage,
            to_stage=target_stage,
            time_span_days=days,
            focus_tags=focus_tags or ["labor"],
        )
        service = LifeTransitionService(rng=self.rng)
        preview = service.preview(proposal, character)

        if not confirm:
            playback = Playback(
                narration="【时间跳跃预览】\n" + "\n".join(preview.to_display()),
                actions=[],
            )
            playback.messages.extend(preview.irreversible_notes)
            return playback

        settled = service.settle(proposal, character)
        events: list[EventEnvelope] = []
        base = state.sequence + 1

        events.append(
            self._new_event(
                campaign_id, base, EventType.TIME_ADVANCED, origin=EventOrigin.RULES,
                payload={"days": days, "to_stage": target_stage},
            )
        )
        base += 1
        deltas = settled["attribute_deltas"]
        assert isinstance(deltas, dict)
        for attr, delta in deltas.items():
            if delta == 0:
                continue
            assert state.character is not None
            new_value = state.character.attributes.get(attr, 25) + delta
            events.append(
                self._new_event(
                    campaign_id, base, EventType.ATTRIBUTE_CHANGED, origin=EventOrigin.RULES,
                    payload={"attribute_id": attr, "value": new_value},
                )
            )
            base += 1
        skill_progress = settled["skill_progress"]
        assert isinstance(skill_progress, dict)
        for skill_id, progress in skill_progress.items():
            events.append(
                self._new_event(
                    campaign_id, base, EventType.SKILL_PROGRESSED, origin=EventOrigin.RULES,
                    payload={"skill_id": skill_id, "progress": progress,
                             "learned_from_event_id": proposal.transition_id},
                )
            )
            base += 1
        new_stage = str(settled["new_stage"])
        if new_stage != character.life_stage:
            events.append(
                self._new_event(
                    campaign_id, base, EventType.LIFE_STAGE_CHANGED, origin=EventOrigin.RULES,
                    payload={"life_stage": new_stage},
                )
            )
            base += 1

        expected_before = state.sequence
        state = self._apply_events(state, events)
        commit_turn(
            self.repo,
            campaign_id=campaign_id,
            expected_last_sequence=expected_before,
            state=state,
            events=events,
        )
        narration = f"时间推进 {days} 天，进入阶段 {new_stage}。" if new_stage != current_stage else f"时间推进 {days} 天。"
        return Playback(
            narration=narration,
            actions=[],
            messages=["\n".join(preview.to_display())],
        )


def _next_stage(current: str) -> str:
    from noosphere40k.rules.aging import STAGE_AGE_RANGES

    order = list(STAGE_AGE_RANGES.keys())
    idx = order.index(current) if current in order else 0
    if idx + 1 < len(order):
        return order[idx + 1]
    return current


__all__ = ["TutorialService", "Playback", "PROMPT_VERSION"]