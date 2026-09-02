"""B-02: RngService — single randomness entry, injectable draws."""

from __future__ import annotations

import pytest

from noosphere40k.rules.rng import RngService


def test_injected_sequence_served_in_order() -> None:
    rng = RngService(sequence=[42, 7])
    assert rng.draw_d100() == 42
    assert rng.draw_d100() == 7
    assert rng.remaining_injection() == 0


def test_prng_draws_in_range_and_tracked() -> None:
    rng = RngService(seed=1234)
    draws = [rng.draw_d100() for _ in range(200)]
    assert all(1 <= d <= 100 for d in draws)
    assert rng.draw_count == 200


def test_same_seed_same_draws() -> None:
    a = [RngService(seed=7).draw_d100() for _ in range(5)]
    b = [RngService(seed=7).draw_d100() for _ in range(5)]
    assert a == b


def test_injected_out_of_range_rejected() -> None:
    rng = RngService(sequence=[0])
    with pytest.raises(ValueError):
        rng.draw_d100()


def test_draw_int_enforces_one_based() -> None:
    with pytest.raises(ValueError):
        RngService().draw_int(0, 10)