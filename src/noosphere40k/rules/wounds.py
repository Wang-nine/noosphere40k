"""Wounds, pressure and corruption (TECHNICAL_SPEC §7.3; B-06).

Every terminal condition is explainable to an event chain: the Condition or
Wound event carries the causation event id. Child-stage content defaults are
enforced by the caller (clamping graphic violence); the rules here stay
generic and deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass

# Corruption is accumulated and has explicit thresholds; reaching the final
# threshold is a terminal condition (corruption_terminal ending).
CORRUPTION_THRESHOLD_TERMINAL = 100
CORRUPTION_THRESHOLD_NOTABLE = 40

# Pressure conditions
PRESSURE_MAX = 100


@dataclass
class CorruptionResult:
    new_corruption: int
    condition_applied: str | None
    terminal: bool


@dataclass
class PressureResult:
    new_pressure: int
    condition_applied: str | None


def apply_corruption(current: int, delta: int) -> CorruptionResult:
    """Apply a corruption delta; returns the new total and any condition."""
    new_value = max(0, min(CORRUPTION_THRESHOLD_TERMINAL, current + delta))
    condition: str | None = None
    if new_value >= CORRUPTION_THRESHOLD_TERMINAL:
        condition = "corruption_terminal"
    elif new_value >= CORRUPTION_THRESHOLD_NOTABLE:
        condition = "corruption_notable"
    return CorruptionResult(
        new_corruption=new_value,
        condition_applied=condition,
        terminal=new_value >= CORRUPTION_THRESHOLD_TERMINAL,
    )


def apply_pressure(current: int, delta: int) -> PressureResult:
    """Apply stress/pressure; spawns temporary conditions at thresholds."""
    new_value = max(0, min(PRESSURE_MAX, current + delta))
    condition: str | None = None
    if new_value >= 80:
        condition = "pressure_breakdown"
    elif new_value >= 50:
        condition = "pressure_fatigue"
    return PressureResult(new_pressure=new_value, condition_applied=condition)


WOUND_SEVERITY_ORDER = {"minor": 1, "major": 2, "critical": 3, "terminal": 4}


def resolve_injury_result(
    *,
    current_wounds: list[dict[str, object]],
    severity: str,
    location: str,
) -> tuple[str, dict[str, object]]:
    """Return (new_severity, wound_payload). Terminal wounds are rule-derived."""
    if severity not in WOUND_SEVERITY_ORDER:
        severity = "minor"
    return severity, {
        "wound_id": f"wound.{location}.{len(current_wounds) + 1}",
        "location": location,
        "severity": severity,
        "cause_event_id": None,  # filled by the caller with the causation event
    }


def is_terminal_severity(severity: str) -> bool:
    return severity == "terminal"


__all__ = [
    "CORRUPTION_THRESHOLD_TERMINAL",
    "CORRUPTION_THRESHOLD_NOTABLE",
    "apply_corruption",
    "apply_pressure",
    "resolve_injury_result",
    "is_terminal_severity",
    "WOUND_SEVERITY_ORDER",
]