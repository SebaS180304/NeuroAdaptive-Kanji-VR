"""game_flow_state SR_DELAYED_RETENTION and experiment_sessions.evaluated_session_id: block R (D-F6-125, D-F6-190, D-F6-223)

Revision ID: 0019
Revises: 0018
Create Date: 2026-11-17

Same pattern as 0002-0018: the SQL lives in sql/0019_block_r_up.sql and
sql/0019_block_r_down.sql and runs as is.
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0019_block_r_up.sql")


def downgrade() -> None:
    _run("0019_block_r_down.sql")
