"""
End of a session, by itself (AU4, D-F6-244): the live epochs saved before the recording stops (D-F6-240 (4)),
then, after the XDF is processed, the four SQL of the kit and a summary. Read-only on the database.

    POSTGRES_HOST=127.0.0.1 python -m app.eeg.summary <session id>    # the same by hand, for a past session

Every file goes to backend/logs/<ses8>-<name>.txt (and <ses8>-live_epochs.csv, <ses8>-summary.txt).
"""

import asyncio
import csv
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

from app.eeg.preflight import REPO

SQL = [("verify_eeg", "database/verify_eeg.sql"), ("verify_adaptation", "database/verify_adaptation.sql"),
       ("verify_projection", "database/verify_projection.sql"), ("p0_j3_fallback_check", "database/p0_j3_fallback_check.sql")]
BAD_WORDS = ("FAIL", "OUT", "SHORT", "NOT VALID", "MISSING")
KEEP = ("== 2 ", "== 3 ", "== 4 ", "== 6 ", "== 7 ")  # verify_eeg sections copied whole: sync, S4 alpha, S6, usable epochs, A-7


async def _rows(sql: str, **params):
    from app.db.base import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(text(sql), params)
        return list(result.keys()), result.all()


async def export_live_epochs(session_id: str, log_dir: Path) -> Path:
    """Before the recording stops: autorun replaces these rows with the XDF cut afterwards (fill_from_xdf)."""
    cols, rows = await _rows("SELECT * FROM eeg_epochs WHERE session_id = :s ORDER BY 1, 2", s=session_id)
    path = log_dir / f"{session_id[:8]}-live_epochs.csv"
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    print(f"live epochs saved before the stop: {len(rows)} rows -> {path} (D-F6-240 (4))")
    return path


def run_sql(name: str, rel: str, ses8: str, log_dir: Path) -> tuple[int, str]:
    with open(REPO / rel, "rb") as sql:
        p = subprocess.run(["docker", "compose", "exec", "-T", "db", "psql", "-U", "neuroadaptive",
                            "-d", "neuroadaptive_vr", "-v", f"sid={ses8}"],
                           stdin=sql, capture_output=True, cwd=REPO, timeout=300)
    out = (p.stdout + p.stderr).decode("utf-8", errors="replace")
    (log_dir / f"{ses8}-{name}.txt").write_text(out, encoding="utf-8")
    return p.returncode, out


def sections(out: str) -> list[tuple[str, list[str]]]:
    found, head, body = [], None, []
    for line in out.splitlines():
        if line.startswith("== "):
            if head:
                found.append((head, body))
            head, body = line, []
        elif head:
            body.append(line)
    if head:
        found.append((head, body))
    return found


def flags(out: str) -> list[str]:
    """Rows of an 'expected no rows' check, and table rows that say FAIL, OUT, SHORT, NOT VALID or MISSING."""
    found = []
    for head, body in sections(out):
        if "expected no rows" in head and not any(line.strip() == "(0 rows)" for line in body):
            found.append(f"{head.strip()} -> has rows")
        for line in body:
            if "|" in line and any(c.strip() in BAD_WORDS for c in line.split("|")):
                found.append(line.strip())
    return found


async def facts(session_id: str) -> list[str]:
    _, (row,) = await _rows("SELECT condition, status, created_at, completed_at FROM experiment_sessions "
                            "WHERE id = :s", s=session_id)
    lines = [f"condition {row[0]} · status {row[1]}"
             + (f" · Play -> S9 {(row[3] - row[2]).total_seconds() / 60:.1f} min" if row[3] else " · not completed")]
    _, acc = await _rows("SELECT block_state, count(*), count(*) FILTER (WHERE is_correct) FROM trials "
                         "WHERE session_id = :s GROUP BY 1 ORDER BY 1", s=session_id)
    lines.append("accuracy: " + ", ".join(f"{str(st).split('_')[0]} {ok}/{n}" for st, n, ok in acc))
    return lines


async def write(session_id: str, recording: str, log_dir: Path = Path("logs")) -> int:
    ses8 = session_id[:8]
    log_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"session {session_id}", f"recording: {recording}", *await facts(session_id)]
    failed, bad = [], []
    for name, rel in SQL:
        code, out = run_sql(name, rel, ses8, log_dir)
        if code:
            failed.append(f"{name} exit {code}")
        bad += [f"{name}: {f}" for f in flags(out)]
        if name == "verify_eeg":
            for head, body in sections(out):
                if head.startswith(KEEP):
                    lines += ["", head, *[b for b in body if b.strip() and not b.startswith("CREATE")]]
    lines += ["", "SQL: " + ("all four ran" if not failed else "; ".join(failed)),
              "flags: " + ("none" if not bad else ""), *[f"  {b}" for b in bad],
              f"files: {log_dir.resolve()}\\{ses8}-*.txt"]
    text_out = "\n".join(lines)
    (log_dir / f"{ses8}-summary.txt").write_text(text_out, encoding="utf-8")
    print("---- summary ----\n" + text_out)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(write(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "not recorded by autorun")))
