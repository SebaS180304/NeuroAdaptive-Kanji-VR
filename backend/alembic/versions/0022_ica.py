"""eeg_sessions.ica: option (3) live, the S6 fit or why there is none (I2, D-F6-275, D-F6-276)

Revision ID: 0022
Revises: 0021
Create Date: 2026-11-20

Same pattern as 0002-0021: the SQL lives in sql/0022_ica_up.sql and
sql/0022_ica_down.sql and runs as is.
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0022"
down_revision: Union[str, None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0022_ica_up.sql")


def downgrade() -> None:
    _run("0022_ica_down.sql")
