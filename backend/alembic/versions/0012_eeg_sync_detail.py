"""eeg_sessions.sync_detail: how the sync offset and drift were found, or why not (D-F6-157, D-F6-159)

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-06

Same pattern as 0002-0011: the SQL lives in sql/0012_eeg_sync_detail_up.sql and
sql/0012_eeg_sync_detail_down.sql and runs as is. Written by app/eeg/sync.py.
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0012_eeg_sync_detail_up.sql")


def downgrade() -> None:
    _run("0012_eeg_sync_detail_down.sql")
