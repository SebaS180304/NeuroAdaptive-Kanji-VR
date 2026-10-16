# Todo: S4 EEG Baseline visuals

Plan: `tasks/plan.md`. Answer its Open Questions (timing vs. today's delivery, wording) before Task 1.

## [x] Task 1: Eyes-open segment shows the instruction line + centred fixation cross

**Description:** Add `StudioTrialPresenter.ShowBaseline(string instruction, bool eyesClosed)`.
It calls `Clear()`, puts `instruction` on the question line (`SetQuestion`), and for
`eyesClosed == false` shows a large static cross centred where the prompt glyph sits
(two `Image` bars, created lazily like `CueChip`). `Clear()` hides the cross.
`SessionFlowRunner.RunBaseline` calls it for the eyes-open segment instead of `Show(...)`,
keeping the log fallback when `board` is null.

**Acceptance criteria:**
- [x] During eyes-open: instruction above, cross in the centre, nothing else on the board (no cards, hint, feedback)
- [x] The cross does not move, pulse or change colour during the 60 s
- [x] Any later board call (`ShowMessage`, `Present`, `ShowExposure`...) leaves no cross behind

**Verification:**
- [x] Unity compiles, console clean (`Unity_GetConsoleLogs`)
- [x] Phase2TestHarness passes (existing cases; S4 matrix case unchanged)
- [ ] Manual: Play with `baselineTimeScale` 0.05, capture the board during S4 (`Unity_Camera_Capture`); revert the Inspector change

**Dependencies:** None

**Files likely touched:**
- `unity-client/Assets/Scripts/Controllers/StudioTrialPresenter.cs`
- `unity-client/Assets/Scripts/Core/SessionFlowRunner.cs`

**Estimated scope:** Small

## Checkpoint A
- [ ] Compiles, harness green, capture shows the cross
- [ ] Review with Sebas before Task 2

## Task 2: Eyes-closed segment shows the instruction line + an eye that closes once and holds

**Description:** In `ShowBaseline(..., eyesClosed: true)`, hide the cross and show an eye
in the same spot: a procedural almond + iris `Texture2D` (made once) on a `RawImage`
(`NewRawImage`). A coroutine scales it on Y from 1 to ~0.06 over ~1 s (ease-in) and stops;
the eye stays as a closed line until the board changes. `Clear()` stops the coroutine and
hides the eye. `RunBaseline` calls it for the eyes-closed segment, right before the first chime.

**Acceptance criteria:**
- [ ] When the closed segment starts the eye is open, closes in ~1 s, and then does not move
- [ ] The animation never loops or restarts during the 45 s
- [ ] Chimes, segment durations and BASELINE_STARTED/COMPLETED payloads are unchanged
- [ ] After S4 the next board (S5 announcement) has no eye or cross

**Verification:**
- [ ] Unity compiles, console clean; Phase2TestHarness passes
- [ ] Manual: Play with `baselineTimeScale` 0.05, capture at the start and end of the closed segment; check `eyes_open_ms` / `eyes_closed_ms` in BASELINE_COMPLETED
- [ ] Headset (Quest 2 via Link): full S4 at scale 1, cross and eye readable and centred; revert any Inspector tuning, do not save the scene in Play

**Dependencies:** Task 1

**Files likely touched:**
- `unity-client/Assets/Scripts/Controllers/StudioTrialPresenter.cs`
- `unity-client/Assets/Scripts/Core/SessionFlowRunner.cs`

**Estimated scope:** Small

## Checkpoint B: Complete
- [ ] All acceptance criteria met
- [ ] Entry in Plan_Fase5a §9 (S4 visuals changed, from which session on)
- [ ] `graphify update .`
- [ ] Commit per task, message shown to Sebas first, not on main
