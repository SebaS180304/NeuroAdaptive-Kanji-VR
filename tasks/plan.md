# Implementation Plan: S4 EEG Baseline visuals (fixation cross + closing eye)

## Overview
During S4 the board shows only a line of text today (`SessionFlowRunner.RunBaseline`,
`SessionFlowRunner.cs:537`). Change it so the board shows the instruction as the line
above the centre (the trial "question" line) and an icon in the centre:
- **Eyes open (60 s):** a large, static fixation cross.
- **Eyes closed (45 s):** an eye that closes once, then stays closed.

Timing, chimes and the BASELINE_* telemetry do not change.

## Architecture Decisions
- **One new board method, `StudioTrialPresenter.ShowBaseline(string instruction, bool eyesClosed)`.**
  The presenter is the board's only owner (decision D1, 24 Sep), so the icons live there,
  not in a new component. The instruction goes through the existing `SetQuestion()` line
  (`StudioTrialPresenter.cs:1140`); `Clear()` hides the icons so every other board call
  removes them without new code.
- **Cross = two UI `Image` bars**, created lazily the way `CueChip` / `StageChip` are.
  No font glyph: the `+` in Noto Sans is thin and its weight depends on the font.
- **Eye = one procedural texture** (almond outline + iris, made once in code into a
  `Texture2D`) on a `RawImage` via the existing `NewRawImage()` helper. "Closing" animates
  its height (scale Y 1 → ~0.06, ~1 s, ease-in) until it is a thin line, then **holds**.
  No art file to make or import. If Sebas wants designed art, a PNG in
  `Resources/baseline/` replaces the texture; the rest stays the same.
- **No motion during eyes-open, the closing animation plays once and never loops.** The
  60 s eyes-open segment is the EEG reference: anything that moves near fixation adds a
  visual response to it (UI design v1, 7.1: movement near fixation was removed). The eye
  plays once when the closed segment starts, then holds still.
- **No new telemetry.** The segment timing already travels in BASELINE_STARTED/COMPLETED.
  The visual change goes in the progress log (Plan §9) so sessions before and after it
  are not mixed up without a note.

## Dependency graph
```
StudioTrialPresenter.ShowBaseline (+ Clear hides icons)
   ├── cross (Task 1)  ──► SessionFlowRunner.RunBaseline eyes-open call
   └── eye + animation (Task 2) ──► SessionFlowRunner.RunBaseline eyes-closed call
```
Task 2 depends on Task 1 (same method and the same icon slot).

## Task List
See `tasks/todo.md` for full acceptance criteria.

### Phase 1: Fixation cross
- [ ] Task 1: Eyes-open segment shows instruction line + centred fixation cross

### Checkpoint A
- [ ] Compiles, no console errors; S4 in the Editor at `baselineTimeScale` 0.05 shows the cross

### Phase 2: Closing eye
- [ ] Task 2: Eyes-closed segment shows instruction line + eye that closes once and holds

### Checkpoint B (complete)
- [ ] Full S4 in the Editor: cross → eye, chimes on both edges, BASELINE_COMPLETED unchanged
- [ ] Next board state (S5 intro) has no cross or eye left on it
- [ ] Headset look (Quest 2 via Link) at real scale for legibility and size
- [ ] Note in Plan_Fase5a §9; `graphify update .`; commit (message shown first)

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Today (2026-10-16) is the F5a delivery and phase test. A participant-facing S4 change on this branch the same day changes the protocol under test | High | Land it **after** the `phase5a-delivery-2026-10-16` tag, or on its own branch. See Open Questions |
| Animation or flicker during eyes-open contaminates the EEG reference | High | Cross is static; eye animates only at the start of the closed segment, once |
| Participant still watching the eye close adds ~1 s to the closed segment before the eyes actually shut | Low | Same as today (reaction time was already in `eyes_closed_ms`); the eye's 1 s is shorter than the reaction |
| Two-line instruction overflows the question line (80 px high, NoWrap) into the stage chip | Med | Keep each instruction to one line, or move `questionY` only for S4; check in a capture |
| Cross/eye size wrong in the headset (board distance) | Med | Sizes as `[SerializeField]` like the rest of the presenter; tune in the headset look, revert Inspector changes |

## Open Questions
1. **When does this land?** Before or after today's delivery tag? (Recommend: after.)
2. **Instruction wording** (participant-facing). Proposal:
   - open: "Look at the cross and relax."
   - closed: "Close your eyes. Open them at the chime."
3. **Eye art:** procedural texture (proposed) or a designed PNG?
4. Should the board stay completely empty except the icon (no stage chip / progress dots) during S4? Proposal: leave them as they are.
