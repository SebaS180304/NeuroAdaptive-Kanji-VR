"""trials.option_kinds, option_kind, lure_selected: the lure fields Unity sends (D-F6-143, D-F6-131)

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-10

Same pattern as 0002-0016: the SQL lives in sql/0017_trial_lures_up.sql and
sql/0017_trial_lures_down.sql and runs as is. proj_apply is patched in place, as 0015 did.
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0017_trial_lures_up.sql")


def downgrade() -> None:
    _run("0017_trial_lures_down.sql")
