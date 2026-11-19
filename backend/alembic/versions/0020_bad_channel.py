"""eeg_sessions.bad_channel, bad_channel_from_ms and eeg_epochs.excluded_channels: the persistently bad channel (D-F6-216, D-F6-224)

Revision ID: 0020
Revises: 0019
Create Date: 2026-11-19

Same pattern as 0002-0019: the SQL lives in sql/0020_bad_channel_up.sql and
sql/0020_bad_channel_down.sql and runs as is.
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0020"
down_revision: Union[str, None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0020_bad_channel_up.sql")


def downgrade() -> None:
    _run("0020_bad_channel_down.sql")
