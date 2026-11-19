"""
The eeg_sessions row of a session that never reached S3 (D-F6-258 (2), D-F6-260 (1)). It is still written when the
session is created (autorun, AU2's recording and s3watch hang on it); once the session ends (COMPLETED or ABORTED)
without a STATE_ENTERED of S3, there is no EEG to keep, so the row goes: a short visit (S1 → block R → S9, the pilot's
visit 4) leaves none, and verify_eeg.sql does not list an empty one.
"""

import logging

from sqlalchemy import text

from app.db.base import AsyncSessionLocal

logger = logging.getLogger(__name__)

_DROP = text("""
DELETE FROM eeg_sessions e USING experiment_sessions s
WHERE e.session_id = s.id AND s.id = ANY(CAST(:ids AS uuid[])) AND s.status IN ('COMPLETED', 'ABORTED')
  AND NOT EXISTS (SELECT 1 FROM session_events v WHERE v.session_id = s.id AND v.event_type = 'STATE_ENTERED'
                  AND v.payload ->> 'state' = 'S3_SYSTEM_VALIDATION')
RETURNING e.session_id""")


async def drop_rows_without_s3(session_ids) -> int:
    """After the commit that closed the sessions; in its own DB session. Returns how many rows went."""
    if not session_ids:
        return 0
    async with AsyncSessionLocal() as db:
        gone = (await db.execute(_DROP, {"ids": [str(s) for s in session_ids]})).scalars().all()
        await db.commit()
    for sid in gone:
        logger.info("eeg_sessions row of %s deleted: the session ended without S3 (D-F6-260)", sid)
    return len(gone)
