"""KANJI_EXPOSED.stages_authored is a count, not a boolean

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-23

Same pattern as 0002-0007: the SQL lives in sql/0008_stages_authored_count_up.sql and
sql/0008_stages_authored_count_down.sql and runs as is. With the set A objects of S5 the
count reaches 2, which the boolean cast of the projection cannot read.
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0008_stages_authored_count_up.sql")


def downgrade() -> None:
    _run("0008_stages_authored_count_down.sql")
