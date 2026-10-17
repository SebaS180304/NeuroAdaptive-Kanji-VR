// design-system.md "Reserved slot": what does not exist yet is shown, never faked.
export function ReservedSlot({ thing, className = '' }: { thing: string; className?: string }) {
  return (
    <section
      aria-label={`${thing} (reserved)`}
      className={`type-caption rounded-(--radius-panel) border border-dashed border-(--color-border-strong) bg-(--color-border-subtle) p-6 text-(--color-text-muted) ${className}`}
    >
      {thing}: available in a later version.
    </section>
  )
}
