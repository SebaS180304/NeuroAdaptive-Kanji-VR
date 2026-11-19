"""eeg_sessions.monitor, monitor_at: the live monitor's per-channel figures (M1b, D-F6-254, D-F6-265)

Revision ID: 0021
Revises: 0020
Create Date: 2026-11-19

Same pattern as 0002-0020: the SQL lives in sql/0021_monitor_up.sql and
sql/0021_monitor_down.sql and runs as is.
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0021_monitor_up.sql")


def downgrade() -> None:
    _run("0021_monitor_down.sql")
