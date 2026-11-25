"""schema v1 (fase 3, F3.4): relational projection of session_events

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-01

Design: claude/MER_Schema_v1.md (1 Oct 2026). The SQL lives next to this
file, in sql/0002_schema_v1_up.sql and sql/0002_schema_v1_down.sql, and runs
as is: one file that psql, pgAdmin and this migration all execute the same
way, instead of the DDL copied into Python strings.

What it adds, on top of the five Phase 1 tables (which do not change):
  * the kanji_items catalogue (seeded separately: database/seed_kanji_items.sql);
  * the projected tables (session_states, trial_blocks, planned_trials,
    trials, hint_requests, environment_applications, peripheral_events,
    head_away_episodes, kanji_exposures, assemblies, assembly_attempts) and
    projection_errors;
  * the projector in PL/pgSQL: project_event(event_id), called by the
    backend after every insert, and project_session(session_id) for the
    backfill;
  * the views v_environment_intervals and v_trial_behavior and the function
    trial_timeline(session_id, window_n).

session_events stays the source of truth: downgrading drops only what can
be rebuilt from it.

Verified on 1 Oct against PostgreSQL 16 with schema.sql of Phase 1: up, down
and up again, plus the synthetic session of tests/fixtures (live projection,
re-projection and project_session give identical rows).
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    # Straight to psycopg2 with no parameters at all: no bind parsing by
    # SQLAlchemy and no %-formatting by the driver, so the PL/pgSQL bodies
    # (RAISE '... %', LIKE '%enum%', '::' casts) reach the server untouched.
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0002_schema_v1_up.sql")


def downgrade() -> None:
    _run("0002_schema_v1_down.sql")
