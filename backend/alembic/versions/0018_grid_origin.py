"""eeg_sessions.grid_origin_lsl: one epoch grid for live and offline (D-F6-200 (1))

Revision ID: 0018
Revises: 0017
Create Date: 2026-11-17

Same pattern as 0002-0017: the SQL lives in sql/0018_grid_origin_up.sql and
sql/0018_grid_origin_down.sql and runs as is.
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0018_grid_origin_up.sql")


def downgrade() -> None:
    _run("0018_grid_origin_down.sql")
