# Data model

- **Source of truth:** the Alembic migrations in `backend/alembic/versions/` (current head `0023`). Several
  migrations are raw SQL in `backend/alembic/versions/sql/`.
- **`database/schema.sql`:** generated with `pg_dump --schema-only` from the database at the head; its
  header says how to regenerate it after each migration. It holds no rows.
- **Verification SQL** in `database/`: `verify_eeg.sql`, `verify_adaptation.sql`, `verify_projection.sql`,
  `verify_events.sql` and others, all read-only. `autorun` runs four of them after each session.

The main tables, by who writes them:

| Written by | Tables |
| --- | --- |
| the backend, from Unity's events | `participants`, `experiment_sessions`, `session_events`, `session_states`, `trials`, `trial_blocks`, `head_away_episodes`, `adaptation_decisions`, `adaptation_applications`, `kanji_exposures`, `assemblies` … |
| the portal | `kanji_pretest_responses`, the free recall |
| `live.py` and `autorun` (the PC) | `eeg_sessions` (sync, reference, ICA, monitor, heartbeat, `live_vs_xdf`), `eeg_epochs` |

Deleting a participant cascades to its sessions and everything under them. A test participant is deleted
that way, in one transaction, counting the rows before and after.

!!! note "Diagrams"
    The diagrams below are Mermaid. This site is built to open without internet, so they show as text.

## Entity-relationship diagram (`database/ERD.md`)

--8<-- "database/ERD.md"

## Event payload contract (`database/EVENT_CONTRACT.md`)

--8<-- "database/EVENT_CONTRACT.md"
