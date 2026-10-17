"""research portal read side: v_session_overview, v_projection_errors, verify_*_fn()

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-17

Same pattern as 0002-0004: the SQL lives in sql/0006_research_read_up.sql and
sql/0006_research_read_down.sql and runs as is. Design: tasks/plan.md, Task 0.3.
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0006_research_read_up.sql")


def downgrade() -> None:
    _run("0006_research_read_down.sql")
