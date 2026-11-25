"""
F4 S3 (tasks/todo.md, M6): app/eeg/window.py, whether the EEG counts in a decision window and its z.
D-F6-127 (P7), D-F6-151 (15 s), D-F6-162 (by the centre, union), D-F6-172 (finished epochs), D-F6-177 (ends at the answer).
"""

import math

import pytest

from app.eeg import window

REF = {"source": "S6", "indices": {
    "engagement_index": {"mean": math.log(0.5), "sd": 0.25, "n": 8},
    "theta_fz": {"mean": math.log(0.2), "sd": 0.5, "n": 8},
    "alpha_parietal": {"mean": math.log(0.1), "sd": None, "n": 8},
    "theta_beta": {"mean": math.log(2.0), "sd": 0.3, "n": 8},
}}


def _epoch(start_ms: int, quality: str = "GOOD", clean: list[bool] | None = None, ei: float = 0.5) -> dict:
    empty = quality == "POOR"
    return {"start_ms": start_ms, "end_ms": start_ms + 5000, "quality": quality,
            "chunk_clean": [True] * 9 if clean is None else clean,
            "engagement_index": None if empty else ei, "theta_fz": None if empty else 0.2,
            "alpha_parietal": None if empty else 0.1, "theta_beta": None if empty else 2.0}


def test_fast_trials_still_reach_back_15_s_from_the_answer() -> None:
    out = window.evaluate([_epoch(83_000), _epoch(90_000)], first_start_ms=95_000, decision_ms=100_000, ref=REF)
    assert out["non_poor"] == 2                  # centre at 85.5 s is inside 85–100 s, though the trials began at 95 s


def test_slow_trials_use_their_own_start() -> None:
    eps = [_epoch(62_000), _epoch(70_000)]
    assert window.evaluate(eps, first_start_ms=60_000, decision_ms=100_000, ref=REF)["non_poor"] == 2
    assert window.evaluate(eps, first_start_ms=65_000, decision_ms=100_000, ref=REF)["non_poor"] == 1


def test_an_epoch_that_has_not_finished_at_the_answer_does_not_count() -> None:
    out = window.evaluate([_epoch(90_000), _epoch(96_000)], first_start_ms=90_000, decision_ms=100_000, ref=REF)
    assert out["non_poor"] == 1                  # the second ends at 101 s, with its centre inside


def test_an_epoch_counts_only_if_it_ended_1_5_s_before_the_answer() -> None:
    # D-F6-188: ends at 98.5 s counts, at 98.6 s (1.4 s before the answer) does not; both centres are inside.
    eps = [_epoch(90_000), _epoch(93_500), _epoch(93_600)]
    assert window.evaluate(eps, first_start_ms=90_000, decision_ms=100_000, ref=REF)["non_poor"] == 2


def test_a_second_shared_by_two_epochs_counts_once() -> None:
    out = window.evaluate([_epoch(90_000), _epoch(92_500)], first_start_ms=88_000, decision_ms=100_000, ref=REF)
    assert out["clean_s"] == 7.5


def test_it_counts_with_two_non_poor_epochs_and_five_clean_seconds() -> None:
    assert window.evaluate([_epoch(90_000), _epoch(92_500)], 88_000, 100_000, REF)["counted"] is True


def test_one_non_poor_epoch_is_not_enough() -> None:
    assert window.evaluate([_epoch(90_000)], 88_000, 100_000, REF)["counted"] is False


def test_under_five_clean_seconds_is_not_enough() -> None:
    three_s = [k < 5 for k in range(9)]          # chunks at 0–2 s: 3 s covered, ACCEPTABLE
    out = window.evaluate([_epoch(90_000, "ACCEPTABLE", three_s), _epoch(90_500, "ACCEPTABLE", three_s)], 88_000, 100_000, REF)
    assert out["non_poor"] == 2 and out["clean_s"] == 3.5 and out["counted"] is False


def test_clean_chunks_of_a_poor_epoch_count_as_seconds_like_the_sql() -> None:
    two_s = [k < 3 for k in range(9)]
    assert window.evaluate([_epoch(90_000, "POOR", two_s)], 88_000, 100_000, REF)["clean_s"] == 2.0


def test_old_epochs_with_five_chunks_read_one_second_apart() -> None:
    assert window.evaluate([_epoch(90_000, clean=[True] * 5)], 88_000, 100_000, REF)["clean_s"] == 5.0


def test_z_is_the_mean_of_the_non_poor_epochs_z_against_the_reference() -> None:
    eps = [_epoch(90_000, ei=0.5), _epoch(92_500, ei=0.5 * math.exp(0.5)), _epoch(92_000, "POOR")]
    out = window.evaluate(eps, 88_000, 100_000, REF)
    assert out["z"]["engagement_index"] == pytest.approx((0.0 + 2.0) / 2)


def test_an_index_without_spread_has_no_z() -> None:
    assert window.evaluate([_epoch(90_000)], 88_000, 100_000, REF)["z"]["alpha_parietal"] is None


def test_without_a_reference_there_is_no_z() -> None:
    assert window.evaluate([_epoch(90_000)], 88_000, 100_000, {"source": None, "indices": {}})["z"]["engagement_index"] is None
