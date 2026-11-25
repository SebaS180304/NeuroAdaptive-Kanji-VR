"""
Learner Profile v1 (Plan_Fase6.md §4, D-F6-2 and D-F6-3; tasks/plan.md).

One ``learner_profiles`` row per participant (migration 0007), rebuilt from
``session_events`` and the schema. Only COMPLETED sessions count: an ABORTED one
is in no part, even if it reached S6 or S7 (Sebas, 21 Oct). Three parts, oldest
session first:

- ``calibrations``: the S6 profile of each session, as the estimator builds it,
  plus S6 correct as ``correct`` of ``n`` and the trial types that fell back to the
  global median.
- ``adaptations``: the changes (``NO_CHANGE`` left out), grouped by estimated state,
  cause, dimension and direction, with outcome counts, O4 reasons and their ids per
  session.
- ``trend``: each session's condition, kanji set and S7 numbers, and for adaptive
  sessions the ``NO_CHANGE`` count, whether decisions were recorded at all (not
  before migration 0003, 13 Oct) and their rules version (D-F6-92).

The profile never changes how a session starts (D-F6-1): nothing on that path
reads it.

    # inside the backend container
    docker compose exec backend python -m app.adaptation.learner_profile --all
    docker compose exec backend python -m app.adaptation.learner_profile --all --check
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from collections import Counter
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.adaptation.profile import MIN_TRIALS_PER_TYPE, build_profile, profile_trials
from app.adaptation.trials import S7_STATE, build_trials

VERSION = "v1"

logger = logging.getLogger(__name__)

_SESSIONS = text("""
SELECT s.id::text AS session_id, s.condition::text AS condition, s.assigned_kanji_set AS kanji_set,
       s.created_at, t.s7_trials, t.s7_correct, t.s7_mean_rt_ms, d.decisions, d.no_change, d.rules_version
FROM experiment_sessions s
CROSS JOIN LATERAL (
    SELECT count(*) AS s7_trials, count(*) FILTER (WHERE is_correct) AS s7_correct,
           round(avg(response_time_ms)::numeric, 1)::float AS s7_mean_rt_ms
    FROM trials WHERE session_id = s.id AND block_state = :s7) t
CROSS JOIN LATERAL (
    SELECT count(*) AS decisions, count(*) FILTER (WHERE action = 'NO_CHANGE') AS no_change,
           max(rules_version) AS rules_version
    FROM adaptation_decisions WHERE session_id = s.id) d
WHERE s.participant_id = :pid AND s.status = 'COMPLETED'
ORDER BY s.created_at
""")

_EVENTS = text("SELECT id, event_type, payload FROM session_events WHERE session_id = :sid ORDER BY id")

# The O4 reason (RESOLVED, HELD_WITH_DROP, NOT_APPLIED, INCOMPLETE...) is only in the event payload.
_CHANGES = text("""
SELECT d.session_id::text AS session_id, d.decision_id, d.learner_state, d.cause, d.evidence, d.dimension,
       CASE WHEN d.to_level > d.from_level THEN 'UP' ELSE 'DOWN' END AS direction,
       d.outcome, e.payload->>'outcome_reason' AS reason,
       s.session_clock_started_at + d.decided_elapsed_ms * interval '1 millisecond' AS decided_at
FROM adaptation_decisions d
JOIN experiment_sessions s ON s.id = d.session_id
LEFT JOIN session_events e ON e.id = d.outcome_event_id
WHERE s.participant_id = :pid AND s.status = 'COMPLETED' AND d.action <> 'NO_CHANGE'
ORDER BY s.created_at, d.decided_elapsed_ms
""")

_UPSERT = text("""
INSERT INTO learner_profiles (participant_id, profile_version, computed_at, session_ids, profile)
VALUES (:pid, :version, now(), CAST(:session_ids AS uuid[]), CAST(:profile AS jsonb))
ON CONFLICT (participant_id, profile_version)
DO UPDATE SET computed_at = now(), session_ids = EXCLUDED.session_ids, profile = EXCLUDED.profile
""")


def _calibration(session_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    trials = build_trials(events)
    profile = build_profile(trials)
    used = profile_trials(trials)
    valid = Counter(t.trial_type for t in used if t.rt_valid)
    p = profile.as_dict()
    return {
        "session_id": session_id, **p,
        "correct": sum(t.is_correct for t in used), "n": p["n_trials"],
        # Types whose reference is the global median: fewer than MIN_TRIALS_PER_TYPE valid trials.
        "fallback_types": sorted({t.trial_type for t in used} - {k for k, n in valid.items()
                                                                  if n >= MIN_TRIALS_PER_TYPE}),
    }


def _groups(changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for c in changes:
        cause = c["cause"]
        # UNDERCHALLENGED with FAST and NO_ENVIRONMENT both met has its own clause (Contenido_UI_F-PROFILE.md §3.2).
        if c["learner_state"] == "UNDERCHALLENGED" and {"FAST", "NO_ENVIRONMENT"} <= set(c.get("evidence") or ()):
            cause = "FAST+NO_ENVIRONMENT"
        key = f"{c['learner_state']}.{cause or 'NONE'}.{c['dimension']}.{c['direction']}"
        g = groups.setdefault(key, {
            "key": key, "learner_state": c["learner_state"], "cause": cause,
            "dimension": c["dimension"], "direction": c["direction"], "count": 0,
            "outcomes": {}, "outcome_reasons": {}, "decisions": {}, "last_decided_at": None,
        })
        outcome, reason = c["outcome"] or "NOT_RECORDED", c["reason"] or "NOT_RECORDED"
        g["count"] += 1
        g["outcomes"][outcome] = g["outcomes"].get(outcome, 0) + 1
        reasons = g["outcome_reasons"].setdefault(outcome, {})
        reasons[reason] = reasons.get(reason, 0) + 1
        g["decisions"].setdefault(c["session_id"], []).append(c["decision_id"])
        if c["decided_at"] is not None:
            g["last_decided_at"] = max(filter(None, [g["last_decided_at"], c["decided_at"].isoformat()]))
    # Most frequent first, then the most recent; never by outcome (D-F6-1: not a ranking).
    ordered = sorted(groups.values(), key=lambda g: g["last_decided_at"] or "", reverse=True)
    return sorted(ordered, key=lambda g: g["count"], reverse=True)


async def build(db: AsyncSession, participant_id: str) -> tuple[list[str], dict[str, Any]]:
    """The session ids and the profile JSON, from events and schema; writes nothing."""
    sessions = [dict(r._mapping) for r in await db.execute(_SESSIONS, {"pid": participant_id, "s7": S7_STATE})]
    calibrations = []
    for s in sessions:
        events = [dict(r._mapping) for r in await db.execute(_EVENTS, {"sid": s["session_id"]})]
        calibrations.append(_calibration(s["session_id"], events))
    changes = [dict(r._mapping) for r in await db.execute(_CHANGES, {"pid": participant_id})]
    trend = [{
        "session_id": s["session_id"], "condition": s["condition"], "kanji_set": s["kanji_set"],
        "created_at": s["created_at"].isoformat(),
        "s7_trials": s["s7_trials"], "s7_correct": s["s7_correct"], "s7_mean_rt_ms": s["s7_mean_rt_ms"],
        # STATIC never adapts: None, not 0. False: an adaptive session with no decision rows.
        "no_change": None if s["condition"] == "STATIC" else s["no_change"],
        "decisions_recorded": None if s["condition"] == "STATIC" else s["decisions"] > 0,
        # rules-v1 / rules-v2 (D-F6-92); None without decisions. A session never mixes versions.
        "rules_version": s["rules_version"],
    } for s in sessions]
    profile = {"calibrations": calibrations, "adaptations": _groups(changes), "trend": trend}
    return [s["session_id"] for s in sessions], profile


async def compute(db: AsyncSession, participant_id: str) -> None:
    """Rebuild and store one participant's profile. The caller commits."""
    session_ids, profile = await build(db, participant_id)
    await db.execute(_UPSERT, {"pid": participant_id, "version": VERSION,
                               "session_ids": session_ids,
                               "profile": json.dumps(profile)})


async def refresh(participant_ids) -> None:
    """Recompute after a session completes or aborts, in its own DB session.

    A failure is logged and never raised: the PATCH or the sweep that triggered it
    must not fail for a derived table; ``--all`` rebuilds whatever was missed.
    """
    from app.db.base import AsyncSessionLocal

    for pid in participant_ids:
        try:
            async with AsyncSessionLocal() as db:
                await compute(db, str(pid))
                await db.commit()
        except Exception:
            logger.exception("learner profile of %s not computed", pid)


async def differences(db: AsyncSession, participant_id: str) -> list[str]:
    """What the stored row has that a rebuild would not (computed_at aside)."""
    session_ids, profile = await build(db, participant_id)
    row = (await db.execute(text(
        "SELECT session_ids, profile FROM learner_profiles WHERE participant_id = :pid AND profile_version = :v"),
        {"pid": participant_id, "v": VERSION})).first()
    if row is None:
        return ["no stored profile"]
    diffs = []
    if [str(s) for s in row.session_ids] != session_ids:
        diffs.append("session_ids")
    # Through JSON both ways, so floats and dates compare as they are stored.
    expected = json.loads(json.dumps(profile))
    diffs += [part for part in sorted(set(expected) | set(row.profile))
              if expected.get(part) != row.profile.get(part)]
    return diffs


async def _main(check: bool) -> int:
    from app.db.base import AsyncSessionLocal   # only needed here

    async with AsyncSessionLocal() as db:
        pids = (await db.execute(text(
            "SELECT DISTINCT participant_id::text FROM experiment_sessions ORDER BY 1"))).scalars().all()
        bad = 0
        for pid in pids:
            if check:
                diffs = await differences(db, pid)
                if diffs:
                    bad += 1
                    print(f"{pid}: {', '.join(diffs)}")
            else:
                await compute(db, pid)
        if not check:
            await db.commit()
    print(f"{len(pids)} participant(s) {'checked' if check else 'computed'}, {bad} with differences")
    return 1 if bad else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rebuild or check every Learner Profile v1.")
    parser.add_argument("--all", action="store_true", required=True, help="every participant with sessions")
    parser.add_argument("--check", action="store_true", help="compare with the stored rows; write nothing")
    sys.exit(asyncio.run(_main(parser.parse_args().check)))
