# Design system · v1 (approved Oct 16)

Alineado hasta: D-F6-272 (`Estado_Actual.md`, Nov 20 2026).

> **Status: v1 design COMPLETE.** Tokens approved Oct 16 2026 (light 23:15, dark
> 23:18). Every screen, V1.1 to V1.11, validated by Oct 17 2026, 00:20 (see the log).
> Implement these exact values. A screen is built only once its mockup appears as
> *Validated* in the log below. Anything not covered here: flag it and ask; do not
> invent a value. If a design needs data the API does not have, the dev chat says
> so instead of faking it.

## Source of truth

- Mockups: Claude Design canvas "Research Dashboard · Wireframes v1",
  `https://claude.ai/artifact/Xh2oJPSpVH8hubWxNZcooL` (artboard names below).
- *Design System* artifact "NeuroAdaptive Research Dashboard" (tokens, README, cover):
  `https://claude.ai/artifact/NBVJKr7iEdfApEAFx1uZ4L`
- Rules these values satisfy: `design-rules.md`.

If this file and the Design System artifact disagree, the artifact wins: update
this file and say so.

## Validation log

Who decides: Sebas validates; the design chat records it here with the date and
the URL. Status *Pending* = do not build the screen yet.

| Screen | Artboard(s) on the canvas | Status | Date |
| --- | --- | --- | --- |
| Tokens (color, type, shape, elevation) | *Tokens: color, type, radius, shadow* | Validated | Oct 16 2026, 23:15 |
| V1.1 Session list | *Session list* | Validated | Oct 16 2026, 23:15 |
| V1.2–V1.4 Session View (summary, timeline, Trials tab) | *Session View* | Validated | Oct 16 2026, 23:15 |
| V1.2–V1.4 Session View, dark | *Session View, dark theme* | Validated | Oct 16 2026, 23:18 |
| V1.5 Adaptations tab | *V1.5 Session View, Adaptations tab* and its dark artboard | Validated | Oct 17 2026, 00:08 |
| V1.6 Plan and execution tab | *V1.6 Session View, Plan and execution tab* and its dark artboard | Validated | Oct 17 2026, 00:08 |
| V1.7 Data quality | *V1.7 Data quality* (Tweaks: `noErrors`), dark variant | Validated; revised from real data and re-validated | Oct 17 2026, 00:02; Oct 19 2026, 23:54 |
| V1.8 Participant View (without the profile) | *Superseded Oct 21: V1.8 Participant View …* and its dark artboard, moved to the "Superseded" zone of the canvas | **Superseded** (D-F6-16): replaced by *V1.8 Participant View · Learner Profile*; do not build from it | Validated Oct 17 and Oct 19; superseded Oct 21 2026, 20:11 |
| V1.10 Kanji pre-test | *V1.10 …* row (pick, register, one kanji, complete, states) and its dark row; summary without substitutions (Sebas, Oct 16, 23:57) | Validated | Oct 17 2026, 00:02 |
| V1.11 Participant list (needs a scope entry from the dev chat) | *V1.11 Participant list (proposed)* and its dark artboard | Validated | Oct 17 2026, 00:20 |
| F-PROFILE Learner Profile at the top of V1.8 | *V1.8 Participant View · Learner Profile* (Tweaks: `noSessions`, `oneSession`, `staticOnly`, `noChanges`, `manySessions`) and its dark artboard | Validated | Oct 21 2026, 14:14 |
| F-PROFILE: "See [n] decisions in [k] sessions" and the V1.5 group filter | Learner Profile (`manySessions`) and V1.5 (`groupFilter`) artboards, canvas version 38 | Validated | Oct 21 2026, 18:22 |
| F-PROFILE: aborted sessions never mentioned (scope line without the "[m] aborted…" clause) | same artboard, canvas version 39 | Validated | Oct 21 2026, 18:22 |
| F-PROFILE: "Not recorded" outcome badge (D-F6-8, D-F6-16) | Learner Profile artboard, Tweak `manySessions`, second group, canvas version 41 | Validated (D-F6-96; validated by Sebas on the canvas, recorded Oct 26 with no date noted) | Recorded Oct 26 2026, 17:00 |
| Estimated state `UNDERCHALLENGED`: color `--color-state-underchallenged` (D-F6-81) | *Tokens* artboard, "Estimated state" row, canvas version 42 | Defined by the design chat (D-F6-81: design web defines the color); shown to Sebas | Oct 26 2026, 16:45 |
| F-PROFILE: canvas-only form written here (D-F6-11; the 12 form points of the dev chat's Task 11a-fix) | same artboards, canvas 30, 38 and 39; no new drawing | Recorded, nothing new to validate | Oct 21 2026, 19:40 |
| Brand: andon icon, favicon, rail header, logo, covers (D-F6-117, D-F6-120, D-F6-121) | *Brand (D-F6-120): Andon_icono_E vector …*, canvas version 47 (round 2: oval light and two rods) | Validated; kept as is after the Google Lens match with Semibot (D-F6-121) | Oct 30 2026 |
| V1.12 Block R: free recall form (D-F6-125, D-F6-208, D-F6-225, D-F6-226) | *V1.12 Block R · Free recall* (Tweak `state`: `marking`, `saved`, `nothingRecalled`, `saveError`) and its dark artboard; files `BlockRRecall.dc.html` and `BlockRRecallDark.dc.html` | **Validated** (D-F6-226) by Sebas (from the states sheet and the artboard files in `design-handoff/block-r/`; on the canvas since Nov 17, 16:38, canvas version 51, right of "Brand"). The dev chat replaces its placeholder form with this one (D-F6-208, D-F6-223 (3)). *What counts* fixed by D-F6-225 | Proposed Nov 16 2026; validated Nov 17 2026, 14:37 |
| V1.13 Live session monitor (D-F6-231, D-F6-233, D-F6-234): read-only second screen, 1440 × 900, no scroll | *V1.13 Live session monitor* (Tweak `state`: `normal`, `channelWatch`, `channelExcluded`, `mains60`, `syncTap`, `sourceCut`, `notCounted`, `beforeS7`, `sessionEnded`, `noSession`) and its dark artboard; files `LiveSessionMonitor.dc.html` and `LiveSessionMonitorDark.dc.html` in `design-handoff/monitor/`, with the states sheets | **Validated** (D-F6-233) by Sebas, ahead of the Thu 19 date of D-F6-231 (5). On the canvas since Nov 17, 16:38 (canvas version 51, right of V1.12). Built in M1, during the pilot (D-F6-231 (5)). Low / Normal / High bands in *Live indices* added by **D-F6-234** (the engine's thresholds; two new Tweak states, `notCounted` and `beforeS7`); canvas version updated the same day. **D-F6-270** completes it with what is already built: the session-ended state (`sessionEnded`), the «Sync tap» mark (`syncTap`, D-F6-254 (2)) and «—» on the `autorun` row (D-F6-267). The two new states are **Validated (D-F6-272)** (canvas versions 70 and 71) | Proposed Nov 17 2026; validated Nov 17 2026, 17:04; bands Nov 17 2026, 17:40; D-F6-270 Nov 20 2026, 15:05; validated (D-F6-272) Nov 20 2026, ≈ 15:20 |
| V1.13 access: rail entry and session link (D-F6-268, D-F6-270, D-F6-272) | *V1.13 access: rail entry and session link* and its dark artboard, canvas x 16720 (files `MonitorAccess.dc.html`, `MonitorAccessDark.dc.html` and `Accesos_monitor_claro.png` / `_oscuro.png` in `design-handoff/monitor/`) | **Validated (D-F6-272)** by Sebas, as drawn. D-F6-270 confirms the window of each way in, Export CSV hidden while `IN_PROGRESS` and the one rule for several running sessions. Labels and tooltips from `Contenido_UI_Monitor_Accesos.md` (UI/UX, aligned to D-F6-270). Built in the portal only, outside sessions with the cap, inside the gate of D-F6-271 | Proposed Nov 20 2026, 14:45; validated Nov 20 2026, ≈ 15:20 |

All artboards: `https://claude.ai/artifact/Xh2oJPSpVH8hubWxNZcooL`.

## Visual direction

A lab notebook with a SaaS frame. A session reads like a report that rebuilds
what happened: an editorial serif for headings, a plain sans for data, and one
memorable element, the timeline, where each system decision is tied to its
cooldown. Everything else stays quiet. Dense where analysis happens (timeline,
tables), roomy around it.

Structural numbers come from the reference analysis of Oct 16: IBM Carbon (16
columns, 32 px gutter, 8 px mini unit, small-size tracking), Vercel (negative
display tracking ≈ −2 % of size), Stripe (pill buttons with near-square panels,
layered shadows). Their palettes and faces were not taken.

## Color tokens

Every color is a CSS variable. Light is the default; dark is applied with
`[data-theme="dark"]` and `prefers-color-scheme: dark` (unless
`[data-theme="light"]`).

### Base

| Token | Light | Dark | Use |
| --- | --- | --- | --- |
| `--color-bg` | `#F9F8F6` (Paper) | `#0F1115` (Night) | Page ground |
| `--color-surface` | `#FFFFFF` | `#181B21` | Panels, tables, inputs |
| `--color-surface-raised` | `#FFFFFF` | `#1E222A` | Inspector, popovers |
| `--color-sidebar` | `#14171C` | `#08090C` | Navigation rail |
| `--color-sidebar-text` | `#ECEAE5` | `#ECEAE5` | Rail text |
| `--color-sidebar-muted` | `#9AA0A8` | `#9AA0A8` | Rail secondary text |
| `--color-text` | `#14171C` (Ink) | `#ECEAE5` | Main text |
| `--color-text-secondary` | `#2E333A` | `#C9CDD2` | Running text, sentences |
| `--color-text-muted` | `#565B62` (Slate) | `#9AA0A8` | Labels, captions, units |
| `--color-border` | `#E4E2DD` | `#262A31` | Panel borders, table rules |
| `--color-border-subtle` | `#EFEDE8` | `#1F232A` | Row rules, lane rules, bar tracks |
| `--color-border-strong` | `#8A8F96` | `#70767D` | Inputs, outline buttons, dashed chips. At least 3:1 on every surface (light 3.3:1 on white, 3.1:1 on Paper; dark 3.8:1 on surface, 3.5:1 on raised). Corrected Oct 18: the old `#C9CDD2` / `#3A3F47` measured 1.6:1 |
| `--color-accent` | `#0B6A73` (Lagoon) | `#3FB7C2` | Active nav, links, focus, tabs, decisions |
| `--color-accent-hover` | `#084F56` | `#7FD3DB` | Link hover |
| `--color-on-accent` | `#FFFFFF` | `#0F1115` | Text on accent fill |
| `--color-accent-tint` | `#DCEBEC` | `#123A3F` | Chips, cooldown band, selected toggle |
| `--color-on-accent-tint` | `#0B4F56` | `#8FDDE4` | Text on accent tint |
| `--color-selected-row` | `#E8F2F3` | `#14343A` | Selected table row |
| `--color-explain-bg` | `#F3F8F8` | `#132A2E` | "Why the system changed" box |
| `--color-cta` | `#F2A93B` (Saffron) | `#F2A93B` | Primary action (Export CSV); the only token equal in both themes |
| `--color-on-cta` | `#14171C` | `#0F1115` | Text on CTA |
| `--color-alert` | `#B83A22` (Vermilion) | `#E5694F` | Errors, negative outcome, incorrect trial |
| `--color-alert-tint` | `#F4D9D2` | `#3A1F19` | Hatch partner for incorrect trials; error notice background |
| `--color-on-alert-tint` | `#8A2A18` | `#F4B3A4` | Text and icons on the alert tint (6.5:1 light, 8.5:1 dark) |
| `--color-warn-tint` | `#FBEBCF` | `#3A2E17` | Warning and inclusion notices (same value as `--color-lal-low`) |
| `--color-on-dark-border` | `#6B7178` | `#6B7178` | Outline buttons on the rail, the researcher strip and the registration bar (3:1 or more) |

### Data

| Token | Light | Dark | Use |
| --- | --- | --- | --- |
| `--color-esl-low` | `#DCEBEC` | `#123A3F` | ESL low |
| `--color-esl-medium` | `#8DBFC4` | `#1F6870` | ESL medium |
| `--color-esl-high` | `#0B6A73` | `#3FB7C2` | ESL high |
| `--color-lal-low` | `#FBEBCF` | `#3A2E17` | LAL low |
| `--color-lal-medium` | `#F2C46D` | `#7A5719` | LAL medium |
| `--color-lal-high` | `#9A6414` | `#F2C46D` | LAL high; also hints and "change assistance" |
| `--color-trial-correct` | `#2E333A` | `#C9CDD2` | Correct trial bar |
| `--color-trial-incorrect` | hatch `--color-alert` / `--color-alert-tint`, 45°, 2 px | same | Incorrect trial |
| `--color-condition-static` | `#8E9399` | `#6B7178` | Static |
| `--color-condition-behavior` | `#0B6A73` | `#3FB7C2` | Behavior-adaptive |
| `--color-condition-multimodal` | `#9A6414` | `#F2C46D` | Multimodal-adaptive (border of its chip, marks) |
| `--color-condition-multimodal-tint` | `#FBEBCF` | `#3A2E17` | Multimodal-adaptive chip fill |
| `--color-on-condition-multimodal-tint` | `#6E4F17` | `#F2C46D` | Multimodal-adaptive chip text (6.4:1 light, 8.1:1 dark) |
| `--color-state-stable` | `#0B6A73` | `#3FB7C2` | Estimated state: stable |
| `--color-state-disengaged` | `#9A6414` | `#F2C46D` | Estimated state: disengaged |
| `--color-state-overloaded` | `#B83A22` | `#E5694F` | Estimated state: overloaded |
| `--color-state-underchallenged` | `#565B62` | `#9AA0A8` | Estimated state: `UNDERCHALLENGED`, label "Low challenge (estimated)" (D-F6-59, D-F6-81; Oct 26). Slate on purpose: it is not a state the system rescues, and it must not read as a variant of Stable. 6.9:1 on white, 6.4:1 on Paper; dark 6.5:1 on surface. Same 10 px dot as the other states, always with its label; the enum goes in the tooltip. Replaces the provisional neutral color in `EstimatedState` |
| `--color-outcome-positive` | `#0B6A73` | `#3FB7C2` | Outcome positive |
| `--color-outcome-neutral` | `#C9CDD2` | `#3A3F47` | Outcome neutral (a fill read with its legend, not a control border; own values since Oct 18) |
| `--color-outcome-negative` | `#B83A22` | `#E5694F` | Outcome negative |
| `--color-outcome-uncertain` | hatch `--color-text-muted` on surface, 45°, 1 px / 5 px | same | Outcome uncertain |
| `--color-headaway` | `#565B62` | `#9AA0A8` | Head-away bars |
| `--color-peripheral` | `#565B62` | `#9AA0A8` | Peripheral event ticks |
| `--color-distractor` | `#8E9399` | `#6B7178` | Dwell bars |
| `--color-state-neutral` | `#E4E2DD` | `#262A31` | Game Flow state bars (S7 uses `--color-text`) |
| `--color-reserved` | `--color-border-subtle` + dashed `--color-border-strong` | same | Reserved slots |
| `--color-quality-ok` / `-warn` / `-error` | `#0B6A73` / `#9A6414` / `#B83A22` | `#3FB7C2` / `#F2C46D` / `#E5694F` | Data quality dots |

Text on data fills: light text on low and medium levels, `--color-bg` (Night or
Ink) on high. Hatch patterns are the only gradient-like fills allowed.

Measured contrast (WCAG): Ink on Paper 16.9:1; Slate on Paper 6.4:1; Lagoon on
Paper 5.9:1; Ink on Saffron 9.0:1; dark text on surface 14.4:1; dark muted on
surface 6.5:1; dark chip 8.0:1; dark active nav 7.9:1; label on dark ESL medium
5.3:1; on dark LAL medium 5.5:1.

## Typography

Families (bundled locally in the build, no runtime Google Fonts):

- **Newsreader** 500 (optical size axis on): headings only.
- **Public Sans** 400 / 500 / 600: body, UI, numbers. `font-variant-numeric:
  tabular-nums` on the app root.
- **JetBrains Mono** 400: trial and session IDs, participant codes, error codes,
  file names, timestamps, axis ticks. Nowhere else.
- **Noto Serif JP** 500: kanji characters only (pre-test, tables that show kanji).

| Token | Family | Size / line height | Letter-spacing | Weight | Use |
| --- | --- | --- | --- | --- | --- |
| `display` | Newsreader | 36 / 40 px | −0.72 px | 500 | Page title |
| `title` | Newsreader | 22 / 28 px | −0.22 px | 500 | Section and panel titles, product name |
| `subtitle` | Newsreader | 18 / 24 px | −0.18 px | 500 | Inspector groups |
| `lead` | Public Sans | 16 / 24 px | 0 | 400 | Summary sentence under the title |
| `figure` | Public Sans | 24 / 32 px | −0.24 px | 600 | Key figures |
| `body` | Public Sans | 14 / 20 px | +0.16 px | 400 | Default |
| `body-strong` | Public Sans | 14 / 20 px | +0.16 px | 500–600 | Lane labels, active tab |
| `caption` | Public Sans | 12 / 16 px | +0.32 px | 400 | Labels, units, notes, table headers |
| `mono` | JetBrains Mono | 12 / 16 px | 0 | 400 | IDs, times |
| `mono-title` | JetBrains Mono | 30 px (in display), 18 px (in title) | −0.6 px / 0 | 400 | IDs inside headings |
| `kanji-display` | Noto Serif JP | 176 / 192 px | 0 | 500 | The kanji on the pre-test screen |
| `kanji-inline` | Noto Serif JP | 20–24 px | 0 | 500 | Kanji inside tables and sentences |

Sentence case everywhere. No all-caps labels.

## Layout and spacing

- Mini unit 8 px. Spacing scale: 4, 8, 16, 24, 32, 48, 64 px.
- Shell: navigation rail 240 px; main area padding 32 px sides, 32 px top,
  64 px bottom.
- Main area grid: `repeat(16, minmax(0, 1fr))`, column gap 32 px, row gap 48 px
  (Session View) / 32 px (lists).
- Session View spans:
  - title block 1–10, session facts 11–16;
  - "Where the time went" 1–10, Adaptations 11–16;
  - Timeline 1–16;
  - tables 1–11, inspector 12–16.
- Panel padding 24 px. Table cell padding 0 16 px; row height 40 px (Session
  View tables) / 48 px (session list); header row 40 px.
- Timeline: label column 184 px; Game Flow lane 40 px, other lanes 32 px; bars
  16 px tall (Game Flow 24 px), 8 px from the lane top.
- Timeline marks beyond the three levels (decided Oct 19 2026, from real data;
  drawn on the Tokens artboard). No new tokens; every mark has its name on it
  or in the legend, never color alone:
  - **ESL MINIMAL (S3) and BASELINE (S4)**: protocol states, not experimental
    levels. Fill `--color-state-neutral`, name on the bar ("Minimal",
    "Baseline") in `--color-text`. The dev chat's treatment is confirmed.
  - **ESL FOCUS (S8)**: the same ESL mechanism at zero props and zero peripheral
    events (spec §7.9), so it stays on the Lagoon scale, below low. Fill
    `--color-surface`, 1 px inside border `--color-esl-high`, name "Focus".
  - **LAL OFF**: no assistance, not a level. No bar: a 1 px `--color-border-strong`
    line through the middle of the bar slot, with "Off" in 12 px
    `--color-text-muted` at the start of each run at least 48 px wide.
    This keeps OFF (recorded, no assistance) distinct from a gap (nothing
    recorded), which has no line.
  - **Trial not answered**: 1 px solid `--color-border-strong` outline, no fill.
  - **Trial not completed (session ended)**: 1 px dashed `--color-border-strong`
    outline, no fill. Dashed means incomplete across the dashboard.
  - Trial legend, in this order: "Correct", "Incorrect", "Not answered",
    "Not completed (session ended)". If the API can't tell the last two apart,
    draw the solid outline and use one entry, "Not answered or not completed".
- Lanes 5–8 marks (decided Oct 19 2026, drawn on the Tokens artboard). They
  follow the outcome-chip shape language; every one is in the legend:
  - **Hints**: requested hint, 8 px dot filled `--color-lal-high`; proactive cue,
    the same dot as a 2 px `--color-lal-high` ring, no fill.
  - **Peripherals**: event tick 2×8 px `--color-peripheral` in the upper half of
    the slot; orienting tick 2×8 px `--color-distractor` in the lower half; dwell
    bar 4 px tall at the bottom. Position separates them, not only color.
  - **Head-away with no return before the session ended**: 1 px dashed
    `--color-headaway` outline, no fill, running to the session end. Tooltip:
    "No return recorded before the session ended".
  - **Decision Unity never answered**: the skipped diamond with a 2 px dashed
    border. Tooltip: "No answer from Unity recorded".
  - **Decision → Unity's answer**: 1 px `--color-accent` line from the diamond to
    the applied or skipped time, ending in a 2×12 px `--color-accent` tick. No
    line when there is no answer.
  - **Outcome badge**: 6 px, at the diamond's upper right with a 1 px
    `--color-surface` ring so it separates from the diamond. Positive: filled
    circle `--color-outcome-positive`. Neutral: circle outlined
    `--color-text-muted`. Negative: filled square `--color-outcome-negative`.
    Uncertain: square outlined `--color-text-muted` (the chip's hatch is
    unreadable at 6 px). Not recorded: no badge, and the tooltip says
    "Outcome: not recorded" (the row in V1.5 shows the dashed chip).
  - **Legend**: lists every mark, not only the levels and trials. It sits in the
    `caption`, grouped by lane in lane order and wrapping to as many lines as it
    needs; tooltips repeat it but don't replace it, because tooltips don't show
    in screenshots or exports.
  - **Lane labels**: lanes stay 32 px. Label 14/16 px, hint 12/16 px, no gap,
    vertically centered (the artboards were corrected to this on Oct 19).
- Range buttons "Whole session" / "Only S7": the button whose range matches the
  current view takes the accent-tint pressed style and `aria-pressed="true"`.
  After a free zoom or pan, neither is pressed; that is intended. Pressing one
  again restores its range.
- Target width: lab monitor ≥ 1440 px. Below 1056 px the 16-column spans
  collapse to full width in source order; tables and timeline scroll inside
  their own box.

## Shape

| Token | Value | Use |
| --- | --- | --- |
| `--radius-panel` | 2 px | Panels, explanation box, swatches |
| `--radius-table` | 0 | Tables and their rows |
| `--radius-input` | 4 px | Inputs, selects, inspector |
| `--radius-pill` | 9999 px | Buttons, chips, nav items, status dots |
| `--radius-bar` | 1 px | Data bars and tracks |

Decision marks are 12 px squares rotated 45°: filled = applied, 2 px outline =
skipped by Unity.

## Elevation

Only the inspector and popovers are elevated. Everything else is flat with a
1 px border.

- Light: `0 1px 1px rgba(20,23,28,0.04), 0 4px 8px -2px rgba(20,23,28,0.06),
  0 16px 32px -12px rgba(11,106,115,0.16)` on `--color-surface-raised`.
- Dark: `inset 0 1px 0 rgba(236,234,229,0.05), 0 4px 8px -2px rgba(0,0,0,0.28),
  0 16px 32px -12px rgba(0,0,0,0.36)` on `#1E222A`. Elevation reads mainly from
  the lighter surface.

No blur, no glass, no glow.

## Components

| Component | Base | Spec |
| --- | --- | --- |
| Navigation rail | custom | `--color-sidebar`; items 40 px pills; active = accent fill + `--color-on-accent` |
| Page header | custom | Breadcrumb (`caption`, link), `display` title with mono ID, `lead` summary sentence built from data |
| Session facts | `<dl>` | 120 px label column, `body`; quality dot 8 px |
| Condition chip | `badge` | 32 px (header) / 24 px (tables), pill. Static: border-subtle fill + text-secondary. Behavior-adaptive: accent tint + on-accent-tint. Multimodal-adaptive (Oct 18): multimodal tint fill, multimodal text and a 1 px `--color-condition-multimodal` border, so it never reads as a warning notice. All three are drawn on the *Tokens* artboard. There is no "Unknown" chip (removed Oct 20): every session has a condition in the database, including sessions that are not projected, so the chip always shows the real condition |
| Primary button | `button` | 32 px, pill, `--color-cta`, `--color-on-cta`, 600 |
| Secondary button | `button` | 32–40 px, pill, 1 px `--color-border-strong`, surface |
| Toggle chip (selected) | `toggle` | 32 px pill, accent tint, 1 px accent border |
| "Where the time went" | custom | State strip 32 px (S7 in `--color-text`), then 4 / 6 split: accuracy figure + sentence, behavior table |
| Adaptations block | custom | 2 px top rule in `--color-text`; action rows 160 px label + 8 px bar + count; outcome bar 16 px segmented |
| Timeline | custom (ECharts) | Lane spec above; cursor 2 px `--color-text`; legend in `caption` |
| Tabs | `tabs` | 48 px, 2 px accent underline on active |
| Data table | `data-table` | `caption` headers, `body` cells, numbers right-aligned, IDs mono; selected row = `--color-selected-row`, ID weight 500 |
| Inspector | custom | Raised surface, radius 4 px, padding 24 px, `subtitle` groups, `<dl>` rows; explanation box with `--color-explain-bg` |
| Reserved slot | custom | Sentence in `caption`: "[Thing]: available in a later version." |
| Filters | `input`, `select` | 40 px, radius 4 px, label above in `caption` |

## Trials tab and inspector (V1.4): cases from real data

Decided Oct 19 2026, after the dev chat built V1.4 against session a5748886.

- **NO_CHANGE decision**: box titled "Why the system made no change", with the
  explanation, "Estimated state" (with confidence) and "Change: None". No In
  Unity, Cooldown until or Outcome rows. Because most S7 trials end this way, it
  is quieter than the change box: `--color-surface-raised` fill with a 1 px
  `--color-border` outline, no `--color-explain-bg`. The tinted box stays for
  real changes, so they stand out when stepping through trials.
- **Trial with no decision**: one `body` line in `--color-text-muted` where the
  box would be: "No decision recorded after this trial." In a static session:
  "Static session: the system makes no decisions."
- **Nothing selected**: the inspector keeps its width and shows, at its top,
  "Select a trial in the table or the timeline to see its details." in
  `--color-text-muted`. The table doesn't reflow when a trial is selected.
- **Tutorial tag (S2 rows)**: 12/16 px pill, `--color-state-neutral` fill,
  `--color-text-secondary` text, no border. Not dashed: dashed means
  incomplete or unknown across the dashboard.
- **Hints column**: the requested-hint count, then, when the trial started with
  the proactive cue, the timeline's 8 px `--color-lal-high` ring after it with
  the accessible name "proactive cue" (visually hidden text). The column
  header's tooltip and the timeline legend explain the ring.
- **Answer column**: the same words as the timeline legend: "Correct",
  "Incorrect", "Not answered", "Not completed (session ended)". A timeout is a
  "Not answered" whose tooltip says "Timed out".
- **Indicators and thresholds in the inspector**: stacked, as built. A caption
  line with the reason code, estimator and rules versions (mono), then
  "Indicators" and "Thresholds" as `caption` headings over key-value lists.
  Keys in mono, nested keys dotted (`rules.cooldown_trials`), allowed to break
  after a dot. Scalar values right-aligned; arrays and objects shown as JSON in
  mono on their own line under the key, left-aligned. The button reads "Hide
  indicators and thresholds" when open.
- **Key-value lists**: labels take their natural width, values take the rest,
  right-aligned and wrapping; trial ids never break (confirmed).
- **Table width**: the 12 columns may scroll sideways inside the 1–11 panel at
  1440 px, but the trial id column is sticky on the left so the row can always
  be identified and selected.
- **Kanji in the table**: 20 px Noto Serif JP (`kanji-inline`), confirmed.

## Session View tabs V1.5 and V1.6

Validated by Sebas on Oct 17 2026, 00:08.

- **Adaptations (V1.5)**: the tables panel spans all 16 columns (no inspector).
  - Columns: expand button, after trial (mono), estimated state (10 px dot in
    its state token + label), cause, confidence, change (dimension and from/to
    in words), in Unity (applied before … / skipped: reason), cooldown until
    (mono), outcome chip.
  - Outcome chips need a shape as well as color:
    - Positive: accent tint, solid dot.
    - Neutral: border-subtle fill, outline dot.
    - Negative: alert tint, square.
    - Uncertain: surface with a hatched square.
    - Not recorded: dashed outline.
  - "Show decisions with no change" checkbox, off by default.
  - The expanded row uses `--color-explain-bg`. It shows the full explanation
    and the reason code with estimator and rules versions on the left, and
    indicators and thresholds as two key-value lists (keys in mono) on the
    right.
- **Plan and execution (V1.6)**: table 1–11, side note 12–16.
  - One row per block (S2, S5, S6, S7, S8). Each row has a strip of 14 px
    squares, one per planned trial:
    - Completed: solid `--color-trial-correct`.
    - Started, not completed: hatch.
    - Never shown: outline `--color-distractor`.
  - Then the planned, started and completed counts, the block seed (mono) and
    the min lag (achieved / requested).
  - A block that was cut gets the row fill `--color-warn-tint`.
  - The side note "Where the session stopped" has a 2 px top rule. It gives one
    sentence naming the last completed trial, a `<dl>` with the last state,
    status and kanji set, and a caption.

## V1.7 and V1.8: cases from real data

Decided Oct 19 2026 (23:45 questions), from the Oct 19 data. Validated by
Sebas on Oct 19 2026, 23:54, on the redrawn artboards (canvas version 27):
*V1.7 Data quality* (Tweak `noErrors` shows the empty state) and *V1.8
Participant View*, both with dark variants.

### V1.8 Participant View

> Superseded in part (D-F6-16): the page layout, the header and the trend chart
> now follow "V1.8 Learner Profile (F-PROFILE)" below. The rules here still
> apply to the status words, the sessions fact, the head-away column, the
> pre-test lead sentences and the notes.

- **Trend x-axis**: session order by start time, not `visit_number`. Ticks are the
  session numbers from the table, with the date in the tooltip, plus the visit
  number when it is above 1.
  - Only COMPLETED sessions are drawn (decided by Sebas, Oct 19): filled
    points joined by a 1 px line in `--color-border-strong`. ABORTED, CREATED
    and IN_PROGRESS sessions stay out of the chart; the table lists them and
    the facts count them. The ticks use the session's number in the table
    ("1, 2, 4, 5, 6" when session 3 was aborted), evenly spaced; axis title
    "Completed sessions, numbered as in the table".
  - With more than 12 sessions the chart keeps its width: ticks every 5, points
    6 px, no point labels. Only test participants such as DEV_UNITY reach that.
- **Point shape by condition** (shape + color, never color alone):
  - Static: square, `--color-condition-static`.
  - Behavior-adaptive: circle, `--color-condition-behavior`.
  - Multimodal-adaptive: triangle, `--color-condition-multimodal`.
  - No Unknown shape (dropped Oct 20): every session has a condition in the
    database, and the chart only draws completed, projected sessions.
  - No diamonds: the diamond belongs to timeline decisions. The latest session
    keeps its condition's shape and gets a "Latest" text label beside it.
  - The legend lists only the conditions present, then the caption
    "Completed sessions only; aborted ones are listed in the table below."
- **Y axes**: accuracy from 0 to 100 %, gridlines at 0, 25, 50, 75 and 100.
  Response time in ms from 0, top at the next round value above the largest
  mean (500 ms steps), 4 or 5 gridlines.
- **Session status words** (decided Oct 20; one shared rule for the V1.1 list and
  the V1.8 "Sessions in order" table, so reuse one component). Plain text in
  `--color-text`, no chip and no color; the condition column already carries
  chips.
  - COMPLETED: "Completed".
  - ABORTED: "Aborted in [state]" with the last state reached (e.g. "Aborted
    in S7"); just "Aborted" when the last state isn't recorded.
  - IN_PROGRESS: "In progress".
  - CREATED: "Not started". The V1.1 status filter uses the same four words.
  - V1.1 keeps "Not projected" for sessions without projection, as drawn.
- **Sessions fact**: "[n] completed, [n] aborted", then ", [n] in progress"
  (IN_PROGRESS) and ", [n] not started" (CREATED), each only when above 0.
- **Head-away column**: episode count, then the total time in
  `--color-text-muted`: "3 (12.4 s)". "—" when not recorded, never 0.
- **Lead sentence**, by case (completed Oct 20 from the dev chat's cases):
  - All sessions after the pre-test, nothing replaced: "Every session used the
    kanji set confirmed by the pre-test. No kanji needed replacing."
  - All after, with replacements: "Every session used the kanji set confirmed
    by the pre-test, with [n] kanji replaced."
  - Some sessions before the pre-test: "[n] of [n] sessions were recorded
    before the pre-test and used the default set. Later sessions used the
    confirmed set" + ", with [n] kanji replaced." when [n] > 0, else ".".
  - Every session before the pre-test: "All [n] sessions were recorded before
    the pre-test and used the default set." ("The only session was recorded
    before the pre-test and used the default set." when there is one.) No
    sentence about later sessions.
  - Pre-test not started: "The pre-test hasn't been started. Sessions use the
    default kanji set until it is completed." with the "Open the pre-test"
    action.
  - Pre-test in progress: "The pre-test is in progress ([n] kanji answered).
    Sessions use the default set until it is completed." The pre-test has no
    fixed length (each known kanji pulls in reserve kanji), so no total.
  - Pre-test completed, no sessions yet: "The pre-test is complete, with [n]
    kanji replaced. No sessions recorded yet." or, with none replaced, "The
    pre-test is complete and no kanji needed replacing. No sessions recorded
    yet."
  - Pre-test not started or in progress, no sessions yet: that case's first
    sentence, then "No sessions recorded yet." in place of "Sessions use the
    default set until it is completed."
- **Notes in the facts**: the same notes and component as V1.11 (warn icon +
  text), plus "[n] sessions recorded before the pre-test" when that applies.

### V1.7 Data quality

- **Lead sentence**: no fixed date. "[n] of [n] projected sessions have no open
  errors and pass every check. [n] sessions are not projected; they are listed
  at the end."
- **Sessions not projected**: a fourth section, last on the page, "Sessions
  not projected": a table with session (mono link), participant, recorded,
  status in words ("Not projected", "No events recorded" for NO_DATA) and the
  reason when the API has one ("—" otherwise). Same table style as "Errors to
  resolve". When there are none, the section is one muted line: "Every
  recorded session is projected."
- **Open errors by code**: always the 5 known codes, in a fixed order; a code
  with no open errors shows an empty track and "0". A code outside the five is
  appended at the end. Under the bars, always: "[n] resolved by
  re-projection so far" in `caption`.
- **Empty state**: with no open errors the bars stay (all at 0) and "Errors to
  resolve" replaces its table with one line: "No errors to resolve. [n]
  resolved by re-projection so far."
- **Many open errors**: paged, 50 rows a page, with "Showing 1–50 of [n]" and
  previous / next under the table. The code filter applies before paging.
- **Needs review**: the check row expands, as in V1.5, using
  `--color-explain-bg`. The expanded row lists the affected sessions (mono
  link to the Session View) with the discrepancy detail for each, 10 at a
  time with "Show all [n]".
- **Check names**: the function name without its suffix, in mono:
  `verify_trials`, not `verify_trials_fn` or a file name.

## V1.8 Learner Profile (F-PROFILE)

Drawn Oct 21 2026; **validated by Sebas on Oct 21 2026, 14:14** (canvas
version 30, light and dark, all six states). Copy comes
from `Contenido_UI_F-PROFILE.md` (UI/UX chat); this section only fixes the form.

- **Place**: the profile is the first section of V1.8, right after the header,
  and fits above the fold at 1440 × 900 for real participants (default case
  ends at y ≈ 897). The header keeps the breadcrumb and title; the condition
  chips and the sessions fact move to its right (11–16). The pre-test sentence,
  facts, notes, substitutions and "Sessions in order" follow below the profile.
- **Open decision 1 (validated)**: the profile's "Across sessions" block
  replaces the old V1.8 trend chart. One chart on the page.
- **Open decision 2 (validated)**: calibration shows the latest session's
  values with the range across all sessions, never an average.
- **Profile header** (1–16): 2 px `--color-text` top rule, "Learner Profile" in
  `section` type (22/28), the scope line in body secondary (1–13), and
  "Updated [date], profile v[n]" in `caption` at 14–16, right-aligned.
- **Three blocks, three treatments** (not a card grid):
  - *Usual performance* (1–6), no panel: subtitle, the entry sentence, then a
    table with "Latest session" and the range column ("Across [n] sessions", or
    "One session so far." with no range values). The three response-time rows
    sit under a 600-weight "Typical response time" row and are indented 16 px;
    trial types read "Meaning to kanji (T1)", "Kanji to meaning (T2)", "Kanji to
    reading (T3)". The overall-median fallback is a 14 px info icon after the
    value with the tooltip from the copy. Origin lines in `caption`.
  - *What followed each adaptation* (7–16), surface panel, radius 2 px: one row
    per group, rules between rows. Sentence on the left, "See [n] decisions"
    link on the right; below it the badge row. "Too few to tell" is the first
    item of the badge row: a 24 px pill, `--color-state-neutral` fill,
    `--color-text-secondary` 600 text (never dashed). Outcome badges reuse the
    V1.5 outcome chips (same fill + mark shape) with the direction label and
    count, e.g. "Recovered after: 2"; the enum and subtype go in the tooltip.
    At most 3 groups show; more go behind "Show [n] more groups" (outline
    accent pill). The empty texts (STATIC only, no changes) are plain body
    text, not an empty state.
  - *Across sessions* (1–16), 1 px top rule: subtitle, the entry sentence (it is
    the chart title), and the "Correct in S7" / "Response time" toggle. The
    chart follows the V1.8 rules (completed only, ticks numbered as in the
    table, shapes by condition, "Latest" label up to 12 sessions), with one
    change: the accuracy axis is **correct answers of 20** (0, 5, 10, 15, "20 of
    20"), matching the sentence, instead of 0–100 %. With one session there is
    no chart, only the sentence.
- **Only COMPLETED sessions count** (Sebas, Oct 21, 14:24): an ABORTED session
  is in no part of the profile (calibration, adaptations, trend), even if it
  reached S6 or S7. **The profile never mentions aborted sessions** (Sebas, Oct
  21, 18:19; artboard confirmed 18:22): no count, no clause, no
  tooltip, also not in the empty profile. A session can abort for technical
  reasons (30 minutes with no activity), so naming them would read as the
  participant's fault. The scope line is: "A summary of [n] completed sessions.
  It describes what happened in windows of trials, not the person, and it
  doesn't change how the next session starts." Block origin lines don't mention
  them either. "Sessions in order", below the profile, still lists them with
  their status. Copy: `Contenido_UI_F-PROFILE.md` §0.1.
- **"See [n] decisions" across sessions** (Oct 21, 14:50; validated by Sebas
  Oct 21, 18:22, canvas version 38). A group can hold decisions from several
  sessions, and V1.5 belongs to one session:
  - Group from one session: a plain link, "See [n] decisions", to that
    session's V1.5 filtered by the group.
  - Group from several sessions: the link becomes a disclosure button, "See
    [n] decisions in [k] sessions" with a chevron (`aria-expanded`). It opens,
    inside the group row, a list on `--color-explain-bg`: one line per session,
    newest first, "Session [#] ([date])" with the session number from "Sessions
    in order" and, on the right, a link "[n] decisions" to that session's V1.5
    filtered by the group. Not a popover, and no "latest session only" shortcut,
    which would hide the other sessions.
- **V1.5 filtered by a profile group** (Tweak `groupFilter` on the V1.5
  artboard): the table shows only that group's decisions. Above it, in place of
  the intro sentence, a notice on `--color-accent-tint` with `role="status"`:
  "Filtered from the Learner Profile" (600, on-accent-tint), the group sentence
  and "[k] of the [n] decisions in this session"; then "Back to the profile"
  (link) and "Show all decisions" (outline accent pill), which removes the
  filter and restores the intro sentence. The filter lives in the URL
  (e.g. `?group=…`), so reload and back keep it. "Show decisions with no
  change" stays available and applies inside the filter.
- **Exact form from the validated canvas** (D-F6-11, Oct 21 2026). Where the
  canvas and this file differed, the canvas wins; these are the values that
  were only drawn. They supersede the older V1.8 trend-chart rules (axis title,
  0–100 % axis) for the profile's chart.
  - *Page header*: breadcrumb and title (1–10) with 8 px between them; the
    condition chips and the sessions fact share **one** wrapping row at 11–16,
    right-aligned, aligned to the bottom of the title; the fact in
    `--color-text-muted`. The main grid on this page uses a 24 px row gap.
  - *Empty profile*: the profile header stays as in the other states (scope
    line "A summary of the completed sessions. It describes…"), and the meta
    slot at 14–16 reads "No profile computed" instead of the date.
  - *Usual performance table*: header cells 32 px with a 1 px `--color-border`
    bottom rule; "Latest session" and the range column **right-aligned** with
    16 px left padding and no wrapping; body rows compact, 5 px vertical
    padding (indented rows 16 px left), 1 px `--color-border-subtle` rules;
    the "Typical response time" row has 8 px top padding and none below. The
    fallback icon carries the tooltip naming the short type ("Too few T3
    trials in practice; this uses the overall median.") and the same text as
    its `aria-label`.
  - *Adaptations panel*: padding 20 px top/bottom, 24 px sides; 12 px gap
    between title, list and origin lines. Groups are an `<ol>` without
    bullets; each `<li>` has a 1 px `--color-border-subtle` **top** rule and
    12 px vertical padding; inside it a two-column grid (sentence, link) with
    24 px column gap and 8 px row gap.
  - *Links and disclosure*: "See [n] decisions" is underlined, weight 500,
    `--color-accent`, no wrap. The disclosure button looks the same (no
    border, no fill, underlined) and ends in a 12 px stroke chevron (SVG,
    1.6 px stroke), pointing down when closed and up when open; never "▾".
  - *Decision list* (open disclosure): spans the full group row, under the
    badges; `--color-explain-bg`, radius 2 px, padding 8 px / 12 px, 4 px
    between lines; the date in `--color-text-muted` inside the parentheses,
    the "[n] decisions" link right-aligned. Dates use the portal's format.
  - *"Show [n] more groups"*: 32 px outline pill, 1 px `--color-accent`
    border, **transparent** background, on-accent-tint text, weight 500.
  - *Empty texts* (STATIC only, no changes): body text with 12 px top padding
    and a 1 px `--color-border-subtle` top rule; the "See [d] decisions" link
    goes **below** the sentence, not beside it.
  - *"Not recorded" badge* (D-F6-8, validated by D-F6-96): for changes applied
    before Oct 14 with no stored outcome. Same 24 px pill as the other outcome
    badges, **1 px dashed `--color-border-strong` border, no fill, no mark**,
    `--color-text-muted` text, "Not recorded: [n]"; always the **last** item of
    the badge row. It never counts in the "k of n" nor in the "Too few to tell"
    threshold, like `UNCERTAIN`. Tooltip: "No outcome was recorded for these
    changes" (`Contenido_UI_F-PROFILE.md` §3.4). Never shown for `UNDERCHALLENGED`
    groups (rules-v2 always records the outcome).
  - *Badge tooltip*: the enum, then the subtype after a comma, no count:
    "POSITIVE", "POSITIVE, RESOLVED", "UNCERTAIN, INCOMPLETE".
  - *Across sessions*: 16 px top padding over the 1 px top rule, 8 px gap.
    The chart is compact, about 124 px tall (plot about 88 px), with **no
    x-axis title**; the legend row lists the condition shapes and ends with
    "Completed sessions only, numbered as in the table." in `caption`. Point
    tooltip: "Session [#], [condition], set [X], [k] of 20 correct".
  - *Below the profile*: a "Pre-test and kanji sets" section at 1–10 (1 px
    `--color-border` top rule, 24 px top padding, title in `section` type
    22/28) with the pre-test lead sentence (16/24) and a `<dl>` with Pre-test
    and Notes (120 px label column). Next to it, at 11–16, "Kanji replaced by
    the pre-test": 1 px top rule, 24 px top padding, title in `subtitle` type
    18/24, the table directly under it, **no intro sentence**. "Sessions in
    order" follows at 1–16.
  - Copy is not part of this list: where the canvas text is older than
    `Contenido_UI_F-PROFILE.md`, the document wins (D-F6-6).
- **No profile**: the blocks are replaced by one surface panel (1–10) with
  "No profile yet." as subtitle and "[code] has no completed session yet. The
  profile appears after the first one." (+ the pre-test date). A participant
  whose sessions all aborted looks exactly the same: an empty profile, not an
  error.
- **Many sessions**: same layout; with DEV_UNITY the third group and the chart
  fall below 900 px, accepted by Sebas for test participants.
- **V1.5 and V1.6 artboards**: the cause "Impulsive" now reads "Quick errors",
  following the copy rule that `IMPULSIVE` never appears on screen.

## Participant list (V1.11) and navigation

Validated by Sebas on Oct 17 2026, 00:20.

- **Participant list**: the normal shell. Title 1–9 with a lead sentence, and a
  pre-test status bar at 10–16 (segmented: completed, in progress, not started
  dashed). Below it are the filters (code, pre-test status, condition, "only with
  notes") and the table.
  - Columns: code (mono link to V1.8), registered, pre-test chip (same chips as
    V1.10), sessions, condition chips, last session, last accuracy, and notes
    for the researcher (warn icon + text, e.g. "Previous Japanese study
    reported", "Kanji kept with no substitute").
- **How to reach one participant (V1.8)**:
  - the "Participants" item in the rail opens V1.11;
  - a code in V1.11, in the session list (V1.1) or in the Session View facts
    opens V1.8;
  - V1.8's breadcrumb goes back to V1.11;
  - from V1.10, "View result" and the summary's "Open participant page".

## Pre-test screens (V1.10)

Validated by Sebas on Oct 17 2026, 00:02.

- **Two audiences on one screen.** The participant sees everything except what
  sits behind the researcher controls. The participant-facing parts use the
  calmest layout in the app: no sidebar, one kanji, one question, no motion, no
  sound.
- **Pick a participant** uses the normal shell (rail + 16-column grid). Status
  chips carry a shape as well as text:
  - Not started: dashed outline with an empty dot.
  - In progress: accent tint with a half-filled dot and "[n] answered".
  - Completed: neutral fill with a solid dot and the date.

  Row actions are Start (CTA), Resume (accent outline) and View result
  (neutral outline).
- **Register** is a centered form, at most 1120 px wide, with a dark top bar
  (`--color-sidebar`). It has two numbered parts, because the order is real:
  - Part 1, Researcher: the code field and the consent checkbox.
  - Part 2, About you: five radio groups, drawn as pill options 40 px tall, with
    a ✓ on the selected one.

  One "Save registration" CTA covers both parts. After it, the inclusion notice
  appears in `--color-warn-tint` with "Continue to the pre-test" and "Stop
  here".
  - Wording (Oct 17): the attention question has six pills: Never, Rarely,
    Sometimes, Often, Very often, Prefer not to answer.
  - The notice says the criterion "no previous study of Japanese" was accepted
    by MIRAI on Oct 9, not "proposed".
  - "Have you studied Japanese before?" has three pills: No, Yes, Prefer not
    to answer (added Oct 17, approved by Sebas).
  - The same notice, with the same layout, also shows "previous Japanese study
    not reported" when the participant picks Prefer not to answer on that
    question. That state is in *V1.10 States*.
- **One kanji (focus mode)**:
  - Top bar with the product name, the participant code, "[n] answered"
    (`aria-live`) and Pause.
  - The kanji in `kanji-display`, then "Do you know this kanji?" in `title`.
  - Three answer pills, 64 px tall and at least 168 px wide, each showing its
    key (1, 2, 3).
  - For Not sure or Yes: two 48 px inputs (reading, meaning). Each result is a
    pill with an icon and a word ("✓ Correct" on the accent tint, "✕ Incorrect"
    on the alert tint), never color alone.
  - **Researcher strip**: a full-width `--color-sidebar` band at the bottom,
    labeled "Researcher". It holds the flip buttons, named by action ("Mark
    reading incorrect"), and the "Save and next" CTA.
- **Complete**:
  - The participant sees "That's all. Thank you." and nothing else of the
    result.
  - Below a 2 px rule, "For the researcher" shows only the completion time and
    the number answered, plus "Open participant page".
  - Substitutions and flagged kanji are shown **only in Participant View**
    (decided by Sebas, Oct 16, 23:57). This screen never shows set names,
    substitutes, or correct readings and meanings.
- **Notices** (states sheet *V1.10 States*):
  - A panel with radius 2 px, an 18 px icon, a bold title, one sentence and an
    optional outline-pill action.
  - Kinds and fills:

    | Kind | Fill | Icon |
    | --- | --- | --- |
    | info | accent tint | i |
    | warning | warn tint | triangle |
    | error | alert tint | ✕ |
    | neutral | ground with a hairline | clock |

  - Errors use `role="alert"`; the rest use `role="status"`.

## Brand (D-F6-117, D-F6-120, D-F6-121)

Validated by Sebas on Oct 30 2026: round 2 of the vector redraw of
`Andon_icono_E`, artboard *Brand* (canvas version 47). Final files are in
`Claude outputs/design-handoff/brand/`. Brief and history: the "Brief de marca"
section and the Registro of `Reglas_Diseno_Research_Dashboard.md`.

- **Where it may appear:** app icon, favicon, the rail header, logo, covers, and
  empty states the researcher sees. **Never** in the VR scenes or on any
  participant screen, the pre-test included (D-F6-117). Use outside the lab waits
  for MIRAI (A-12).
- **Mascot:** an *andon* paper floor lamp with two big round eyes (Ink pupils,
  two Paper highlights each) on a soft vertical oval of saffron light; two Ink rods
  cross the paper above and below the light; a cap, a rounded frame and four
  splayed legs. No mouth, brows, blush, text or brush stroke. The eyes never
  change with the participant's results.
- **Colors (fixed, the same in both themes; not theme tokens):**

  | Part | Value | Existing token |
  | --- | --- | --- |
  | Icon tile, light | `#0B6A73` Lagoon | `--color-accent` light |
  | Icon tile, dark | `#0F1115` Night | `--color-bg` dark |
  | Disc behind the lamp (the only shape in this color) | `#3FB7C2` Light Lagoon | `--color-accent` dark |
  | Paper, eye highlights | `#F9F8F6` Paper | `--color-bg` light |
  | Light | `#F2A93B` Saffron | `--color-cta` |
  | Cap, frame, rods, legs, pupils | `#14171C` Ink | `--color-text` light |

  Ink never touches Lagoon (2.84:1): it sits on paper, light or the disc. No
  gradients, glows, shadows or outlines.
- **Geometry (viewBox 0 0 100 100):** tile radius 22.5; disc centered at (50, 49.6),
  r 44.7; the lamp spans x 26–74 and y 13–87, inside the 80 % safe zone. Frame
  radius 4.5, paper radius 2.8; light oval rx 18, ry 19.5; rods 2.2 thick (≥ 1/48
  of the side). The SVGs in `design-handoff/brand/` are the source; do not redraw.
- **Files:**

  | Use | Light | Dark |
  | --- | --- | --- |
  | Master, store, PWA (scale down from it) | `andon_icon_light_1024.png`, `andon_icon_light.svg` | `andon_icon_dark_1024.png`, `andon_icon_dark.svg` |
  | apple-touch | `andon_icon_light_180.png` | `andon_icon_dark_180.png` |
  | Rail header, 32 px anywhere outside the browser tab | `andon_icon_light_32.png` | `andon_icon_dark_32.png` |
  | Favicon 32 | `andon_favicon_light_32.png`, `andon_favicon_light_32.svg` (= `andon_favicon_light.svg`) | `andon_favicon_dark_32.png`, `andon_favicon_dark_32.svg` (= `andon_favicon_dark.svg`) |
  | Favicon 16 | `andon_favicon_light_16.png`, `andon_favicon_light_16.svg` | `andon_favicon_dark_16.png`, `andon_favicon_dark_16.svg` |

- **Favicon:** simplified, without eyes or legs: disc, thick cap and base, paper,
  oval light. At 32 px it keeps the two rods at exactly 1 px; at 16 px it drops
  them. In dark mode use the Night files, or one `favicon.svg` that switches the
  tile to Night with `prefers-color-scheme`.
- **Rail header:** the 32 px icon sits **above** "NeuroAdaptive VR" (Newsreader 500,
  22/28 px); beside it, the name wraps in the 240 px rail. The rail keeps its width.
- **Logo:** icon + "NeuroAdaptive VR" in Newsreader 500, clear space 1/4 of the icon
  height; Ink text on Paper or white, `#ECEAE5` on Night. The name never goes
  inside the icon.
- **Covers:** 1600 × 900 and 1200 × 630, Paper or Night; the mascot without the
  tile (disc and lamp) on the left third, the name in Newsreader 500 and one line
  in Public Sans from UI/UX.
- **Known resemblance (D-F6-121):** Google Lens relates the icon to Semibot, from
  the game R.E.P.O. Sebas kept the icon as is. Before asking MIRAI about outside
  use (A-12), the resemblance is reviewed again, with the shape proposal
  `andon_propuesta_forma_repo.png` in `design-handoff/brand/`.
- **When to build:** the dev chat puts the favicon and the rail icon in the portal
  **after the freeze** (Estado_Actual, Oct 30).

## V1.12 Block R: free recall (D-F6-125, D-F6-208)

**Validated** (D-F6-226, Sebas, Nov 17 2026; see the log). The researcher's form for part 1 of block R: the
participant says out loud, in the headset, what they remember of the kanji of an
earlier session; the researcher marks it here as they speak. Researcher-only;
the participant never sees this screen. Nothing on it feeds the engine.

- **Where:** opened from the page of a session that has block R (visits 2, 3 and
  the short visit 4), with a "Free recall" link in the header actions. The form
  belongs to that session and shows **the session it evaluates** (D-F6-190 (2)),
  never the set of the session in progress.
- **Shell:** focus mode, like V1.10: dark bar (`--color-sidebar`) with the title
  "Free recall" (`title`), the participant code (mono), "Visit [n], block R part
  1 of 3" (`caption`, `--color-sidebar-muted`) and an outline pill "Back to the
  session" (`--color-on-dark-border`). No rail. Content `max-width` 1120 px,
  16-column grid, 32 px gutter, padding 48 / 32 / 64 px.
- **Left column (columns 1–5):** `title` "What they remember" and the rule for
  the researcher (don't repeat, correct, hint or ask about a kanji they haven't
  mentioned); a `<dl>` (96 px label column): *Evaluates* (session id, mono
  link), *Set*, *Learned* (date of that session and days since); a box on
  `--color-explain-bg`, radius 2 px, with what the board shows in VR (the
  instruction text from UI/UX, D-F6-208); *What counts* (`caption` label, body
  text), the scoring rule of **D-F6-225**, word for word: "Meaning: the meaning
  or a clear synonym, in any language. Reading: the Japanese reading, said
  close enough to recognise. Anything you're unsure about goes in "What they
  said", without a mark. There is no mark for a partial answer." The same rule
  applies to the dev chat's placeholder form (BR3) until this one is validated.
- **The five kanji (columns 6–16):** one panel (`--color-surface`, 1 px
  `--color-border`, radius 2 px). Header row in `caption`: Kanji, Taught as,
  Recalled, Order. One row per kanji of the evaluated set, in the set's order,
  rows split by `--color-border-subtle`, grid `56px 128px 1fr 48px`, 16 px
  column gap, padding 16 / 24 px:
  - the kanji in Noto Serif JP 500, 32 / 40 px, `lang="ja"`;
  - *Taught as*: meaning (`body`) over reading (`caption`), as the session taught
    them (from `kanji_content.json`);
  - two **toggle buttons**, "Meaning" and "Reading": real `<button
    aria-pressed>`, 32 px pills; off = surface with 1 px `--color-border-strong`;
    on = the selected toggle chip (accent tint, `--color-on-accent-tint`, 1 px
    accent border, weight 600) **plus a check before the label**, so the state
    never rests on color alone;
  - *Order* (mono, `caption` size, `--color-text-muted`, right-aligned): "1st",
    "2nd"… is set automatically the **first time** any toggle of that kanji goes
    on, and kept if it is switched off and on again; "—" while nothing is
    marked;
  - under them, across columns 2–4: "What they said", a 32 px text input, radius
    4 px, optional (partial or doubtful answers, or what they said instead).
- **Anything else they said:** a textarea (3 rows, label in `caption`) for
  intrusions: other kanji, words or guesses that don't match the five.
- **Footer:** 1 px `--color-border` rule; on the left a `role="status"` line with
  an 8 px dot (ring in `--color-border-strong` = not saved; filled
  `--color-accent` = saved; filled `--color-alert` = save failed) and "[k] of 5
  kanji recalled. Not saved yet." / "Saved at [hh:mm]. [k] of 5 kanji recalled.
  Changes are saved again with their time." / "Nothing marked. Not saved yet." /
  "[k] of 5 kanji recalled. Not saved."; on the right the primary button (40 px):
  "Save free recall", "Save changes" once saved, and **"Save: nothing recalled"
  when no toggle is on**. Under it, in `caption`: "Saving with no marks records
  that nothing was recalled. Leaving without saving records nothing for this
  part."
- **Save failed:** an alert notice above the footer (`role="alert"`,
  `--color-alert-tint`, `--color-on-alert-tint`, radius 2 px, ✕-in-circle icon):
  "Couldn't save. Your marks are still here." and "Check that the backend is
  running, then save again." with the error code in mono. The marks stay on
  screen.
- **What is stored** (for the dev chat; names are theirs): per kanji of the
  evaluated session, meaning yes/no, reading yes/no, the order of first mark and
  the "What they said" text; the "anything else" text; who evaluated which
  session; the save time, and a new time on each later save. **Never saved =
  nothing stored** (NULL, "not recorded"); **saved with no marks = recorded as
  nothing recalled** (0). The two are never confused (as D9 of the schema).
- **Who ends it (D-F6-212, D-F6-223):** the researcher. There is no clock: about 2
  minutes is only a guide. If the participant goes quiet, the researcher says
  once, "Anything else you remember?"; when the participant says they are done,
  the researcher saves here and presses **R** in Unity, which ends part 1 and
  logs `BLOCK_R_RECALL_ENDED` with the elapsed time (D-F6-223 (1)). Neither the
  VR nor this form shows a clock.
- **Not here:** no timer or countdown, no score or percentage,
  no hint of what the answer was to the participant, no edit of the yes/no or
  multiple-choice parts of block R (those come from Unity).
- **Dark theme:** the same tokens in their dark values; drawn on the dark
  artboard (`saved` state).

## V1.13 Live session monitor (D-F6-231, D-F6-233, D-F6-234, D-F6-270, D-F6-272)

**Validated** (D-F6-233, Sebas, Nov 17 2026; see the log). M1 builds it during the
pilot, on a day with no participant (D-F6-231 (5)). The Low / Normal / High bands
of *Live indices* follow **D-F6-234**: they are the engine's own thresholds, not
the S6 min/max first suggested. **D-F6-270** adds the session-ended state, the
«Sync tap» mark and «—» for `autorun` (below); **Validated (D-F6-272)**.

What it is: one screen where the researcher watches the session as it runs (the
stage, the signal, what the engine computes and decides). **Read only** (D-F6-231
(1), D-F6-230): no button on it sends anything to Unity, the engine or the
recording, and it has no forms. Commands from the portal (M2) are out of scope.

- **Where:** a **second screen, full screen, 1440 × 900, no scroll** (D-F6-231
  (4)). The page is fixed at 1440 × 900 with `overflow: hidden`; panels never grow
  a scrollbar. If the window is smaller, it's the browser's zoom, not a
  responsive layout.
- **Shell:** focus mode, no rail.
  - **Dark bar**, 88 px, `--color-sidebar`, 24 px side padding, a 3-column grid:
    - left: `caption` "Live session monitor" (`--color-sidebar-muted`) over the
      stage in `display` (36 / 40, Newsreader 500), e.g. "S7 Adaptive practice"
      (S1–S9 and block R, from `STATE_ENTERED`), then the trial "Trial 12 of 20"
      in `body`, `--color-sidebar-muted`;
    - center: the clock since the session started, JetBrains Mono 500, 30 / 36,
      `hh:mm:ss`, with the `caption` "since the session started";
    - right: a `<dl>` of `caption` labels over values: Session (id, mono),
      Participant (P##, mono), Condition, Set, Visit.
  - **Status strip**, 36 px, full width, under the bar. It carries the one
    session-level notice, never a modal:
    - nothing to report: `--color-bg`, `--color-text-muted`, "Read only. Nothing
      on this screen changes the session.";
    - 60 Hz session warning: `--color-warn-tint` with `--color-text`, triangle + bold text "Mains
      noise [n] µV (median of 8 channels). Check reference and ground, unplug the
      charger.";
    - EEG source cut: `--color-alert-tint` with `--color-on-alert-tint`, ✕ + "EEG: no data for [n] s. Windows
      without EEG fall back to behavior.";
    - channel excluded: `--color-surface`, ring + "F3 excluded at [hh:mm:ss] by
      the engine. The indices go on without it until the end of the session.";
    - no session: "No session. The monitor fills in when Unity starts one."
    - session ended, only on `/monitor/<id>` (D-F6-270 (4)): `--color-surface`,
      ring + bold "This session has ended", then in `--color-text-muted`
      "Session {id8} closed at {hh:mm:ss}. Its data is in the session view." and
      the link "Open session view" (`--color-accent`, 600, underlined, opens the
      session view in the same window). See *Session ended* below.
    If two apply at once, the source cut wins, then the 60 Hz warning, then the
    exclusion (the exclusion is also fixed in the quality table, so it is never
    lost).
- **Body:** 16-column grid, 24 px gutter, padding 16 / 24 px. Panels:
  `--color-surface`, 1 px `--color-border`, radius 2 px, padding 12 / 20 / 14 px,
  10 px gap. Every panel header has its `title` (22 / 28) on the left and, on the
  right in `caption`, **when it was last updated** ("Updated 1 s ago", "Measured
  after S3", "Live").
  - Columns 1–5: Signal quality, then System (System takes the rest of the
    height).
  - Columns 6–11: Live indices, then Adaptation decisions (the rest of the
    height).
  - Columns 12–16: Sync, then Events (the rest of the height).
- **Stale data (D-F6-231 (4)):** when a section's source stops, the panel turns
  `--color-bg` with a **1 px dashed** `--color-border-strong` border, its update
  caption becomes "No data for [n] s" in `--color-alert`, the status marks turn
  into "No data" (dashed ring), and the last numbers stay in
  `--color-text-muted`. A number is never shown as current when it isn't.
  - `live.py` stops (no heartbeat): Signal quality and Live indices go stale;
    System shows `live.py` "No heartbeat for [n] s" with ✕.
  - The backend stops: the whole page goes stale (each panel the same way).
  - Events and decisions come from the backend, so they keep updating when only
    the EEG stops.

### Signal quality (D-F6-231 (2) and (3))

- A table (`role="table"`) of 8 rows, in montage order: Fp1, F3, Fz, F4, Cz, P3,
  Pz, P4. Grid `44px 80px 1fr 64px 76px`, 8 px gap, rows ≥ 32 px split by
  `--color-border-subtle`. Header in `caption`: Channel, Last 5 s, **60 Hz
  (µV)**, **RMS (µV)**, **% > 100 µV**. Numbers right-aligned, tabular; channel
  names in mono.
- **Status per channel** (column "Last 5 s"): always a shape + a word, in the
  quality tokens (Sebas chose the portal tokens over a new green, D-F6-231 (4)):
  - **OK**: filled circle, 10 px, `--color-quality-ok`;
  - **Watch**: triangle, 12 × 11 px, `--color-quality-warn`; the row gets
    `--color-warn-tint`;
  - **Bad**: ✕, 11 px, `--color-quality-error`; the row gets
    `--color-alert-tint`;
  - **No data**: dashed ring, 10 px, `--color-border-strong`.
- **The rule** (EEG chat, D-F6-231 (3)): share of samples over 100 µV in the
  **last 5 s**, leaving out ±1 s around each `SYNC_TAP`:
  - OK under 5 %;
  - Watch from 5 to 20 %, **or** the last 30 s span over 20 %;
  - Bad over 20 %, **or a flat signal**.
  The colour is computed by `live.py`, not by the page; the page only shows it.
  The rule is printed under the table in `caption`, so nobody has to remember it.
- **Excluded** (D-F6-216, read from the engine, D-F6-231 (3)): a separate mark,
  **fixed** from the moment the engine excludes the channel until the end of the
  session, and **with its time**. It sits on its own line under the channel's
  row: a 22 px pill with a 1 px **dashed** `--color-border-strong` border, a
  ⊘ icon and "Excluded at [hh:mm:ss]" (time in mono), then `caption` "set by the
  engine". The row's numbers go `--color-text-muted` and the row loses its
  tint, so it reads as out of the count; the status mark keeps showing the 5 s
  rule (it can say Bad and Excluded at once). System and the status strip repeat
  it.
- **60 Hz:**
  - per channel, the value in µV; if a channel is **under 0.3× or over 3×** the
    median of the others, a 8 px **ring** in `--color-quality-warn` and its
    ratio in `caption` ("0.1×") go before the value;
  - session line under the table: shape + word, then "60 Hz, median of 8:
    **[n] µV**" and `caption` "warning from 800 µV". **From 800 µV** it becomes
    Watch (triangle), the caption says "over 800 µV" and the status strip shows
    the session warning. Below 800 µV it's OK.
  - RMS and 60 Hz use the methods of the EEG chat's Registro (17 nov, 14:30).
- **Flat signal:** Bad, with the same ✕; no extra state.
- **Sync tap** (D-F6-254 (2), D-F6-270 (5); Validated, D-F6-272): when the S3 taps leave **less than
  1 s** of the last 5 s outside ±1 s of each tap, `live.py` keeps the **previous
  colour** and flags it. The page shows the same shape and word as before and,
  right after the word, "Sync tap" in `caption` (`--color-text-muted`), no new
  colour and no new shape; the row keeps its tint if it had one. In practice it
  shows on every channel at once during S3 (Tweak `syncTap`). The rule under the
  table ends with "Sync tap: the taps cover the last 5 s, so the earlier colour
  stays."

### Live indices (bands: D-F6-234)

- Two strips, **Engagement Index** and **Frontal theta (Fz)**: `body` 600 name
  on the left; on the right the **band word** and the current z as `figure`
  (24 / 32, 600), signed with a real minus ("−1.3").
- **Bands (D-F6-234 (1)) are the engine's thresholds:** **Low** z ≤ −1,
  **Normal** −1 < z < +1, **High** z ≥ +1, for both indices, against **the same
  reference the engine uses** (S6, or S4 eyes open as the fallback). No
  min/max and no percentiles. They are **for reading only**: they change no rule
  of the engine (D-F6-128, D-F6-198).
- **The word** (D-F6-234 (2)) comes from the z of the **decision window**
  (`eeg_ei_z`, `eeg_theta_z`), never from a single epoch: "Low" with a
  downward triangle (11 × 9 px), "High" with an upward triangle, "Normal" with no
  mark; `body` 600 in `--color-text`. No red or green: Low and High are not "bad"
  or "good".
  - The EEG didn't count in that window (P7): the figure goes
    `--color-text-muted`, the word is "Not counted" with a dashed ring, and there
    is no band word.
  - Before S7: no strips; "Reference after S6. The bands and the first window
    come after trial 3 of S7."
- Under each name, an SVG strip 452 × 70 px. The x axis has a slot for each of
  the 18 decision windows of S7 (after trials 3–20), starting 46 px in so the
  zone names fit; the windows so far are drawn, the rest stays empty, so the
  strip doesn't move. The y axis is z from −2 to +2, labels +1 and −1 in mono
  11 px on the left. Inside it:
  - the **Normal** zone, −1 to +1, in `--color-explain-bg`, edged in
    `--color-border`; the zone names **High**, **Normal** and **Low** in 10 px
    `--color-text-muted` at the left edge of each zone;
  - the decision-window z as a 1.5 px `--color-accent` line with 3 px dots. If
    M1 also draws the per-epoch z, it goes as a 1 px `--color-border-strong`
    line with no word or label (D-F6-234 (2));
  - on the Engagement strip only, the dashed `--color-quality-error` line at
    **−1.5** (where `EEG_LED` can lead), kept by D-F6-234 (1), labelled "−1.5" at
    the right end.
- **EEG row** under the strips, one dot per window: filled `--color-accent` =
  the EEG counted in that window (P7); ring `--color-border-strong` = it didn't.
- Then a `<dl>`: *EEG counted* "[k] of [n] windows ([p] %)" (plus "without F3
  since [time]" when a channel is excluded) and *Reference* "S6 ([n] epochs not
  POOR)" or "S4 eyes open (fallback)" (D-F6-220, D-F6-234 (1)); before S7, "After
  S6". One `caption` line: "Zones use the engine's reference: Low z ≤ −1, High z ≥
  +1. The word is the decision window's, for reading only. Dashed: −1.5, the EEG
  leads."
- **Data (D-F6-234 (3)):** nothing new to compute. The page reads the reference
  from `eeg_sessions` and the z of each decision; if the reference is recomputed
  (D-F6-216), it reads the new one.
- If Fz is the excluded channel, the theta strip shows "Unavailable: Fz
  excluded at [time]" in `--color-text-muted` instead of the line and the word
  (D-F6-216).

### Adaptation decisions

- Header caption: "[k] of 3 changes used" (the cap of D-F6-182).
- **ESL and LAL lanes** (SVG, 46 px): two rows labelled ESL and LAL, x = S7
  trials 1–20, background `--color-border-subtle`; the level as a step bar in
  `--color-border-strong` (Low 6 px, Medium 11 px, High 16 px tall); a 2 px
  `--color-text` tick at each change; a 1.5 px `--color-accent` line at the
  current trial; the current level in words at the right end (`caption` 600).
  The SVG has an `aria-label` that says the same in words.
- **One row per decision, newest first** (the V1.5 language, compressed):
  - a diamond (filled `--color-text` = a change was applied; outline
    `--color-border-strong` = no change), "After [trial]" (trial in mono);
  - the estimated state as a 10 px dot in its state token + label;
  - the EEG effect as its code in mono 12 px (`EEG_CONFIRMED`, `EEG_VETO`,
    `EEG_LED`, `EEG_ONLY_ALERT`, …; nothing when the EEG had no effect);
  - the action on the right ("LAL down one step" in 600; "No change" in 400);
  - second line, `caption`: the short reason on the left (one line, ellipsis)
    and "ESL [level], LAL [from] → [to]" on the right.
- Empty: "No decisions yet."

### Sync and System

- **Sync** (`<dl>`, 120 px label column): S3 taps "[k] of 5 clear", Offset
  "[n] ms", Dispersion (robust) "[n] ms" + mark + "Within 50 ms" (D-F6-217;
  outside: triangle + "Over 50 ms"). Caption "Measured after S3". During S3:
  taps "[k] of 5 so far", Offset and Dispersion "—", a dashed ring + "After S3",
  caption "Measuring in S3". There are no S9 taps, so there is no drift line
  (D-F6-217).
- **System** (`<dl>`): LabRecorder ("Recording AURA and UnityMarkers" / "Not
  recording"), `autorun` **"—" with no mark** in every state (D-F6-267, D-F6-270
  (5): its status does not reach the monitor before the pilot; a later decision
  brings it back with its own shape + word), `live.py` ("Heartbeat [n] s ago" / "No heartbeat for [n] s" / "Not
  running"), Excluded channel ("None" / "F3, at [time]"), S4 alpha ratio ("P3
  [x], Pz [x], P4 [x]. Passes (≥ 1.2)"). Each process with the same shape +
  state marks.

### Events

- `<ol>`, **newest on top**; new lines come in at the top and nothing else moves
  (no animation). Each line: session time (mono 12, `--color-text-muted`), then
  the type (mono, 500) and a short detail, wrapping if needed.
- **Routine** (`TRIAL_STARTED`, `TRIAL_COMPLETED`, `RESPONSE`,
  `DISTRACTOR_INTERACTION`, `FRAME_HITCH` ≤ 100 ms): all in
  `--color-text-muted`.
- **To look at** (`HEAD_AWAY`, `FRAME_HITCH` > 100 ms, an excluded channel, an
  `autorun` error): a small triangle in `--color-quality-warn`, type in 600 and
  text in `--color-text`.
- `ADAPTATION_DECISION`: type in `--color-accent`, 600.
- As many lines as fit; the oldest fall off the bottom (the full log stays in
  the Session View).

### No active session

Bar: "No session running" in `display`, "Unity has not started a session", clock
"--:--:--" in `--color-sidebar-muted`, no metadata. Panels keep their place with
"Waiting" captions, dashes and the empty sentences above. System still reports
what it can (LabRecorder "Not recording", `autorun` "—", `live.py` "Not
running"). `/monitor` comes back here when its session ends (D-F6-270 (4)). With
more than one `IN_PROGRESS` session (one left hanging before D-A1 closes it),
`/monitor` follows the one with the latest event; the rail entry uses the same
rule (D-F6-270 (3)).

### Session ended (D-F6-270 (4); Validated, D-F6-272)

Only on `/monitor/<id>`, when that session closes while the page is open (Tweak
`sessionEnded`).

- **Bar:** the last stage stays; the trial slot says "Session ended"; the clock
  stops at the closing time, in `--color-sidebar-muted`. Metadata stays.
- **Status strip:** the session-ended notice above (it wins over every other
  notice: nothing else is live any more).
- **Panels keep their last data in the stale style:** `--color-bg`, 1 px dashed
  `--color-border-strong`, numbers and words in `--color-text-muted`, the index
  lines in `--color-border-strong`; every update caption reads "Last data at
  [hh:mm:ss]" in `--color-text-muted` (not the alert colour: nothing failed).
  Status marks keep their last shape. Events keep their last lines.
- The page doesn't jump to another session and doesn't empty itself: the
  researcher may still be reading it. Text: `Contenido_UI_Monitor_Accesos.md`
  §3.1.

### Not here

No buttons that act on the session, no sound, no blinking, no animation (values
change in place), no score or performance figure for the participant, no raw
EEG trace. Dark theme: the same tokens in their dark values; the bar uses the
dark `--color-sidebar` (`#08090C`).

## V1.13 access: rail entry and session link (D-F6-268, D-F6-272)

**Validated (D-F6-272)** (see the log), with the answers of D-F6-270. Until it is
built, V1.13 only opens from its address. These two ways in are **links only**: they change nothing in the session,
the recording, the engine or `live.py`. Words come from
`Contenido_UI_Monitor_Accesos.md` (UI/UX); if they change there, they change here.

### 1. Rail entry

- **Place:** the **second item of the navigation rail, under Sessions**, because
  it is about the session that is running now. Same item as the others: 40 px
  pill, 16 px left padding, 12 px gap, `--color-sidebar-text`; active =
  `--color-accent` (light value) fill and `--color-on-accent`, like any view.
- **Icon:** a signal line, 16 × 16, 1.5 px stroke, round caps and joins, in
  `currentColor`: `M1.5 8.5h3l1.5-4 3 7 1.5-3h4`. It is not a heart rate and not
  a brain; it reads as "live signal" next to the other rail icons.
- **Label:** "Live monitor" in both states (the rail never changes its word).
- **Status at the end of the pill** (D-F6-268: it follows the running session):
  - session `IN_PROGRESS`: an 8 px filled dot in `#3FB7C2` (the Lagoon of the dark
    rail) and the word "Live" (`caption`, 500, `--color-sidebar-muted`); on the
    active pill, both in `--color-on-accent`;
  - no session: an 8 px empty ring, 1 px `--color-sidebar-muted`, no word;
  - the state is also in the accessible name: "Live monitor, session in
    progress" / "Live monitor, no session in progress". The dot and the word are
    `aria-hidden`.
  - No count, no stage, no blinking, no sound: the rail only says that a session
    is running. How it is going is the monitor's job.
- **Opens `/monitor` in the same window**, like the other rail items; that page
  follows the running session and, with none, shows "Waiting for a new session".
  **Never disabled:** opening the monitor before the session starts is the normal
  case (it waits on the second screen).
- **Tooltip** on hover and keyboard focus, UI/UX text: "Opens the live session
  monitor for {P##}, session {id8}. Read-only." / "No session in progress. The
  monitor will show the next session when it starts."
- **Data:** the same endpoint the monitor uses to find the running session; the
  rail polls it at the monitor's rate or slower. With more than one
  `IN_PROGRESS` session it follows the one with the latest event, like `/monitor`
  (D-F6-270 (3)). If the backend doesn't answer,
  the item shows the no-session ring (it never claims a session it can't see).

### 2. Link on the session view

- **Only on a session whose status is `IN_PROGRESS`.** Completed, aborted and
  not-started sessions show nothing in its place (no grey or disabled link).
- **Place:** in the header's facts column, in the row with the condition chip,
  where Export CSV sits on a closed session. Export CSV is not shown while the
  session runs (it would export half a session).
- **Form:** outline pill, 32 px tall, 16 px side padding, 1 px `--color-accent`
  border, `--color-surface` fill, `--color-accent` text, 600; the 16 px signal
  icon before the label and a 12 px external-window mark after it. Outline on
  purpose: the portal's one filled call to action stays Saffron.
- **Label:** "Open live monitor". Accessible name: "Open live monitor for
  session {id8}".
- **Opens `/monitor/<id>` of this session in a new window** (`target="_blank"`,
  `rel="noopener"`), so the session view stays where it was and the monitor can go
  to the second screen. The tooltip ends with "Opens in a new window."
- **Status** in the facts reads "In progress, {stage}" with an 8 px
  `--color-accent` dot.
- **Tooltip**, UI/UX text: "Signal quality, live indices, events and adaptation
  decisions for this session, as it runs. Read-only: it does not change the
  session. Opens in a new window."

### Answered by D-F6-270

- Window: rail in the same window, session link in a new window (as above).
- Export CSV is not shown while the session is `IN_PROGRESS`; "Open live
  monitor" takes its place.
- Several `IN_PROGRESS` sessions: one rule for the rail and `/monitor`, the
  latest event.
- When the session ends with `/monitor/<id>` open: V1.13 *Session ended*.

## Inherited constraints

- Non-clinical language across the UI.
- Meaning never by color alone (hatches, shapes, labels).
- No decorative motion; zoom and selection respond to the user only.
