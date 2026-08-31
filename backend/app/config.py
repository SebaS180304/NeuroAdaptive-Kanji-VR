"""
Configuracion central del backend (Fase 1 - Foundation & Feasibility).

Todas las variables se leen de entorno / .env. No hay valores secretos
hard-codeados: esto es intencional porque el backend eventualmente correra
en un entorno de investigacion con datos de participantes reales.
"""

from functools import lru_cache

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

    # --- WebSocket / Unity ---
    # Umbral simple para el "walking skeleton" de M1: cuanto tiempo (segundos)
    # toleramos sin recibir un PING de Unity antes de considerar la conexion
    # caida. Los valores reales de latencia tolerada se validan en Fase 1.
    websocket_heartbeat_timeout_seconds: int = 15

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
