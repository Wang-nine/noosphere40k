"""B-07: simplified combat."""

from __future__ import annotations

from noosphere40k.rules.combat import (
    AttackRequest,
    Combatant,
    CombatEngine,
    Weapon,
)
from noosphere40k.rules.rng import RngService


def _engine(rolls) -> CombatEngine:
    return CombatEngine(rng=RngService(sequence=rolls))


def test_hit_deals_damage_with_armor() -> None:
    engine = _engine([30])  # hit vs ranged 30 target (30<=30)
    attacker = Combatant(actor_id="a", ranged=30)
    defender = Combatant(actor_id="d", body=30, armor=2)
    result = engine.resolve_attack(
        AttackRequest(
            attack_id="atk1", attacker_id="a", defender_id="d",
            weapon=Weapon(weapon_id="lasgun", attack_attribute="ranged", damage=5),
        ),
        attacker,
        defender,
    )
    assert result.hit is True
    # damage 5 (margin 1 -> damage=5), armor_blocked=2, dealt=3 -> minor (3 < 15)
    assert result.armor_blocked == 2
    assert result.damage_dealt == 3
    assert result.target_wound_severity == "none" or result.target_wound_severity == "minor"


def test_miss_deals_no_damage() -> None:
    engine = _engine([80])
    attacker = Combatant(actor_id="a", ranged=30)
    defender = Combatant(actor_id="d", body=30)
    result = engine.resolve_attack(
        AttackRequest(
            attack_id="atk1", attacker_id="a", defender_id="d",
            weapon=Weapon(weapon_id="lasgun", attack_attribute="ranged", damage=5),
        ),
        attacker,
        defender,
    )
    assert result.hit is False
    assert result.damage_dealt == 0
    assert result.defender_dead is False


def test_cover_penalizes_attack() -> None:
    engine = _engine([35])  # 35 > 30-10=20 -> miss
    attacker = Combatant(actor_id="a", ranged=30)
    defender = Combatant(actor_id="d", body=30)
    result = engine.resolve_attack(
        AttackRequest(
            attack_id="atk1", attacker_id="a", defender_id="d", cover=10,
            weapon=Weapon(weapon_id="lasgun", attack_attribute="ranged", damage=5),
        ),
        attacker,
        defender,
    )
    assert result.hit is False


def test_penetration_bypasses_armor() -> None:
    engine = _engine([30])
    attacker = Combatant(actor_id="a", ranged=30)
    defender = Combatant(actor_id="d", body=30, armor=5)
    result = engine.resolve_attack(
        AttackRequest(
            attack_id="atk1", attacker_id="a", defender_id="d",
            weapon=Weapon(weapon_id="plasma", attack_attribute="ranged", damage=8, penetration=5),
        ),
        attacker,
        defender,
    )
    assert result.hit is True
    assert result.armor_blocked == 0  # armor fully bypassed


def test_high_damage_can_be_terminal() -> None:
    engine = _engine([30])
    attacker = Combatant(actor_id="a", ranged=30)
    defender = Combatant(actor_id="d", body=10, armor=0)
    result = engine.resolve_attack(
        AttackRequest(
            attack_id="atk1", attacker_id="a", defender_id="d",
            weapon=Weapon(weapon_id="melta", attack_attribute="ranged", damage=35),
        ),
        attacker,
        defender,
    )
    assert result.hit is True
    assert result.defender_dead is True
    assert result.target_wound_severity == "terminal"


def test_retreat_succeeds_on_good_agility_roll() -> None:
    engine = _engine([40])  # agility 40 target, roll 40 -> success
    attacker = Combatant(actor_id="a", ranged=30)
    defender = Combatant(actor_id="d", agility=40)
    assert engine.resolve_retreat(attacker, defender) is True


def test_retreat_fails_on_bad_roll() -> None:
    engine = _engine([90])
    attacker = Combatant(actor_id="a", ranged=30)
    defender = Combatant(actor_id="d", agility=40)
    assert engine.resolve_retreat(attacker, defender) is False


def test_suppression_requires_willpower() -> None:
    engine = _engine([70])
    attacker = Combatant(actor_id="a", ranged=30)
    defender = Combatant(actor_id="d", willpower=50)  # willpower attr used
    # roll 70 > 50 target -> not suppressed (returns False)
    assert engine.resolve_suppression(attacker, defender) is False