"""
Replay of a session through the estimator (Planteamiento_Tecnico_F5a.md §5).

Prints, trial by trial of S7, the window indicators, the state, the cause, the
confidence and the rule engine's decision that the live path would have
produced. A recorded session is replayed as if it were adaptive: the engine
assumes each change it decides is applied, whatever condition the session
actually ran in, so a STATIC recording shows what the adaptive path would have
done with the same behaviour.

    # from the database (inside the backend container), by id or id prefix
    docker compose exec backend python -m app.adaptation.replay 87761ce6

    # from an exported JSON (list of session_events rows, or {"events": [...]})
    python -m app.adaptation.replay 87761ce6 --file tests/fixtures/prueba_fase_f3_events.json

    # one JSON object per S7 trial, for diffs and evidence
    python -m app.adaptation.replay 87761ce6 --json

    # with another estimator version than the session's own
    python -m app.adaptation.replay 678b7806 --version behavior-v2

    # as MULTIMODAL_ADAPTIVE, with the EEG of its XDF (X2). The container does not see the XDF folder and the PC's
    # venv has no psycopg2, so copy it in first (Git Bash: MSYS_NO_PATHCONV=1):
    #   docker compose cp "<xdf_path of eeg_sessions>" backend:/tmp/07343b5d.xdf
    #   docker compose exec backend python -m app.adaptation.replay 07343b5d --xdf /tmp/07343b5d.xdf
    # (--xdf with no path takes eeg_sessions.xdf_path, for where that path is visible)
    # the epochs are cut as live.py cuts them (live.Buffer, fed in CHUNK_S pieces), and window.py counts them at each
    # answer (D-F6-172, D-F6-188). A window while EEG_STATUS said PROCESS_DOWN does not count, as it did not live.

A session replays with the estimator version of its stored decisions (a v1
session stays v1); one without decisions (STATIC) with the current version.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.adaptation.estimator import ESTIMATOR_VERSION, ESTIMATOR_VERSIONS, estimate
from app.adaptation.indicators import window_indicators, window_trials
from app.adaptation.outcome import POST_WINDOW, classify
from app.adaptation.profile import build_profile
from app.adaptation.rules import decide, initial_state
from app.adaptation.state import NO_EEG, stored_version
from app.adaptation.trials import S7_STATE, build_trials


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


def s7_entry(events: Iterable[Mapping[str, Any]]) -> Mapping[str, Any]:
    """Payload of the STATE_ENTERED that opened S7 (start time and levels), or {}."""
    for event in events:
        payload = event.get("payload") or {}
        if event["event_type"] == "STATE_ENTERED" and payload.get("state") == S7_STATE:
            return payload
    return {}


PROCESS_DOWN = "PROCESS_DOWN"
HITCH_MS = 100     # as epochs.HITCH_MS (D-F6-129)
CHUNK_S = 0.5      # shortcut: XDF fed to live.Buffer in 0.5 s pieces (live pulls ~0.2 s); finer if z differences matter


def down_spans(events: Iterable[Mapping[str, Any]]) -> list[tuple[int, float]]:
    """Session-ms spans where EEG_STATUS said the EEG process was down, until the next status."""
    marks = sorted(((e.get("payload") or {}).get("session_elapsed_ms"), (e.get("payload") or {}).get("status"))
                   for e in events if e["event_type"] == "EEG_STATUS"
                   and (e.get("payload") or {}).get("session_elapsed_ms") is not None)
    spans = []
    for i, (t, status) in enumerate(marks):
        if status == PROCESS_DOWN:
            spans.append((t, marks[i + 1][0] if i + 1 < len(marks) else float("inf")))
    return spans


def hitches_per_state(markers: Iterable[tuple[float, Mapping[str, Any]]]) -> dict[str, tuple[int, float]]:
    """FRAME_HITCH over 100 ms per state: (count, total ms). They are only in the XDF (F4 §7)."""
    out: dict[str, tuple[int, float]] = {}
    for _, m in markers:
        if m.get("event") == "FRAME_HITCH" and m.get("duration_ms", 0) > HITCH_MS:
            n, ms = out.get(m.get("state"), (0, 0.0))
            out[m.get("state")] = (n + 1, round(ms + m["duration_ms"], 1))
    return out


def xdf_source(path: str, montage: dict):
    """eeg_source for replay() from an XDF: epochs as live.py cuts them, the reference as live writes it."""
    import numpy as np

    from app.eeg import baseline, epochs, live, lsl_reader, reference, window

    streams = lsl_reader.load_xdf(path)
    aura, markers = streams[lsl_reader.EEG_STREAM], epochs.markers_of(streams.get(lsl_reader.MARKER_STREAM))
    x, ts = np.asarray(aura["time_series"], dtype=float), np.asarray(aura["time_stamps"], dtype=float)
    buf = live.Buffer(float(aura["info"]["nominal_srate"][0]), montage)
    step, mk, cut = max(1, int(buf.srate * CHUNK_S)), 0, []
    for i in range(0, len(ts), step):
        hi = ts[min(i + step, len(ts)) - 1]
        j = mk
        while j < len(markers) and markers[j][0] <= hi:
            j += 1
        buf.add(x[i:i + step].tolist(), ts[i:i + step].tolist(), markers[mk:j])
        mk = j
        buf.sync_if_ready()
        cut += buf.new_epochs()
    ref = reference.compute(cut, baseline.spans(markers))
    info = {"epochs": len(cut), "offset_ms": buf.offset_ms, "reference": ref.get("source"),
            "hitches": hitches_per_state(markers)}
    return (lambda first_start_ms, decision_ms: window.evaluate(cut, first_start_ms, decision_ms, ref)), info


def replay(events: Iterable[Mapping[str, Any]], version: str | None = None,
           eeg_source=None) -> tuple[Any, list[dict[str, Any]]]:
    """Profile and one row per answered S7 trial, as the live path computes them.

    ``eeg_source(first_start_ms, decision_ms)`` -> window.evaluate(): replays as MULTIMODAL_ADAPTIVE (rules-v2-mm).
    """
    events = list(events)
    downs = down_spans(events)
    version = version or stored_version(events) or ESTIMATOR_VERSION
    trials = build_trials(events)
    profile = build_profile(trials)
    entry = s7_entry(events)
    started = entry.get("session_elapsed_ms")
    engine = initial_state(entry.get("esl"), entry.get("lal"), None if started is None else int(started))
    rows = []
    open_changes = []      # (row, pre result, seq): O4, assumed applied
    for trial in trials:
        if trial.phase != "S7":
            continue
        window = window_indicators(window_trials(trials, trial.trial_id), profile)
        result = estimate(window, profile, version=version)
        seq = trial.trial_sequence or int(trial.trial_id.split("-")[1])
        eeg = None
        if eeg_source is not None:   # the same window start as SessionAdaptationState.feed
            first = window_trials(trials, trial.trial_id)[0]
            first_start = first.started_ms if first.started_ms is not None else first.answered_ms
            down = any(lo <= trial.answered_ms < hi for lo, hi in downs)
            eeg = (None if down else eeg_source(first_start, trial.answered_ms)) or NO_EEG
        decision, engine = decide(result, seq, trial.answered_ms, engine, eeg=eeg)
        row = {"trial": trial, "window": window, "result": result, "decision": decision, "outcome": None}
        for change in [c for c in open_changes if seq >= c[2] + POST_WINDOW]:
            change[0]["outcome"] = classify(change[0]["decision"].as_dict(), change[1], result)
            open_changes.remove(change)
        if decision.is_change:
            open_changes.append((row, result, seq))
        rows.append(row)
    for row, pre, _ in open_changes:       # S7 ended first
        row["outcome"] = classify(row["decision"].as_dict(), pre, None)
    return profile, rows


def _fmt(value: float | None, pattern: str = "{:.2f}") -> str:
    return "—" if value is None else pattern.format(value)


def print_table(session: str, profile, rows: list[dict[str, Any]]) -> None:
    p = profile.as_dict()
    print(f"Session {session} · {rows[0]['result'].version if rows else '—'}")
    print(f"S6 profile: rt_ref {p['rt_ref']} (global {p['rt_ref_global']}) · spread {p['rt_spread']} · "
          f"acc {p['acc_ref']} · idle_eff {p['idle_eff_ref']} · n {p['n_trials']} · reliability {p['reliability']}")
    print()
    head = f"{'trial':7} {'type':5} {'rt':>6} {'ok':2}  {'ratio':>5} {'z':>6} {'acc':>6} {'fast':>4} {'slow':>4} " \
           f"{'away':>5} {'dwell':>5} {'orient':>6} {'idle':>6}  {'state':15} {'cause':14} {'conf':>4}  {'decision'}"
    print(head)
    print("-" * len(head))
    for row in rows:
        t, w, r = row["trial"], row["window"], row["result"]
        print(f"{t.trial_id:7} {t.trial_type[:2]:5} {t.rt_ms:6d} {'ok' if t.is_correct else 'x':2}  "
              f"{_fmt(w.rt_ratio):>5} {_fmt(w.rt_z, '{:.1f}'):>6} {_fmt(w.acc_delta):>6} {w.fast_errors:4d} {w.slow_errors:4d} "
              f"{w.away_ms:5d} {w.env_dwell_ms:5d} {_fmt(w.orienting_rate):>6} {_fmt(w.idle_eff_ratio):>6}  "
              f"{r.state:15} {(r.cause or ''):14} {r.confidence:4.2f}  {_fmt_decision(row['decision'])}")
    changes = [row["decision"] for row in rows if row["decision"].is_change]
    print()
    print(f"{len(changes)} change(s)")
    outcomes = {row["trial"].trial_id: row["outcome"] for row in rows if row["outcome"] is not None}
    for d in changes:
        print(f"  {d.trial_id}: {d.explanation}")
        o = outcomes.get(d.trial_id)
        if o is not None:
            print(f"      -> {o.outcome} ({o.reason_code}): {o.explanation}")


def _fmt_decision(d) -> str:
    eeg = "" if d.eeg is None else f"  [EEG {d.eeg['effect']}{'' if d.eeg['counted'] else ', not counted'}]"
    if d.is_change:
        return f"{d.action} {d.from_level}->{d.to_level}" + (" +cues" if d.proactive_cues else "") + eeg
    return f"- {d.reason_code}" + eeg


def xdf_of(session_prefix: str) -> tuple[str, dict]:
    """The session's XDF path and montage, from eeg_sessions."""
    from sqlalchemy import create_engine, text

    from app.config import get_settings
    from app.eeg.baseline import DEFAULT_MONTAGE

    with create_engine(get_settings().sync_database_url).connect() as conn:
        row = conn.execute(text("SELECT xdf_path, montage FROM eeg_sessions WHERE session_id::text LIKE :p"),
                           {"p": session_prefix + "%"}).one()
    return row[0], row[1] or DEFAULT_MONTAGE


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay a session through the F5a estimator.")
    parser.add_argument("session", help="session id or id prefix (e.g. 87761ce6)")
    parser.add_argument("--file", type=Path, help="read events from a JSON export instead of the database")
    parser.add_argument("--json", action="store_true", help="one JSON object per S7 trial")
    parser.add_argument("--version", choices=ESTIMATOR_VERSIONS,
                        help="estimator version (default: the session's own, else the current one)")
    parser.add_argument("--xdf", nargs="?", const="", metavar="PATH",
                        help="replay as MULTIMODAL_ADAPTIVE with the EEG of this XDF (default: the session's own)")
    args = parser.parse_args(argv)

    events = load_from_file(args.file, args.session) if args.file else load_from_db(args.session)
    source = None
    if args.xdf is not None:
        path, montage = xdf_of(args.session)
        source, info = xdf_source(args.xdf or path, montage)
        hitches = ", ".join(f"{k} {n} ({ms:.0f} ms)" for k, (n, ms) in info["hitches"].items()) or "none"
        print(f"EEG from {args.xdf or path}: {info['epochs']} epochs cut as live.py, S3 offset {info['offset_ms']} ms, "
              f"reference {info['reference']}; FRAME_HITCH > {HITCH_MS} ms per state: {hitches}", file=sys.stderr)
    profile, rows = replay(events, args.version, eeg_source=source)
    if args.json:
        for row in rows:
            out = {**row["result"].as_dict(), "decision": row["decision"].as_dict(),
                   "outcome": row["outcome"].as_dict() if row["outcome"] else None}
            print(json.dumps(out, ensure_ascii=False, default=str))
    else:
        print_table(str(events[0]["session_id"]) if events else args.session, profile, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
