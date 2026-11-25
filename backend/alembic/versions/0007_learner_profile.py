"""Learner Profile v1: learner_profiles, one row per participant and format version

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-21

Same pattern as 0002-0006: the SQL lives in sql/0007_learner_profile_up.sql and
sql/0007_learner_profile_down.sql and runs as is. Design: tasks/plan.md,
"Architecture decisions: Learner Profile v1".
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0007_learner_profile_up.sql")


def downgrade() -> None:
    _run("0007_learner_profile_down.sql")
