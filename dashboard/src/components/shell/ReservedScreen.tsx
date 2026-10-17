import { ReservedSlot } from '@/components/reserved/ReservedSlot'

// A route whose screen is not built yet: its title, and a reserved slot in its place.
// The title spans columns 1-9, and the full width below 1056 px (design-system.md).
export function ReservedScreen({ title, thing }: { title: string; thing: string }) {
  return (
    <>
      <header className="col-span-16 min-[1056px]:col-span-9">
        <h1 className="type-display m-0">{title}</h1>
      </header>
      <ReservedSlot thing={thing} className="col-span-16" />
    </>
  )
}
