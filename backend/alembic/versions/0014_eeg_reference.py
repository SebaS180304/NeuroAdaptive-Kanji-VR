"""eeg_sessions.reference: mean and SD of ln(index) that the z of the session uses (D-F6-73)

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-09

Same pattern as 0002-0013: the SQL lives in sql/0014_eeg_reference_up.sql and
sql/0014_eeg_reference_down.sql and runs as is. Written by app/eeg/reference.py.
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0014_eeg_reference_up.sql")


def downgrade() -> None:
    _run("0014_eeg_reference_down.sql")
