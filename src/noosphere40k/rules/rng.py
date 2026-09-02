"""Single randomness entry point (TECHNICAL_SPEC §7.3; B-02).

All game randomness flows through :class:`RngService`. Roll results are saved
into RandomDrawn events at commit time, so replay never re-rolls and does not
depend on the Python version's RNG algorithm. Tests inject fixed sequences.
"""

from __future__ import annotations

import secrets
from collections.abc import Sequence
from random import Random


class RngService:
    """Deterministic-by-default randomness service.

    If ``sequence`` is provided, draws are served from it in order (test
    injection). Otherwise a seeded ``Random`` instance is used; a ``secrets``
    source is optional for production but MVP uses the seeded PRNG for
    reproducibility.
    """

    def __init__(
        self,
        *,
        seed: int | None = None,
        sequence: Sequence[int] | None = None,
        source: str = "prng",
    ) -> None:
        self.seed = seed
        self.source = source
        if sequence is not None:
            self._queue = list(sequence)
            self._index = 0
        else:
            self._queue = []
            self._index = 0
        self._rng = Random(seed)
        self.draw_count = 0

    def draw_int(self, low: int, high: int) -> int:
        """Draw an integer in [low, high] inclusive, low >= 1."""
        if low < 1:
            raise ValueError("random draws are 1-based in this game")
        if self._index < len(self._queue):
            value = self._queue[self._index]
            self._index += 1
        else:
            if self.source == "secrets":
                value = secrets.randbelow(high - low + 1) + low
            else:
                value = self._rng.randint(low, high)
        if not (low <= value <= high):
            raise ValueError(f"injected draw {value} out of range [{low}, {high}]")
        self.draw_count += 1
        return value

    def draw_d100(self) -> int:
        """Draw 1d100 (1..100)."""
        return self.draw_int(1, 100)

    def remaining_injection(self) -> int:
        return len(self._queue) - self._index