import type { Schemas } from '@/api/client'

// Notes for the researcher, one rule for V1.11 and V1.8 (design-system.md, V1.8 "Notes in the facts").

export function participantNotes(p: Schemas['ResearchParticipant']): string[] {
  return [
    ...(p.previous_japanese_experience ? ['Previous Japanese study reported'] : []),
    ...(p.flagged_count ? ['Kanji kept with no substitute'] : []),
  ]
}

export function NoteList({ notes }: { notes: string[] }) {
  return (
    <span className="flex flex-col gap-1">
      {notes.map((n) => (
        <span key={n} className="inline-flex items-center gap-2">
          <svg aria-hidden="true" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="var(--color-lal-high)" strokeWidth="1.6">
            <path d="M8 1.8L15 14H1z" />
            <path d="M8 6.2v3.8M8 11.6v.3" />
          </svg>
          {n}
        </span>
      ))}
    </span>
  )
}
