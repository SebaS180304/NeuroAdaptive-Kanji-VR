"""esquema inicial fase 1: participants, experiment_sessions,
session_config_snapshots, system_validation_events, session_events

Revision ID: 0001
Revises:
Create Date: 2026-08-24

Esta migracion fue verificada aplicandola (como DDL equivalente, ver
database/schema.sql) contra una instancia real de PostgreSQL 16:
inserts con FK, joins entre las 5 tablas y cascade delete al borrar un
participante se probaron manualmente antes de congelar esta version.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


experimental_condition = postgresql.ENUM(
    "STATIC", "BEHAVIOR_ADAPTIVE", "MULTIMODAL_ADAPTIVE",
    name="experimental_condition",
    create_type=False,
)
session_status = postgresql.ENUM(
    "CREATED", "IN_PROGRESS", "COMPLETED", "ABORTED",
    name="session_status",
    create_type=False,
)
game_flow_state = postgresql.ENUM(
    "S0_SESSION_INITIALIZATION",
    "S1_WELCOME_ORIENTATION",
    "S2_VR_TUTORIAL",
    "S3_SYSTEM_VALIDATION",
    "S4_EEG_BASELINE",
    "S5_STANDARDIZED_LEARNING",
    "S6_GUIDED_PRACTICE_CALIBRATION",
    "S7_EXPERIMENTAL_RETRIEVAL",
    "S8_IMMEDIATE_ASSESSMENT",
    "S9_SESSION_SUMMARY",
    "S10_HCI_SELF_REPORT",
    name="game_flow_state",
    create_type=False,
)
validation_component = postgresql.ENUM(
    "UNITY_BACKEND_WS", "WAVEX_EEG", "CLOCK_SYNC", "OTHER",
    name="validation_component",
    create_type=False,
)
validation_status = postgresql.ENUM(
    "OK", "WARNING", "ERROR",
    name="validation_status",
    create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    bind = op.get_bind()
    experimental_condition.create(bind, checkfirst=True)
    session_status.create(bind, checkfirst=True)
    game_flow_state.create(bind, checkfirst=True)
    validation_component.create(bind, checkfirst=True)
    validation_status.create(bind, checkfirst=True)

    op.create_table(
        "participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                   server_default=sa.text("gen_random_uuid()")),
        sa.Column("external_code", sa.String(32), nullable=False, unique=True),
        sa.Column("age_range", sa.String(32), nullable=True),
        sa.Column("previous_japanese_experience", sa.Boolean(), nullable=True),
        sa.Column("previous_kanji_experience", sa.Boolean(), nullable=True),
        sa.Column("previous_vr_experience", sa.Boolean(), nullable=True),
        sa.Column("self_rated_attention_difficulty", sa.String(32), nullable=True),
        sa.Column("consent_obtained", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("consent_obtained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_participants_external_code", "participants", ["external_code"])

    op.create_table(
        "experiment_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                   server_default=sa.text("gen_random_uuid()")),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("participants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("condition", experimental_condition, nullable=False),
        sa.Column("status", session_status, nullable=False, server_default="CREATED"),
        sa.Column("current_state", game_flow_state, nullable=False,
                   server_default="S0_SESSION_INITIALIZATION"),
        sa.Column("assigned_kanji_set", sa.String(8), nullable=True),
        sa.Column("visit_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("random_seed", sa.String(64), nullable=True),
        sa.Column("software_version", sa.String(32), nullable=True),
        sa.Column("experiment_config_version", sa.String(32), nullable=True),
        sa.Column("controller_config_version", sa.String(32), nullable=True),
        sa.Column("session_clock_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_experiment_sessions_participant_id", "experiment_sessions", ["participant_id"])

    op.create_table(
        "session_config_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                   server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("experiment_sessions.id", ondelete="CASCADE"),
                   nullable=False, unique=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "system_validation_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                   server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("experiment_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component", validation_component, nullable=False),
        sa.Column("status", validation_status, nullable=False),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("client_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_system_validation_events_session_id", "system_validation_events", ["session_id"])

    op.create_table(
        "session_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("experiment_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("client_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("server_received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_session_events_session_id", "session_events", ["session_id"])
    op.create_index("ix_session_events_event_type", "session_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("session_events")
    op.drop_table("system_validation_events")
    op.drop_table("session_config_snapshots")
    op.drop_table("experiment_sessions")
    op.drop_table("participants")

    bind = op.get_bind()
    validation_status.drop(bind, checkfirst=True)
    validation_component.drop(bind, checkfirst=True)
    game_flow_state.drop(bind, checkfirst=True)
    session_status.drop(bind, checkfirst=True)
    experimental_condition.drop(bind, checkfirst=True)
