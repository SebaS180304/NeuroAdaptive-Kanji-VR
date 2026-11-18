from app.eeg import summary

# Cut from verify_eeg.sql and verify_adaptation.sql on T01 (0077f47d), 18 Nov
EEG = """CREATE VIEW
== 2 · Sync (F4 §2.4): robust spread <= 50 ms
 session  | offset_ms | robust_spread_ms | offset_check | spread_check
----------+-----------+------------------+--------------+-------------
 0077f47d |      35.7 |              7.9 | ok           | ok
(1 row)

== 5 · S7 windows where the EEG counts (A-7 asks >= 60 %)
 session  | windows | eeg_counts | pct | check
----------+---------+------------+-----+-------
 0077f47d |      18 |          0 |   0 | SHORT
(1 row)

== 7 · A-7, multimodal session valid
 session  |               source               |    a7     | s7_p7
----------+------------------------------------+-----------+------
 0077f47d | live engine (adaptation_decisions) | NOT VALID | 0/18
(1 row)
"""
ADAPT_OK = """== 2 · STATIC never adapts (criterion 5): expected no rows
 session | what | trial_id
---------+------+----------
(0 rows)
"""
ADAPT_BAD = """== 3 · Adaptive S7: one decision per answered trial: expected no rows
 session  | trial_id | problem
----------+----------+---------
 0077f47d | S7-004   | no decision
(1 row)
"""


def test_the_bad_rows_of_t01_are_flagged_and_the_good_ones_not() -> None:
    found = summary.flags(EEG)
    assert len(found) == 2 and "SHORT" in found[0] and "NOT VALID" in found[1]


def test_an_expected_no_rows_check_with_rows_is_flagged() -> None:
    assert summary.flags(ADAPT_OK) == []
    assert summary.flags(ADAPT_BAD) == ["== 3 · Adaptive S7: one decision per answered trial: expected no rows -> has rows"]


def test_sections_keep_their_tables() -> None:
    heads = [h for h, _ in summary.sections(EEG)]
    assert [h[:4] for h in heads] == ["== 2", "== 5", "== 7"]
