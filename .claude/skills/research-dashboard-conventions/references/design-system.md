# Design system · v1 (approved Oct 16)

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
| V1.7 Data quality | *V1.7 Data quality* | Validated | Oct 17 2026, 00:02 |
| V1.8 Participant View | *V1.8 Participant View* (Tweaks: `pretestDone` shows the "Open the pre-test" state) | Validated | Oct 17 2026, 00:02 |
| V1.10 Kanji pre-test | *V1.10 …* row (pick, register, one kanji, complete, states) and its dark row; summary without substitutions (Sebas, Oct 16, 23:57) | Validated | Oct 17 2026, 00:02 |
| V1.11 Participant list (needs a scope entry from the dev chat) | *V1.11 Participant list (proposed)* and its dark artboard | Validated | Oct 17 2026, 00:20 |

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
| Condition chip | `badge` | 32 px (header) / 24 px (tables), pill. Static: border-subtle fill + text-secondary. Behavior-adaptive: accent tint + on-accent-tint. Multimodal-adaptive (Oct 18): multimodal tint fill, multimodal text and a 1 px `--color-condition-multimodal` border, so it never reads as a warning notice. Unknown: dashed `--color-border-strong`, muted text. All four are drawn on the *Tokens* artboard |
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

## Inherited constraints

- Non-clinical language across the UI.
- Meaning never by color alone (hatches, shapes, labels).
- No decorative motion; zoom and selection respond to the user only.
