"""
Kanji pre-test substitution rules (spec §13.2, tasks/plan.md): validity of a
reserve kanji against a participant's effective set, and best-fit ranking.
No database.
"""

import pytest

from app.pretest.rules import contract, ranked_substitutes, valid_substitutes


@pytest.fixture(autouse=True)
def _clean_test_participants():
    """Overrides the conftest fixture: these tests do not touch the database."""
    yield


def test_nominal_sets_reproduce_the_exported_table():
    # Drift guard: same rules as tools/kanji_metrics.py, from the exported data.
    c = contract()
    for name, members in c["sets"].items():
        for e in members:
            assert valid_substitutes(name, members, e) == c["substitutionTable"][name][e], (name, e)


def test_excluded_kanji_are_never_offered():
    a = contract()["sets"]["A"]
    assert "木" in valid_substitutes("A", a, "月")
    assert "木" not in valid_substitutes("A", a, "月", excluded={"木"})


def test_second_substitution_is_checked_against_the_first():
    # 月 -> 木 already applied. 水 is a valid substitute for 竹 in the nominal
    # set, but 水 and 木 are too alike to share a set (sim > 0.55).
    effective = ["木", "車", "火", "竹", "石"]
    assert "水" in contract()["substitutionTable"]["A"]["竹"]
    assert "水" not in valid_substitutes("A", effective, "竹")


def test_ranking_is_a_reordering_of_the_valid_list():
    a = contract()["sets"]["A"]
    ranked = ranked_substitutes("A", a, "月")
    assert sorted(ranked) == sorted(valid_substitutes("A", a, "月"))
    assert ranked != []
