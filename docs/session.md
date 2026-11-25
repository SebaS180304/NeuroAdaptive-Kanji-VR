# Running a session

The operator kit of each day is written outside the repo, in the development drafts. This page is what
does not change from one day to the next. Participants appear **only by code**.

## Before the session

1. Reopen Unity. Open the AURA software with **LSL Stream Out** on, the portal in Edge and LabRecorder.
   Close Firefox, VS Code, ChatGPT, Codex and Blender (they caused frame hitches). Keep Unity's Profiler
   closed.
2. Switch the network off before the cap goes on (Ethernet and Wi-Fi); on again when `autorun` says
   *both streams recorded*.
3. Run `preflight`:

    ```powershell
    cd backend; .\.venv\Scripts\python.exe -m app.eeg.preflight
    ```

    It checks the backend (`/health`, `/health/db`), the portal, the database port, a clean `git status`,
    one Unity Editor and how long it has been open, the AURA software, Edge and LabRecorder running, the
    programs that must be closed, no `UnityMarkers` before Play, the network, `LabRecorderCLI`, and the
    XDF folder. **No `FAIL` before the cap.**

## autorun

From `backend\`, in its own window, before Play:

```powershell
$env:POSTGRES_HOST='127.0.0.1'; $env:ENVIRONMENT='production'; .venv\Scripts\python -m app.eeg.autorun
```

(`ENVIRONMENT=production` only in that window keeps SQLAlchemy's SQL log out of the console.)

What it prints, in order:

- `waiting for a new session`, then the session id at Play;
- `RECORDING (automatic): AURA + UnityMarkers of <PC> -> <xdf>` (or `MANUAL: <reason>`: record by hand);
- `live: AURA at 250.0 Hz and UnityMarkers; cutting from the end of S3; EEG rule <rule>`;
- S3 warnings (a bad channel, a head turned away) and each sync tap: `tap n/5: clear (peak … uV)`;
- `S3 offset … ms`, the S4 alpha ratio and whether it passes (≥ 1.2);
- at S6, with rule `ica`: `ICA identified (…)`, `ICA not identified (…): option (2) for this session`,
  or `ICA dropped: …`;
- `reference from S6 (n epochs)` (or S4 eyes open as the fallback);
- at S9: live epochs saved, recording stopped, `both streams recorded`, `live vs XDF: k of n epochs
  differ`, then the summary and `exit code 0`.

Save the whole console as `autorun.txt` with the session's export: the official reference of a session
is its `autorun` line plus `backend\logs\<8>-live_epochs.csv`.

After the session, `backend\logs\` holds `<8>-summary.txt`, `<8>-live_epochs.csv`, `<8>-verify_eeg.txt`
and the other verification outputs.

## The live monitor

`http://127.0.0.1:5300/monitor` on the second screen, read-only. It follows the session in progress;
`/monitor/<session id>` pins one. Its panels: signal quality per channel (M1b, when
`EEG_MONITOR_LIVE=true`), live indices (per epoch with `MONITOR_LIVE_INDICES=true`), adaptation
decisions, sync, system and the event console. From S4 to S8 nobody touches the PC.

## After the session

- Wait for `exit code 0` before closing `autorun`. Network back on.
- Export for the EEG analysis without the XDF (the recording never leaves the PC): the session's rows
  read-only, `replay --rule <rule>` in the container, the frame hitches from the XDF, `ocul.py`. The
  scripts of each export sit next to it in the drafts' export folders.
