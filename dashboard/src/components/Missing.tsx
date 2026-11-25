// NULL is "not recorded", never zero (skill rule 3): a dash that says why.
export function Missing({ reason }: { reason: string }) {
  return (
    <span title={reason} aria-label={reason} className="text-(--color-text-muted)">
      —
    </span>
  )
}
