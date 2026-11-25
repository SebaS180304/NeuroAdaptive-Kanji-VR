"""adaptation_decisions.eeg_*: what the EEG did in each rules-v2-mm decision (D-F6-128)

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-10

Same pattern as 0002-0014: the SQL lives in sql/0015_rules_v2_mm_up.sql and
sql/0015_rules_v2_mm_down.sql and runs as is. The columns come from the ``eeg`` block
of the ADAPTATION_DECISION payload (app/adaptation/rules.py).
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent / "sql"


def _run(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql, execution_options={"no_parameters": True})


def upgrade() -> None:
    _run("0015_rules_v2_mm_up.sql")


def downgrade() -> None:
    _run("0015_rules_v2_mm_down.sql")
