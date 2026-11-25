"""eeg_sessions: one row per session recorded with the AURA cap (F4 S2)

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-02

Same pattern as 0002-0009: the SQL lives in sql/0010_eeg_sessions_up.sql and
sql/0010_eeg_sessions_down.sql and runs as is. Planteamiento_Tecnico_F4.md §2.3,
with the P9 decisions of D-F6-127 (one XDF per session, the montage here).
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0010_eeg_sessions_up.sql")


def downgrade() -> None:
    _run("0010_eeg_sessions_down.sql")
