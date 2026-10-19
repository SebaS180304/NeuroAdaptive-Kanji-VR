import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'

// V1.9 Export CSV: the CTA opens a menu (plan.md, decided 17 Oct) in the elevated
// popover style. WAI-ARIA menu button: Enter, Space or the arrows open it; the arrows
// move and wrap; Esc closes and returns focus; Tab or a click outside closes.

type Item = { label: string; kind: 'trials' | 'adaptations'; disabled?: string }

export function ExportMenu({ sessionId, condition }: { sessionId: string; condition: string }) {
  const [open, setOpen] = useState(false)
  const button = useRef<HTMLButtonElement>(null)
  const items = useRef<(HTMLAnchorElement | null)[]>([])
  const box = useRef<HTMLDivElement>(null)
  const menuId = useId()
  const ITEMS: Item[] = [
    { label: 'Trials (CSV)', kind: 'trials' },
    { label: 'Adaptations (CSV)', kind: 'adaptations', disabled: condition === 'STATIC' ? 'No adaptations in a static session' : undefined },
  ]

  const focusItem = (i: number) => items.current[(i + ITEMS.length) % ITEMS.length]?.focus()
  // The item to focus once the menu mounts (its ref callback runs after the items' refs).
  const pending = useRef<number | null>(null)
  function show(at: number) {
    pending.current = at
    setOpen(true)
  }
  function close(refocus: boolean) {
    setOpen(false)
    if (refocus) button.current?.focus()
  }

  useEffect(() => {
    if (!open) return
    const outside = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false) }
    document.addEventListener('mousedown', outside)
    return () => document.removeEventListener('mousedown', outside)
  }, [open])

  function onButtonKey(e: KeyboardEvent) {
    if (e.key === 'ArrowDown') { e.preventDefault(); show(0) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); show(ITEMS.length - 1) }
  }
  function onMenuKey(e: KeyboardEvent, i: number) {
    if (e.key === 'ArrowDown') { e.preventDefault(); focusItem(i + 1) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); focusItem(i - 1) }
    else if (e.key === 'Home') { e.preventDefault(); focusItem(0) }
    else if (e.key === 'End') { e.preventDefault(); focusItem(ITEMS.length - 1) }
    else if (e.key === 'Escape') { e.preventDefault(); close(true) }
    else if (e.key === 'Tab') close(false)
  }

  return (
    <div ref={box} className="relative">
      <button
        ref={button}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => (open ? close(false) : show(0))}
        onKeyDown={onButtonKey}
        className="type-body h-8 rounded-(--radius-pill) bg-(--color-cta) px-5 font-semibold text-(--color-on-cta)"
      >
        Export CSV
      </button>
      {open && (
        <div
          ref={(el) => {
            if (el && pending.current !== null) { focusItem(pending.current); pending.current = null }
          }}
          id={menuId}
          role="menu"
          aria-label="Export CSV"
          className="absolute right-0 z-10 mt-2 flex min-w-60 flex-col rounded-(--radius-input) bg-(--color-surface-raised) p-1 shadow-(--shadow-raised)"
        >
          {ITEMS.map((it, i) => (
            <a
              key={it.kind}
              ref={(el) => { items.current[i] = el }}
              role="menuitem"
              tabIndex={-1}
              {...(it.disabled
                ? { 'aria-disabled': true }
                : { href: `/api/research/sessions/${sessionId}/export.csv?kind=${it.kind}`, download: true, onClick: () => close(true) })}
              onKeyDown={(e) => onMenuKey(e, i)}
              className={`type-body flex flex-col rounded-(--radius-input) px-3 py-2 no-underline outline-none focus:bg-(--color-selected-row) ${
                it.disabled ? 'cursor-not-allowed text-(--color-text-muted)' : 'text-(--color-text) hover:bg-(--color-selected-row)'}`}
            >
              {it.label}
              {it.disabled && <span className="type-caption text-(--color-text-muted)">{it.disabled}</span>}
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
