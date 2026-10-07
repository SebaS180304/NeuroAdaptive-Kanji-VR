"""
Replay of a session through the estimator (Planteamiento_Tecnico_F5a.md §5).

Prints, trial by trial of S7, the window indicators, the state, the cause and
the confidence the live path would have produced. The rule engine (rules.py,
Tue 13) adds its decision column here.

    # from the database (inside the backend container), by id or id prefix
    docker compose exec backend python -m app.adaptation.replay 87761ce6

    # from an exported JSON (list of session_events rows, or {"events": [...]})
    python -m app.adaptation.replay 87761ce6 --file tests/fixtures/prueba_fase_f3_events.json

    # one JSON object per S7 trial, for diffs and evidence
    python -m app.adaptation.replay 87761ce6 --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.adaptation.estimator import estimate
from app.adaptation.indicators import window_indicators, window_trials
from app.adaptation.profile import build_profile
from app.adaptation.trials import build_trials


def load_from_file(path: Path, session_prefix: str) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    events = data["events"] if isinstance(data, dict) else data
    rows = [e for e in events if str(e["session_id"]).startswith(session_prefix)]
    ids = {str(e["session_id"]) for e in rows}
    if len(ids) != 1:
        raise SystemExit(f"'{session_prefix}' matches {len(ids)} sessions in {path}")
    return sorted(rows, key=lambda e: e["id"])


def load_from_db(session_prefix: str) -> list[dict[str, Any]]:
    from sqlalchemy import create_engine, text   # only needed here

    from app.config import get_settings

    engine = create_engine(get_settings().sync_database_url)
    with engine.connect() as conn:
        ids = conn.execute(
            text("SELECT DISTINCT session_id::text FROM session_events WHERE session_id::text LIKE :p"),
            {"p": session_prefix + "%"},
        ).scalars().all()
        if len(ids) != 1:
            raise SystemExit(f"'{session_prefix}' matches {len(ids)} sessions in the database")
        rows = conn.execute(
            text("SELECT id, session_id::text AS session_id, event_type, payload "
                 "FROM session_events WHERE session_id::text = :s ORDER BY id"),
            {"s": ids[0]},
        ).mappings().all()
    return [dict(r) for r in rows]


def replay(events: Iterable[Mapping[str, Any]]) -> tuple[Any, list[dict[str, Any]]]:
    """Profile and one row per answered S7 trial, as the live path computes them."""
    trials = build_trials(events)
    profile = build_profile(trials)
    rows = []
    for trial in trials:
        if trial.phase != "S7":
            continue
        window = window_indicators(window_trials(trials, trial.trial_id), profile)
        result = estimate(window, profile)
        rows.append({"trial": trial, "window": window, "result": result})
    return profile, rows


def _fmt(value: float | None, pattern: str = "{:.2f}") -> str:
    return "—" if value is None else pattern.format(value)


def print_table(session: str, profile, rows: list[dict[str, Any]]) -> None:
    p = profile.as_dict()
    print(f"Session {session}")
    print(f"S6 profile: rt_ref {p['rt_ref']} (global {p['rt_ref_global']}) · spread {p['rt_spread']} · "
          f"acc {p['acc_ref']} · idle_eff {p['idle_eff_ref']} · n {p['n_trials']} · reliability {p['reliability']}")
    print()
    head = f"{'trial':7} {'type':5} {'rt':>6} {'ok':2}  {'ratio':>5} {'z':>6} {'acc':>6} {'fast':>4} {'slow':>4} " \
           f"{'away':>5} {'dwell':>5} {'orient':>6} {'idle':>6}  {'state':10} {'cause':11} {'conf':>4}"
    print(head)
    print("-" * len(head))
    for row in rows:
        t, w, r = row["trial"], row["window"], row["result"]
        print(f"{t.trial_id:7} {t.trial_type[:2]:5} {t.rt_ms:6d} {'ok' if t.is_correct else 'x':2}  "
              f"{_fmt(w.rt_ratio):>5} {_fmt(w.rt_z, '{:.1f}'):>6} {_fmt(w.acc_delta):>6} {w.fast_errors:4d} {w.slow_errors:4d} "
              f"{w.away_ms:5d} {w.env_dwell_ms:5d} {_fmt(w.orienting_rate):>6} {_fmt(w.idle_eff_ratio):>6}  "
              f"{r.state:10} {(r.cause or ''):11} {r.confidence:4.2f}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay a session through the F5a estimator.")
    parser.add_argument("session", help="session id or id prefix (e.g. 87761ce6)")
    parser.add_argument("--file", type=Path, help="read events from a JSON export instead of the database")
    parser.add_argument("--json", action="store_true", help="one JSON object per S7 trial")
    args = parser.parse_args(argv)

    events = load_from_file(args.file, args.session) if args.file else load_from_db(args.session)
    profile, rows = replay(events)
    if args.json:
        for row in rows:
            print(json.dumps(row["result"].as_dict(), ensure_ascii=False, default=str))
    else:
        print_table(str(events[0]["session_id"]) if events else args.session, profile, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
