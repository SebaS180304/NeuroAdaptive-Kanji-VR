# Design rules (anti-generic) and final audit

Set by Sebas on Oct 16. They apply to **every** iteration of the dashboard: the
mockups in the design chat and the code in the dev chat. Where a rule was written
for marketing pages, the dashboard reading is given under it.

## 1 · Typography

> Avoid generic UI fonts like Inter, Roboto, or Arial. Use a distinct font
> pairing. For headings, use [e.g., Playfair Display / Cabinet Grotesk /
> Newsreader]; for body text, use [e.g., Public Sans / General Sans / Source
> Serif 4]. Specify exact font-size, line-height, and letter-spacing values in rem
> or px rather than generic size classes.

- Also off the list: Geist (it is Vercel's house face), system-ui as the design
  face, and any font chosen only because it is a framework default.
- Every text style is a named token with exact `font-size`, `line-height`,
  `letter-spacing` and weight (see `design-system.md`). No `text-sm`/`text-lg`
  without a mapped token.
- Fonts are bundled locally (no runtime Google Fonts), per the local-only rule.

## 2 · Color

> Strictly prohibit purple, indigo, or violet gradients. Build a tight,
> restricted color palette: a deep non-black primary background ([e.g., #0F1115
> or warm cream #F9F8F6]), an assertive dominant accent color, and a sharp
> contrasting call-to-action color. No muddy mid-tones or random neon glows.

- No gradients as decoration at all; the only "gradient-like" fills allowed are
  hatch patterns that encode data (e.g. incorrect trials, uncertain outcome).
- Data colors (conditions, ESL/LAL, states, outcomes) are derived from the same
  restricted palette (tints of the accent and CTA hues plus one alert color), not
  a separate rainbow.
- Text contrast AA minimum, checked numerically.

## 3 · Component rhythm

> Do not default to the standard 3-column feature card grid. Vary the component
> rhythm: mix editorial text blocks, asymmetric split-screens, data callouts, or
> interactive elements. Every section must serve a distinct visual purpose with
> intentional whitespace and grid alignment.

- Dashboard reading: no row of identical KPI cards. Summary figures go in an
  asymmetric split (ruled definition list, a per-state strip, a breakdown block),
  each with its own form because each answers a different question.
- Everything aligns to the 16-column grid and the 8 px mini unit (see
  `design-system.md`).

## 4 · Corners and shadows

> Border-radius rules: do not apply the exact same rounded corner to every
> element. Vary sharpness (e.g., sharp 0px/4px structural blocks paired with
> pill-shaped buttons). Shadows must be soft and directional (layered
> soft-diffused shadows), never harsh black drops.

- Radius encodes role: structural panels and tables sharp; inputs slightly
  rounded; buttons and chips pill. Values in `design-system.md`.
- Shadows only on genuinely elevated elements (the inspector, popovers), as a
  layered, downward, low-alpha, ink-tinted stack. Flat panels use a 1 px hairline.

## 5 · Final audit (mandatory, end of every iteration)

> Audit the code/design you just generated against the 5 classic AI-slop tells:
> (1) generic typeface, (2) indigo/violet fade, (3) three identical feature cards,
> (4) uniform rounded corners, and (5) lazy frosted-glass overlays. Name every
> single one that you accidentally used and rewrite those sections.

How to report it: a five-row table (tell · found? · where · fix) in the reply to
Sebas, after the fixes are applied. "Not found" needs a one-line reason, not a
bare "no". Also check the secondary tells: all-caps labels, middle-dot meta
strings, monospace for every small label, `→` appended to links/buttons.

## 6 · Reference analysis (design chat only)

> Research avant-garde web pages and contrast them with ours. Analyze the
> typography scale, grid spacing, corner radius, and color values of the
> reference. Rebuild the layout of my page to match these exact structural
> numbers instead of guessing generic styles.

The dev chat does not redo this: it implements the numbers the design chat
recorded in `design-system.md`. If a needed number is missing there, it asks.

## 7 · Who decides what, and how validation is recorded (Oct 16 sync)

- Design chat: how things look (tokens, layout, components).
- Dev chat: implementation and API data. If a design needs data the API does not
  have, the dev chat says so instead of faking it.
- Sebas: scope, which screens exist, and whether a design is validated.
- When Sebas validates a mockup, the design chat records the date and the URL in
  the validation log of `design-system.md`. A screen without a *Validated* row is
  not built.
- The master copy of the skill is the repo's `.claude/skills/research-dashboard-conventions/`.
  The design chat sends back only the files it changed (`design-system.md`,
  `design-rules.md`); it never edits `scope-and-roadmap.md`, `data-contract.md`
  or `stack-and-structure.md`.

## 8 · Screens the participant sees (V1.10)

- No sidebar, no decorative elements, no motion and no sound while a kanji is on
  screen.
- Nothing on a participant-facing screen reveals an answer: no correct reading
  or meaning anywhere. Set names and "substitute" labels never appear on the
  kanji screen.
- Researcher-only content is visibly separated (the dark researcher strip, or the
  gated details on the summary) and labeled as such.
