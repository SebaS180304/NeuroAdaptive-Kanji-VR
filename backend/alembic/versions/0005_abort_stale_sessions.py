"""abandoned sessions: abort_stale_sessions() sets idle IN_PROGRESS sessions to ABORTED

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-17

Same pattern as 0002-0004: the SQL lives in sql/0005_abort_stale_sessions_up.sql and
sql/0005_abort_stale_sessions_down.sql and runs as is. Design: tasks/plan.md, Task 0.2.
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0005_abort_stale_sessions_up.sql")


def downgrade() -> None:
    _run("0005_abort_stale_sessions_down.sql")
