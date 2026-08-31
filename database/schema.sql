-- =====================================================================
-- NeuroAdaptive VR -- Esquema inicial de PostgreSQL (Fase 1)
-- =====================================================================
-- Este archivo es la referencia humana-legible del esquema que produce
-- la migracion Alembic 0001_initial_schema (backend/alembic/versions).
-- Los dos deben mantenerse identicos; si se autogenera una nueva
-- migracion con Alembic, este archivo debe regenerarse con:
--   pg_dump --schema-only --no-owner --no-privileges neuroadaptive_vr
--
-- Alcance: ver docstring de backend/app/models/__init__.py. Este es el
-- esquema "fundacional" de la Fase 1 (Foundation & Feasibility) --
-- participante, sesion, snapshot de configuracion y dos tablas de
-- telemetria/validacion tecnica genericas para probar el walking
-- skeleton Unity <-> Backend <-> PostgreSQL. El contenido kanji, los
-- trials, los eventos de adaptacion ESL/LAL y las ventanas EEG se
-- modelan en fases posteriores (M2-M4) sobre esta misma base.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto; -- gen_random_uuid()

-- ---------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------

CREATE TYPE experimental_condition AS ENUM (
    'STATIC',
    'BEHAVIOR_ADAPTIVE',
    'MULTIMODAL_ADAPTIVE'
);

CREATE TYPE session_status AS ENUM (
    'CREATED',
    'IN_PROGRESS',
    'COMPLETED',
    'ABORTED'
);

-- Estados formales S0-S10 del Game Flow v1 (spec seccion 7)
CREATE TYPE game_flow_state AS ENUM (
    'S0_SESSION_INITIALIZATION',
    'S1_WELCOME_ORIENTATION',
    'S2_VR_TUTORIAL',
    'S3_SYSTEM_VALIDATION',
    'S4_EEG_BASELINE',
    'S5_STANDARDIZED_LEARNING',
    'S6_GUIDED_PRACTICE_CALIBRATION',
    'S7_EXPERIMENTAL_RETRIEVAL',
    'S8_IMMEDIATE_ASSESSMENT',
    'S9_SESSION_SUMMARY',
    'S10_HCI_SELF_REPORT'
);

CREATE TYPE validation_component AS ENUM (
    'UNITY_BACKEND_WS',
    'WAVEX_EEG',
    'CLOCK_SYNC',
    'OTHER'
);

CREATE TYPE validation_status AS ENUM (
    'OK',
    'WARNING',
    'ERROR'
);

-- ---------------------------------------------------------------------
-- participants
-- ---------------------------------------------------------------------
-- Metadata de screening (spec 13.1). Sin nombre ni identificador
-- directo: external_code es el codigo pseudonimizado asignado por el
-- investigador fuera del sistema.

CREATE TABLE participants (
    id                                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_code                       VARCHAR(32) NOT NULL UNIQUE,
    age_range                           VARCHAR(32),
    previous_japanese_experience        BOOLEAN,
    previous_kanji_experience           BOOLEAN,
    previous_vr_experience              BOOLEAN,
    self_rated_attention_difficulty     VARCHAR(32),
    consent_obtained                    BOOLEAN NOT NULL DEFAULT FALSE,
    consent_obtained_at                 TIMESTAMPTZ,
    created_at                          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_participants_external_code ON participants (external_code);

-- ---------------------------------------------------------------------
-- experiment_sessions
-- ---------------------------------------------------------------------
-- S0 - Session Initialization (spec 7.1): participante, condicion,
-- kanji set asignado, seed y versiones para reproducibilidad exacta.

CREATE TABLE experiment_sessions (
    id                             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id                 UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    condition                      experimental_condition NOT NULL,
    status                         session_status NOT NULL DEFAULT 'CREATED',
    current_state                  game_flow_state NOT NULL DEFAULT 'S0_SESSION_INITIALIZATION',
    assigned_kanji_set             VARCHAR(8),
    visit_number                   INTEGER NOT NULL DEFAULT 1,
    random_seed                    VARCHAR(64),
    software_version               VARCHAR(32),
    experiment_config_version      VARCHAR(32),
    controller_config_version      VARCHAR(32),
    session_clock_started_at       TIMESTAMPTZ,
    completed_at                   TIMESTAMPTZ,
    created_at                     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_experiment_sessions_participant_id ON experiment_sessions (participant_id);

-- ---------------------------------------------------------------------
-- session_config_snapshots
-- ---------------------------------------------------------------------
-- SESSION_CREATED: config snapshot completo. JSONB flexible a proposito
-- -- varios parametros siguen "to validate" (spec seccion 16).

CREATE TABLE session_config_snapshots (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id     UUID NOT NULL UNIQUE REFERENCES experiment_sessions(id) ON DELETE CASCADE,
    config         JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- system_validation_events
-- ---------------------------------------------------------------------
-- S3 - EEG & System Validation: conexion WAVEX, latencia Quest-Backend,
-- calidad de señal, clock offset (spec 7.4). `detail` es JSONB porque
-- los umbrales de calidad EEG siguen "to validate".

CREATE TABLE system_validation_events (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id         UUID NOT NULL REFERENCES experiment_sessions(id) ON DELETE CASCADE,
    component          validation_component NOT NULL,
    status             validation_status NOT NULL,
    detail             JSONB NOT NULL DEFAULT '{}'::jsonb,
    client_timestamp   TIMESTAMPTZ,
    received_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_system_validation_events_session_id ON system_validation_events (session_id);

-- ---------------------------------------------------------------------
-- session_events
-- ---------------------------------------------------------------------
-- Event log generico de proposito general (walking skeleton). El
-- vocabulario conductual completo (TRIAL_STARTED, HEAD_AWAY, etc. --
-- spec 11.1) se instrumenta formalmente en Fase 3.

CREATE TABLE session_events (
    id                     BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    session_id             UUID NOT NULL REFERENCES experiment_sessions(id) ON DELETE CASCADE,
    event_type             VARCHAR(64) NOT NULL,
    payload                JSONB NOT NULL DEFAULT '{}'::jsonb,
    client_timestamp       TIMESTAMPTZ,
    server_received_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_session_events_session_id ON session_events (session_id);
CREATE INDEX ix_session_events_event_type ON session_events (event_type);
