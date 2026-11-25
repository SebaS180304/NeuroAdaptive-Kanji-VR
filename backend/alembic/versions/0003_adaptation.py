"""adaptation loop (fase 5a): decisions, applications, distractor interactions

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-14

Design: Planteamiento_Tecnico_F5a.md §8.3. Same pattern as 0002: the SQL lives
in sql/0003_adaptation_up.sql and sql/0003_adaptation_down.sql and runs as is.

What it adds:
  * distractor_interactions  <- DISTRACTOR_INTERACTION (D5, contract §5.11)
  * adaptation_decisions     <- ADAPTATION_DECISION (backend; NO_CHANGE included),
                                with the outcome column for ADAPTATION_OUTCOME (F6)
  * adaptation_applications  <- ADAPTATION_APPLIED / ADAPTATION_SKIPPED (Unity)
  * trials.cue_trigger / proactive_index (D9); idle also read from ANSWER_SELECTED
  * proj_apply and project_session replaced; trial_timeline recreated with the
    new columns at the end; view v_adaptations

Rows stored before the upgrade are projected with database/backfill_projection.sql
(project_session per session). Verified on 14 Oct against PostgreSQL 16:
up, down and up again; a synthetic adaptive session built from OBS_01 through
the live estimator projects with no errors, and project_session twice gives
the same rows.
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    # Same as 0002: straight to the driver with no parameter parsing, so the
    # PL/pgSQL bodies reach the server untouched.
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0003_adaptation_up.sql")


def downgrade() -> None:
    _run("0003_adaptation_down.sql")
