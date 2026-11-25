# Tests

Never during a session: they load the PC.

## Backend: pytest

Inside the container, where the dependencies are:

```powershell
docker compose exec -T -e EEG_LIVE_RULE=current -e EEG_MONITOR_LIVE=false backend python -m pytest -q
```

- About 556 tests (25 Nov 2026).
- Pass the defaults as above. A few `fill_from_xdf` tests read the live rule from the container's
  environment, and fail when `backend/.env` has `ica`.
- The tests use their own fixtures in the database and clean up after themselves.

## Unity: the Editor harness

In the Unity Editor: **Tools › NeuroAdaptive VR › Correr pruebas de Fase 2**
(`unity-client/Assets/Editor/Phase2TestHarness.cs`). It runs the scene's checks in the Editor and prints
PASS or FAIL per case (119 cases in November 2026). Never save the scene during Play.

## Portal: Vitest, type check, lint, build

```powershell
cd dashboard
npm test            # Vitest, about 162 tests
npx tsc -b          # type check
npm run lint        # oxlint
npm run build       # what nginx serves
```

After a backend schema change, regenerate the API types with the backend running: `npm run gen:api`.

## Portal: Playwright

```powershell
cd dashboard
npm run e2e
```

The end-to-end specs are in `dashboard/tests/e2e/`.

## EEG checks on recorded data

- `replay --xdf --rule …` in the container: the same decisions as live (the official ones are the live
  ones).
- `database/verify_eeg.sql` and the other `verify_*.sql`: read-only checks of a session.
- A full simulation of a session replays an XDF over two LSL outlets into `live.py` at 1× (real time),
  with a test participant deleted at the end. At 10× the live-edge effect shows ≈ 5 times smaller.
