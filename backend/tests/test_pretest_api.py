"""
Kanji pre-test API (spec §13.2, tasks/plan.md Task 3): a scripted pre-test from
the first kanji to the stored substitutions, plus the guards and the registration
rules (Task 1.2 of the research portal plan).
"""

import pytest

from app.pretest.rules import contract, ranked_substitutes

CODE = "TEST_PRETEST"
ID = {k["kanji"]: k["id"] for k in contract()["kanji"]}


async def _participant(client, consent: bool = True) -> str:
    resp = await client.post("/participants", json={"external_code": CODE, "consent_obtained": consent})
    assert resp.status_code == 201
    return resp.json()["id"]


async def _answer(client, pid, char, self_report="NO", reading=None, meaning=None):
    body = {"kanji_id": ID[char], "self_report": self_report}
    if self_report != "NO":
        body |= {"typed_reading": "x", "typed_meaning": "x",
                 "reading_correct": reading, "meaning_correct": meaning}
    return await client.post(f"/participants/{pid}/pretest/responses", json=body)


@pytest.mark.asyncio
async def test_full_pretest_with_one_known_primary_and_one_known_substitute(client):
    pid = await _participant(client)
    first, second = ranked_substitutes("A", contract()["sets"]["A"], "月")[:2]

    state = (await client.get(f"/participants/{pid}/pretest")).json()
    assert state["completed"] is False and state["next"]["kanji"] == "月"
    assert "meaning" not in state["next"] and "target_reading" not in state["next"]

    state = (await _answer(client, pid, "月", "YES", True, True)).json()
    assert state["next"]["kanji"] == first
    state = (await _answer(client, pid, first, "UNSURE", True, True)).json()
    assert state["next"]["kanji"] == second
    state = (await _answer(client, pid, second, "YES", False, True)).json()   # PARTIALLY_KNOWN

    while state["next"] is not None:
        state = (await _answer(client, pid, state["next"]["kanji"])).json()

    assert state["completed"] is True and state["completed_at"] is not None
    assert state["substitutions"] == [{"set": "A", "original": "月", "substitute": second}]
    assert state["flagged"] == []
    assert state["answered"] == 17

    # Stored result, not recomputed: the same on a fresh GET.
    assert (await client.get(f"/participants/{pid}/pretest")).json() == state


@pytest.mark.asyncio
async def test_out_of_order_and_repeated_answers_are_refused(client):
    pid = await _participant(client)
    assert (await _answer(client, pid, "車")).status_code == 409      # next is 月
    assert (await _answer(client, pid, "月")).status_code == 200
    assert (await _answer(client, pid, "月")).status_code == 409      # already answered
    assert (await client.get(f"/participants/{pid}/pretest")).json()["answered"] == 1


@pytest.mark.asyncio
async def test_yes_without_the_researchers_verdict_is_rejected(client):
    pid = await _participant(client)
    resp = await client.post(f"/participants/{pid}/pretest/responses",
                             json={"kanji_id": ID["月"], "self_report": "YES"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_check_grades_without_storing(client):
    pid = await _participant(client)
    resp = await client.post(f"/participants/{pid}/pretest/check",
                             json={"kanji_id": ID["月"], "typed_reading": "tsuki", "typed_meaning": "sun"})
    assert resp.json() == {"reading_correct": True, "meaning_correct": False}
    assert (await client.get(f"/participants/{pid}/pretest")).json()["answered"] == 0


@pytest.mark.asyncio
async def test_unknown_participant_is_404(client):
    resp = await client.get("/participants/00000000-0000-0000-0000-000000000000/pretest")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_everything_known_stores_fifteen_flags(client):
    pid = await _participant(client)
    state = (await client.get(f"/participants/{pid}/pretest")).json()
    while state["next"] is not None:
        state = (await _answer(client, pid, state["next"]["kanji"], "YES", True, True)).json()
    assert state["completed"] and state["substitutions"] == []
    assert len(state["flagged"]) == 15
    assert (await client.get(f"/participants/{pid}/pretest")).json() == state


@pytest.mark.asyncio
async def test_consent_sets_its_timestamp(client):
    with_consent = (await client.post("/participants", json={"external_code": CODE, "consent_obtained": True})).json()
    assert with_consent["consent_obtained"] is True and with_consent["consent_obtained_at"] is not None
    without = await client.post("/participants", json={"external_code": CODE + "_NC"})
    assert without.status_code == 201 and without.json()["consent_obtained_at"] is None


@pytest.mark.asyncio
async def test_pretest_without_consent_is_409_and_stores_nothing(client):
    pid = await _participant(client, consent=False)
    resp = await _answer(client, pid, "月")
    assert resp.status_code == 409 and resp.json()["detail"] == "consent not recorded"
    resp = await client.post(f"/participants/{pid}/pretest/check",
                             json={"kanji_id": ID["月"], "typed_reading": "tsuki", "typed_meaning": "moon"})
    assert resp.status_code == 409
    assert (await client.get(f"/participants/{pid}/pretest")).json()["answered"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("field, value", [("age_range", "50-60"), ("self_rated_attention_difficulty", "ALWAYS")])
async def test_unknown_registration_option_is_422(client, field, value):
    resp = await client.post("/participants", json={"external_code": CODE, field: value})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_approved_registration_options_are_stored(client):
    body = {"external_code": CODE, "consent_obtained": True, "age_range": "45+",
            "previous_japanese_experience": None, "previous_kanji_experience": False,
            "previous_vr_experience": True, "self_rated_attention_difficulty": "VERY_OFTEN"}
    resp = await client.post("/participants", json=body)
    assert resp.status_code == 201
    assert {k: resp.json()[k] for k in body} == body
