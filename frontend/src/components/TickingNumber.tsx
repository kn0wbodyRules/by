import * as React from 'react'
import { animate, motion, useMotionValue, useTransform } from 'motion/react'

/**
 * Numeric field whose displayed value counts to its target instead of snapping —
 * the "values tick up/down" behaviour from the design brief. Typing is
 * unaffected; the tween only runs when the value changes from outside (stepper
 * buttons, resets, loading a different room).
 */
export function TickingNumber({
  label,
  value,
  onChange,
  step = 1,
  min = 0,
  suffix,
  decimals = 0,
}: {
  label: string
  value: number
  onChange: (v: number) => void
  step?: number
  min?: number
  suffix?: string
  decimals?: number
}) {
  const [editing, setEditing] = React.useState(false)
  const [draft, setDraft] = React.useState(String(value))

  const motionValue = useMotionValue(value)
  const display = useTransform(motionValue, (v) => v.toFixed(decimals))

  React.useEffect(() => {
    if (editing) return
    const controls = animate(motionValue, value, {
      duration: 0.45,
      ease: [0.22, 1, 0.36, 1],
    })
    return controls.stop
  }, [value, motionValue, editing])

  function commit(raw: string) {
    const parsed = Number.parseFloat(raw)
    onChange(Number.isFinite(parsed) ? Math.max(min, parsed) : min)
    setEditing(false)
  }

  return (
    <div className="border-navy/10 flex items-center justify-between gap-4 border-b py-3">
      <span className="font-ui text-navy/70">{label}</span>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => onChange(Math.max(min, +(value - step).toFixed(2)))}
          aria-label={`Decrease ${label}`}
          className="text-navy/50 hover:text-navy hover:bg-navy/5 grid h-7 w-7 cursor-pointer place-items-center rounded-full transition-colors"
        >
          −
        </button>

        {editing ? (
          <input
            autoFocus
            value={draft}
            inputMode="decimal"
            onChange={(e) => setDraft(e.target.value)}
            onBlur={(e) => commit(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commit((e.target as HTMLInputElement).value)
              if (e.key === 'Escape') setEditing(false)
            }}
            aria-label={label}
            className="font-display text-navy w-16 bg-transparent text-right text-xl font-bold outline-none"
          />
        ) : (
          <button
            type="button"
            onClick={() => {
              setDraft(String(value))
              setEditing(true)
            }}
            className="font-display text-navy w-16 cursor-text text-right text-xl font-bold"
            aria-label={`${label}: ${value}${suffix ? ` ${suffix}` : ''}`}
          >
            <motion.span>{display}</motion.span>
          </button>
        )}

        {suffix && <span className="font-ui text-navy/40 w-6 text-sm">{suffix}</span>}

        <button
          type="button"
          onClick={() => onChange(+(value + step).toFixed(2))}
          aria-label={`Increase ${label}`}
          className="text-navy/50 hover:text-navy hover:bg-navy/5 grid h-7 w-7 cursor-pointer place-items-center rounded-full transition-colors"
        >
          +
        </button>
      </div>
    </div>
  )
}
