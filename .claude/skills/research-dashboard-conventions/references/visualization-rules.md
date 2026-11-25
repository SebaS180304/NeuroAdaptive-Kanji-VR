# Visualization rules

The rules are fixed. The **values** (exact colors, sizes) come from
`design-system.md` once it is validated; until then, tokens with `TODO(design)`.

## General

- Every number carries its unit (`ms`, `%`, `s`) and its window when it applies
  ("mean RT, window n=3").
- NULL: `—` + tooltip "Not recorded in this session". In charts, a gap in the
  series, never zero.
- Empty is not the same as not recorded: "No head-away episodes in this session"
  versus "Head-away was not recorded in this session".
- No clinical interpretation in titles, legends or tooltips. `learner_state`
  (`STABLE`, `DISENGAGED`, `OVERLOADED`) is presented as an **estimated state**
  with its confidence, never as a trait of the person.
- Meaning never depends on color alone (shape, pattern or label as well). AA
  contrast. Tested in light and dark.
- Reserved items (Learner Profile, HCI) appear as a grey card or tab reading
  "Available in a later version". Never sample data in production.

## Fixed semantic tokens

| Token | Concept |
| --- | --- |
| `--color-condition-static` / `-behavior` / `-multimodal` | Conditions |
| `--color-trial-correct` / `-incorrect` | Trial result (not answered: a `--color-border-strong` outline, no token of its own) |
| `--color-esl-*` | ESL levels (sequential scale) |
| `--color-lal-*` | LAL levels (a different sequential scale) |
| `--color-state-stable` / `-disengaged` / `-overloaded` | Estimated state |
| `--color-outcome-positive` / `-neutral` / `-negative` / `-uncertain` | Adaptation outcome |
| `--color-headaway` | Head-away |
| `--color-peripheral` / `--color-distractor` | Peripheral events / distractor interactions |
| `--color-lal-high` | Hints (on request vs proactive, told apart by shape: dot vs ring) |
| `--color-reserved` | Reserved slots |
| `--color-quality-ok` / `-warn` / `-error` | Data quality |

## Session timeline

- X axis: `session_elapsed_ms` as `mm:ss`; tooltip as `mm:ss.SSS`.
- Lanes in a fixed order, top to bottom:
  1. Game Flow states
  2. Environment (ESL)
  3. Assistance (LAL)
  4. Trials
  5. Hints
  6. Peripherals and distractors (`DWELL`, `ORIENTING`)
  7. Head-away
  8. Adaptations
- No EEG lane in v1 (decided Oct 16). The lane model must allow adding one later
  without reworking the others.
- States, ESL/LAL intervals, trials and head-away are bars. Hints, peripherals
  and decisions are point marks. Dwells are bars `[onset, onset + duration)`.
- Adaptation: the decision mark sits at `decided_elapsed_ms` and its application
  at `applied_elapsed_ms`, joined by a line. `SKIPPED` gets a different shape and
  its reason in the tooltip. The cooldown is a band up to `cooldown_until_trial`.
  The outcome is a badge on the mark.
- Horizontal zoom and pan. Clicking a trial or a decision selects its row in the
  matching table, and vice versa.
- Handles a full session (~60 trials, hundreds of marks) without lag.

## Tables

- Trials: trial_id, block, type, kanji, ESL, LAL, RT, correct, idle, head-away,
  hints (+ `cue_trigger`), distractors, estimated state, action, result in Unity,
  window aggregates. S2 (`is_primary_analysis = false`) marked and filterable.
- Adaptations: trial, state + cause + confidence, action (dimension from → to),
  explanation (full text, not truncated), result in Unity, cooldown, outcome.
  `indicators`/`thresholds` in an expandable panel.
- Numbers right-aligned in tabular figures. Default order: time.

## Comparisons (F-EXPERIMENT, after the pilot)

- Distributions before bare means (points + box or violin), n visible.
- No significance asterisks: the pilot is exploratory.
