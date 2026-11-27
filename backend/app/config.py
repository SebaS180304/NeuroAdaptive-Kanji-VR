"""
Configuracion central del backend (Fase 1 - Foundation & Feasibility).

Todas las variables se leen de entorno / .env. No hay valores secretos
hard-codeados: esto es intencional porque el backend eventualmente correra
en un entorno de investigacion con datos de participantes reales.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Identidad del proyecto ---
    project_name: str = "NeuroAdaptive VR Backend"
    environment: str = "development"  # development | staging | production
    api_version: str = "v1"

    # --- Base de datos ---
    postgres_user: str = "neuroadaptive"
    postgres_password: str = "neuroadaptive_dev_password"
    postgres_db: str = "neuroadaptive_vr"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # --- CORS / Dashboard (se usara desde Fase 7, pero se deja configurable) ---
    cors_allow_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # --- LabRecorder remote control (F4, P9 of D-F6-127) ---
    # Off when empty. In Docker: host.docker.internal, since LabRecorder runs on the PC.
    labrecorder_host: str = ""
    labrecorder_port: int = 22345
    # Where LabRecorder writes, as a path on the PC (it is LabRecorder that writes).
    labrecorder_root: str = ""

    # --- EEG rule live (D-F6-246, D-F6-263) ---
    # "current" = option (1); "nosound" = option (2): task sounds of S6–S8 not trimmed + density control; "ica" =
    # option (3), D-F6-275: the ICA fitted at S6's entry, falling back to (2) by itself (live.Buffer). Read by live.py on
    # the PC and by the backend in Docker from the same backend/.env (EEG_LIVE_RULE); change it only between sessions,
    # then `docker compose up -d backend`: `restart` keeps the container's old env_file values (D-F6-283 (2)).
    # The pilot runs with "ica", falling back to (2) by itself (D-F6-289 (2)).
    eeg_live_rule: Literal["current", "nosound", "ica"] = "current"
    # The live monitor's per-channel figures (M1b, D-F6-265): live.py computes and writes them only when on.
    # EEG_MONITOR_LIVE=true in backend/.env, between sessions, then `docker compose up -d backend` (D-F6-283 (2)).
    # It never changes the epoch cut or any rule.
    eeg_monitor_live: bool = False
    # MI (D-F6-277, D-F6-280, D-F6-297 (4)): the monitor's per-epoch indices for the whole session, read by the backend
    # from eeg_epochs. MONITOR_LIVE_INDICES=true in backend/.env, between sessions, then `docker compose up -d backend`.
    monitor_live_indices: bool = False
    # MI outside S7 (D-F6-308 (3), D-F6-309 (4), D-F6-320): S7 alone in z, a 20 s window in ln outside it. Needs
    # MONITOR_LIVE_INDICES on. MONITOR_INDICES_WINDOW=true in backend/.env, between sessions, then `up -d backend`.
    monitor_indices_window: bool = False
    # TR (D-F6-293 (5), D-F6-301 (5)): the monitor's 8-channel traces, written by live.py every 0.25 s to
    # eeg_trace_bins (last 30 s only). EEG_MONITOR_TRACES=true in backend/.env, between sessions, then
    # `docker compose up -d backend`. Display only: it never changes the epoch cut or any rule.
    eeg_monitor_traces: bool = False

    # WebSocket timeout: uvicorn's --ws-ping-timeout in docker-compose.yml and the Dockerfile.

    @property
    def database_url(self) -> str:
        """URL asincrona (asyncpg) usada por la app en runtime."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """URL sincrona (psycopg2) usada solo por Alembic para migraciones."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
