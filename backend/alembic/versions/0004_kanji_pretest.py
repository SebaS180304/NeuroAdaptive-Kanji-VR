"""kanji pre-test (spec 13.2): responses, substitutions, participants.pretest_completed_at

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-16

Same pattern as 0002/0003: the SQL lives in sql/0004_kanji_pretest_up.sql and
sql/0004_kanji_pretest_down.sql and runs as is. Design: tasks/plan.md.
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0004_kanji_pretest_up.sql")


def downgrade() -> None:
    _run("0004_kanji_pretest_down.sql")
