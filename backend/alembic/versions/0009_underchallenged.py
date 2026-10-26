"""UNDERCHALLENGED state of behavior-v2 / rules-v2 in adaptation_decisions

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-26

Same pattern as 0002-0008: the SQL lives in sql/0009_underchallenged_up.sql and
sql/0009_underchallenged_down.sql and runs as is. D-F6-59 adds the state UNDERCHALLENGED
and the causes FAST and NO_ENVIRONMENT, which neither fit VARCHAR(12) nor the v1 CHECKs.
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0009_underchallenged_up.sql")


def downgrade() -> None:
    _run("0009_underchallenged_down.sql")
