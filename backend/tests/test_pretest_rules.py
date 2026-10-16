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


# --------------------------------------------------------------------------- #
# Classification, chain and auto-grading (Task 2)
# --------------------------------------------------------------------------- #

from app.pretest.rules import (  # noqa: E402
    KNOWN, PARTIALLY_KNOWN, UNKNOWN, auto_grade, chain_state, classify,
)

PRIMARIES = [c for m in contract()["sets"].values() for c in m]


def _walk(answer):
    """Runs the chain to the end; `answer(char)` returns the classification."""
    responses, asked = {}, []
    while (state := chain_state(responses)).next is not None:
        asked.append(state.next)
        responses[state.next] = answer(state.next)
    return asked, state


def test_classify():
    assert classify("NO", True, True) == UNKNOWN
    assert classify("YES", False, False) == UNKNOWN
    assert classify("UNSURE", True, False) == PARTIALLY_KNOWN
    assert classify("YES", False, True) == PARTIALLY_KNOWN
    assert classify("YES", True, True) == KNOWN


def test_all_no_asks_the_fifteen_primaries_and_substitutes_nothing():
    asked, state = _walk(lambda c: UNKNOWN)
    assert asked == PRIMARIES
    assert state.substitutions == [] and state.flagged == []


def test_known_primary_walks_down_its_ranking_until_one_is_not_known():
    a = contract()["sets"]["A"]
    first, second = ranked_substitutes("A", a, "月")[:2]
    answers = {"月": KNOWN, first: KNOWN}
    asked, state = _walk(lambda c: answers.get(c, PARTIALLY_KNOWN))
    assert asked[:3] == ["月", first, second]
    assert state.substitutions == [("A", "月", second)]


def test_a_reserve_kanji_is_asked_once_and_used_once():
    asked, state = _walk(lambda c: KNOWN if c in PRIMARIES else UNKNOWN)
    assert len(asked) == len(set(asked))
    used = [s for _, _, s in state.substitutions]
    assert len(used) == len(set(used))
    # Every primary is either substituted or flagged.
    assert len(state.substitutions) + len(state.flagged) == 15


def test_original_stays_and_is_flagged_when_candidates_run_out():
    asked, state = _walk(lambda c: KNOWN)
    assert state.substitutions == []
    assert len(state.flagged) == 15
    assert all(c in PRIMARIES or c in contract()["reserve"] for c in asked)


@pytest.mark.parametrize("typed", ["つき", "ツキ", "tsuki", "Tsuki ", "tuki"])
def test_reading_accepts_kana_and_romaji(typed):
    assert auto_grade("月", typed, "")[0]


def test_reading_rejects_a_wrong_answer_and_handles_katakana_targets():
    assert not auto_grade("月", "tsuka", "")[0]
    assert auto_grade("学", "gaku", "")[0] and auto_grade("学", "がく", "")[0]
    assert auto_grade("茶", "cha", "")[0] and auto_grade("茶", "tya", "")[0]


@pytest.mark.parametrize("typed", ["foot", "Leg", " leg ", "a foot"])
def test_meaning_accepts_any_listed_variant(typed):
    assert auto_grade("足", "", typed)[1]


def test_meaning_rejects_a_near_miss():
    assert not auto_grade("田", "", "rice")[1]
    assert auto_grade("田", "", "rice-field")[1]


@pytest.mark.parametrize("typed,hepburn", [("shu", "shu"), ("chu", "chu"), ("syu", "shu"),
                                           ("hune", "fune"), ("zya", "ja"), ("si", "shi")])
def test_romaji_folding_keeps_hepburn_intact(typed, hepburn):
    from app.pretest.rules import _fold_romaji
    assert _fold_romaji(typed) == hepburn


def test_every_target_reading_has_a_romaji_form():
    from app.pretest.rules import _hiragana, _romaji
    for k in contract()["kanji"]:
        assert _romaji(_hiragana(k["targetReading"])).isascii(), k["kanji"]


# --------------------------------------------------------------------------- #
# Checkpoint A: properties the plan promises that the cases above do not pin
# --------------------------------------------------------------------------- #

def test_ranking_puts_the_closest_set_first():
    from app.pretest.rules import _distance_to_nominal
    for name, members in contract()["sets"].items():
        for e in members:
            scores = [_distance_to_nominal(name, [r if c == e else c for c in members])
                      for r in ranked_substitutes(name, members, e)]
            assert scores == sorted(scores), (name, e)


def test_every_effective_set_stays_valid_after_many_substitutions():
    # Worst case for the bands: every primary KNOWN, every reserve kanji new.
    from app.pretest.rules import _hard_clash, _in_band
    _, state = _walk(lambda c: KNOWN if c in PRIMARIES else UNKNOWN)
    for name, members in contract()["sets"].items():
        effective = list(members)
        for s, o, r in state.substitutions:
            if s == name:
                effective[effective.index(o)] = r
        assert _in_band(effective), (name, effective)
        assert not any(_hard_clash(a, b) for i, a in enumerate(effective) for b in effective[i + 1:]), effective


def test_partially_known_primary_stays_and_triggers_no_extra_question():
    asked, state = _walk(lambda c: PARTIALLY_KNOWN if c == "月" else UNKNOWN)
    assert asked == PRIMARIES
    assert state.substitutions == []


def test_blank_answers_are_wrong():
    assert auto_grade("月", "", "") == (False, False)
    assert auto_grade("月", "   ", " ") == (False, False)
