# Feature spec · <ID> <Name>

Template to plan and design dashboard features outside v1 (see the roadmap in
`references/scope-and-roadmap.md`). Saved in the Project as
`claude/Dashboard_Feature_<ID>.md`.

| Field | Value |
| --- | --- |
| ID | F-XXX |
| Status | Idea / Planned / Design validated / In dev / Done |
| Project phase | |
| Planned by (PM chat) | date |
| Design validated by Sebas | date + mockup URL |

## 1 · Goal

Which research question it answers. One or two sentences.

## 2 · Data dependencies

- Tables / views / events it needs (checked against `schema.sql`).
- Do they exist already? If not, which phase creates them.
- New endpoints (`GET`) and response shape.
- NULL vs 0: which fields did not exist in older sessions.

## 3 · Hook

Which v1 reserved slot it replaces, or which screen it extends.

## 4 · Design (filled in by the UI/UX chat)

- Mockup in Claude Design (URL) and states: with data, empty, NULL, error, loading.
- New tokens (if needed) → added to the Design System artifact first.
- New components or variants.
- Interpretation risks (non-clinical language, color per condition).

## 5 · Definition of done

- Verifiable with a real session (which one).
- Playwright screenshot matches the mockup.
- No regressions in v1.

## 6 · Out of scope

## 7 · Open decisions
