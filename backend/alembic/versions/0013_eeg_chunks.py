"""eeg_epochs.chunk_clean holds 9 chunks: 1 s, one every 0.5 s (D-F6-163)

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-06

Same pattern as 0002-0012: the SQL lives in sql/0013_eeg_chunks_up.sql and
sql/0013_eeg_chunks_down.sql and runs as is.
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0013_eeg_chunks_up.sql")


def downgrade() -> None:
    _run("0013_eeg_chunks_down.sql")
