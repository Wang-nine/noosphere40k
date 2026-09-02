"""B-06: wounds, pressure, corruption."""

from __future__ import annotations

from noosphere40k.rules.wounds import (
    CORRUPTION_THRESHOLD_TERMINAL,
    apply_corruption,
    apply_pressure,
    is_terminal_severity,
    resolve_injury_result,
)


def test_corruption_accumulation() -> None:
    result = apply_corruption(0, 30)
    assert result.new_corruption == 30
    assert result.condition_applied is None
    assert result.terminal is False


def test_corruption_notable_threshold() -> None:
    result = apply_corruption(35, 10)
    assert result.new_corruption == 45
    assert result.condition_applied == "corruption_notable"
    assert result.terminal is False


def test_corruption_terminal_threshold() -> None:
    result = apply_corruption(90, 20)
    assert result.new_corruption == CORRUPTION_THRESHOLD_TERMINAL
    assert result.condition_applied == "corruption_terminal"
    assert result.terminal is True


def test_corruption_clamps_to_max() -> None:
    result = apply_corruption(95, 50)
    assert result.new_corruption == CORRUPTION_THRESHOLD_TERMINAL


def test_pressure_thresholds() -> None:
    assert apply_pressure(30, 10).condition_applied is None  # 40 < 50
    assert apply_pressure(40, 20).condition_applied == "pressure_fatigue"  # 60 >= 50
    assert apply_pressure(49, 2).condition_applied == "pressure_fatigue"  # 51 >= 50
    assert apply_pressure(79, 2).condition_applied == "pressure_breakdown"  # 81 >= 80


def test_pressure_clamps() -> None:
    result = apply_pressure(99, 10)
    assert result.new_pressure == 100


def test_injury_severity_mapping() -> None:
    severity, payload = resolve_injury_result(current_wounds=[], severity="critical", location="leg")
    assert severity == "critical"
    assert payload["location"] == "leg"


def test_unknown_severity_defaults_to_minor() -> None:
    severity, payload = resolve_injury_result(current_wounds=[], severity="weird", location="arm")
    assert severity == "minor"


def test_terminal_severity_flag() -> None:
    assert is_terminal_severity("terminal") is True
    assert is_terminal_severity("minor") is False