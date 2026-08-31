"""
Health check.

Es el primer endpoint que M1 necesita: confirma que el proceso FastAPI
esta arriba y que puede hablar con PostgreSQL, sin depender todavia de
Unity ni de WAVEX.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(text("SELECT 1"))
    return {"status": "ok", "db_result": result.scalar_one()}
