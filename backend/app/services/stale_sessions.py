"""
Abandoned sessions become ABORTED (migration 0005, abort_stale_sessions()).

The rule lives in the database; this module only runs it: once at startup and
then every 5 minutes, from the app lifespan.
shortcut: an in-process loop because the postgres:16 image has no pg_cron; move
the schedule to pg_cron if the backend stops being always on.
"""

import asyncio
import logging

from sqlalchemy import text

from app.db.base import AsyncSessionLocal

logger = logging.getLogger(__name__)

CHECK_EVERY_S = 300


async def abort_stale_sessions() -> int:
    async with AsyncSessionLocal() as db:
        n = (await db.execute(text("SELECT abort_stale_sessions()"))).scalar_one()
        await db.commit()
    if n:
        logger.info("aborted %d abandoned session(s)", n)
    return n


async def run_forever() -> None:
    while True:
        try:
            await abort_stale_sessions()
        except Exception:  # a DB hiccup must not stop the loop
            logger.exception("abort_stale_sessions failed")
        await asyncio.sleep(CHECK_EVERY_S)
