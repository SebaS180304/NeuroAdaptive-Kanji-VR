import { Missing } from '@/components/Missing'
import { flatten } from './flatten'

// Indicators and thresholds as the backend stored them (design-system.md, V1.4 cases):
// keys in mono, dotted when nested and free to break after a dot; arrays and objects as
// JSON on their own line, left-aligned.
export function KeyValues({ heading, values }: { heading: string; values: Record<string, unknown> | null }) {
  return (
    <div className="flex flex-col gap-2">
      <h4 className="type-caption m-0 font-medium text-(--color-text-secondary)">{heading}</h4>
      {values ? (
        <dl className="type-body m-0 grid grid-cols-[fit-content(60%)_minmax(0,1fr)] gap-x-4 gap-y-1">
          {flatten(values).map(([k, v, block]) => (
            <div key={k} className="contents">
              <dt className={`type-mono text-(--color-text-muted) ${block ? 'col-span-2' : ''}`}>
                {k.split('.').map((part, i) => <span key={i}>{i > 0 && <>.<wbr /></>}{part}</span>)}
              </dt>
              <dd className={`type-mono m-0 break-all ${block ? 'col-span-2 text-left' : 'text-right'}`}>{v}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <Missing reason="Not recorded for this decision" />
      )}
    </div>
  )
}
