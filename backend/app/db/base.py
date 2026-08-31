"""
Base declarativa y engine asincrono de SQLAlchemy.

Este modulo NO importa los modelos directamente para evitar import
circulares; `app/models/__init__.py` los registra sobre `Base.metadata`,
y `alembic/env.py` importa ese paquete para poder autogenerar migraciones.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Clase base declarativa compartida por todos los modelos ORM."""

    pass
