"""Simplified deterministic combat (TECHNICAL_SPEC §7.4; B-07).

- action economy: move, major action, reaction, free actions.
- to-hit by ranged/melee attribute check.
- damage, armor, penetration, cover resolved by the engine.
- retreat, surrender, suppression and negotiation are legal, non-lethal options.
- death only arises from the rules (never from LLM narration).
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field

from noosphere40k.domain.models import StrictModel
from noosphere40k.rules.checks import CheckRequest, Modifier, resolve_check
from noosphere40k.rules.rng import RngService


class Combatant(StrictModel):
    actor_id: str
    display_name: str = ""
    melee: int = 30
    ranged: int = 30
    body: int = 30
    agility: int = 30
    willpower: int = 30
    armor: int = 0
    wounds_severity_max: str = "minor"


class Weapon(StrictModel):
    weapon_id: str
    attack_attribute: str = "ranged"
    damage: int = 4
    penetration: int = 0
    range_bands: list[str] = Field(default_factory=list)


class AttackRequest(StrictModel):
    attack_id: str
    attacker_id: str
    defender_id: str
    weapon: Weapon
    cover: int = 0
    risk: str = "high"


@dataclass
class AttackResult:
    attack_id: str
    hit: bool
    damage_dealt: int
    armor_blocked: int
    target_wound_severity: str
    defender_dead: bool
    roll: int
    target: int
    detail: str


class CombatEngine:
    def __init__(self, rng: RngService | None = None) -> None:
        self.rng = rng or RngService(seed=42)

    def resolve_attack(
        self,
        request: AttackRequest,
        attacker: Combatant,
        defender: Combatant,
    ) -> AttackResult:
        attribute_id = request.weapon.attack_attribute
        attribute_value = getattr(attacker, attribute_id, attacker.ranged)
        modifiers = []
        if request.cover > 0:
            modifiers.append(Modifier(
                modifier_id=f"cover-{request.attack_id}",
                value=-request.cover,
                source_type="scene",
                source_id="cover",
                display_reason="掩体",
            ))
        check = CheckRequest(
            check_id=request.attack_id,
            actor_id=attacker.actor_id,
            attribute_id=attribute_id,
            risk=request.risk,
            situation_modifiers=modifiers,
        )
        roll = self.rng.draw_d100()
        result = resolve_check(check, roll, attribute_value=attribute_value, rank=None)

        if not result.success:
            return AttackResult(
                attack_id=request.attack_id,
                hit=False,
                damage_dealt=0,
                armor_blocked=0,
                target_wound_severity="none",
                defender_dead=False,
                roll=roll,
                target=result.target,
                detail=f"未命中（d100={roll} 目标={result.target}）",
            )

        raw_damage = request.weapon.damage + (result.margin_degrees - 1)
        penetration = request.weapon.penetration
        armor_effective = max(0, defender.armor - penetration)
        armor_blocked = min(raw_damage, armor_effective)
        damage_dealt = raw_damage - armor_blocked

        severity = self._severity_for_damage(damage_dealt, defender)
        dead = severity == "terminal"
        detail = (
            f"命中 d100={roll} 目标={result.target}，"
            f"伤害 {raw_damage}，护甲抵消 {armor_blocked}，伤势 {severity}"
        )
        return AttackResult(
            attack_id=request.attack_id,
            hit=True,
            damage_dealt=damage_dealt,
            armor_blocked=armor_blocked,
            target_wound_severity=severity,
            defender_dead=dead,
            roll=roll,
            target=result.target,
            detail=detail,
        )

    @staticmethod
    def _severity_for_damage(damage: int, defender: Combatant) -> str:
        body = defender.body
        if damage >= body + 20:
            return "terminal"
        if damage >= body + 10:
            return "critical"
        if damage >= body:
            return "major"
        if damage >= max(5, body // 2):
            return "minor"
        return "none"

    # ---- non-lethal / tactical options ----

    def resolve_retreat(self, attacker: Combatant, defender: Combatant) -> bool:
        """Escape check: agility roll vs fixed threshold."""
        check = CheckRequest(
            check_id=f"retreat-{defender.actor_id}",
            actor_id=defender.actor_id,
            attribute_id="agility",
            risk="high",
        )
        roll = self.rng.draw_d100()
        result = resolve_check(check, roll, attribute_value=defender.agility, rank=None)
        return result.success

    def resolve_suppression(self, attacker: Combatant, defender: Combatant) -> bool:
        """Suppression pins the defender unless they pass a willpower roll."""
        check = CheckRequest(
            check_id=f"suppress-{defender.actor_id}",
            actor_id=defender.actor_id,
            attribute_id="willpower",
            risk="standard",
        )
        roll = self.rng.draw_d100()
        result = resolve_check(
            check,
            roll,
            attribute_value=getattr(defender, "willpower", 30),
            rank=None,
        )
        return result.success  # passed -> not suppressed


__all__ = ["CombatEngine", "Combatant", "Weapon", "AttackRequest", "AttackResult"]