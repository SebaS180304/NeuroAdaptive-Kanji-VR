"""eeg_trace_bins and eeg_sessions.traces_now: the monitor's 8-channel traces (TR, D-F6-301 (5))

Revision ID: 0024
Revises: 0023
Create Date: 2026-11-26

Same pattern as 0002-0023: the SQL lives in sql/0024_eeg_trace_bins_up.sql and
sql/0024_eeg_trace_bins_down.sql and runs as is.
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0024"
down_revision: Union[str, None] = "0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0024_eeg_trace_bins_up.sql")


def downgrade() -> None:
    _run("0024_eeg_trace_bins_down.sql")
