"""eeg_sessions.heartbeat_at, eeg_gap_ms: the live process's heartbeat (D-F6-171)

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-10

Same pattern as 0002-0015: the SQL lives in sql/0016_eeg_heartbeat_up.sql and
sql/0016_eeg_heartbeat_down.sql and runs as is. Written by app/eeg/live.py every 2 s.
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0016_eeg_heartbeat_up.sql")


def downgrade() -> None:
    _run("0016_eeg_heartbeat_down.sql")
