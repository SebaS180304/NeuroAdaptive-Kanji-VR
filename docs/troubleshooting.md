# Troubleshooting

| Symptom | Cause | What to do |
| --- | --- | --- |
| A `.env` change does nothing in the backend | `restart` keeps the container's old environment | `docker compose up -d backend`, then `docker compose exec -T backend env` |
| `live.py` or the recorder: `2 LSL streams named 'UnityMarkers'` (or `AURA`) | an old Unity Editor still publishing, or a second AURA | close and reopen Unity; restart the AURA software; `preflight` says it before Play |
| `autorun` prints `MANUAL: …` | not exactly one `AURA` and one `UnityMarkers` of this PC at Play | record by hand in LabRecorder (Update, the two streams of this PC, Start), same path |
| `preflight` FAIL: a program open | Firefox, VS Code, ChatGPT, Codex or Blender running | close them; they caused frame hitches in the headset |
| `preflight` FAIL: `git status` | uncommitted changes in the repo | commit or stash before the session |
| The `autorun` console is thousands of SQL lines | `ENVIRONMENT=development` | start `autorun` with `$env:ENVIRONMENT='production'` in its window |
| `S3 taps: fewer than 3 clear` | taps too soft or too close | repeat the 5 taps on Cz before S4, each peak seen in the AURA software |
| `WARNING: <channel> looks bad` before S4 | gel or contact | fix it before S4; if it stays bad, the channel is excluded and the session goes on |
| Fp1's 60 Hz far below the other channels in S3 | the headset foam pressing on Fp1, or smeared gel | clean and reseat before S4 |
| `HEAD_AWAY` open in S3 | the headset tilted | reseat the headset and repeat the taps |
| `ICA not identified` at S6 | the eye component did not reach a 0.7 correlation with Fp1 | nothing: the session goes on with rule (2) by design |
| Many epochs differ between the live and the XDF cut | the zero-phase filter edge with a blink-heavy Fp1 | declared; the official figures are the live ones |
| `replay`: `No module named 'psycopg2'` | run on the PC | run it inside the backend container |
| The monitor shows `No data for n s` | `live.py` stopped or the signal cut | check the `autorun` window and the AURA software |
| Frame hitches over 100 ms | load on the PC (Profiler, other programs, monitor switches) | close what is open; switch off the newest monitor switch before the next session |
