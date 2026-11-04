"""eeg_epochs: the 5 s epochs of a session with EEG and their quality (F4 S2)

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-04

Same pattern as 0002-0010: the SQL lives in sql/0011_eeg_epochs_up.sql and
sql/0011_eeg_epochs_down.sql and runs as is. Planteamiento_Tecnico_F4.md §2.3,
with the per-chunk flags P7 of D-F6-127 needs (every clean second counted once).
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0011_eeg_epochs_up.sql")


def downgrade() -> None:
    _run("0011_eeg_epochs_down.sql")
