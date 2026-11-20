"""eeg_sessions.live_vs_xdf: how many epochs of the live cut differ from the XDF cut (V, D-F6-281 (2))

Revision ID: 0023
Revises: 0022
Create Date: 2026-11-20

Same pattern as 0002-0022: the SQL lives in sql/0023_live_vs_xdf_up.sql and
sql/0023_live_vs_xdf_down.sql and runs as is.
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0023_live_vs_xdf_up.sql")


def downgrade() -> None:
    _run("0023_live_vs_xdf_down.sql")
