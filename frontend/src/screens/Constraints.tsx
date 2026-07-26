import * as React from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { AnimatePresence, motion } from 'motion/react'
import { FlowChrome } from '@/components/FlowChrome'
import { Icon } from '@/components/Icon'
import { MorphPanel } from '@/components/ui/ai-input'
import { api } from '@/lib/api'
import type { MaterialOverride } from '@/types/api'
import { cn } from '@/lib/utils'

/**
 * Slider materials mirror the Figma screen. The backend takes a single
 * `budget_cap` plus grade/brand overrides, so these per-material allowances are
 * summed into that cap — they read as an allocation breakdown to the user while
 * still sending the contract's shape.
 */
const MATERIALS = [
  { key: 'bricks', label: 'Bricks', max: 40000, low: 6000 },
  { key: 'rods', label: 'Rods', max: 40000, low: 8000 },
  { key: 'paint', label: 'Paint', max: 20000, low: 4000 },
  { key: 'tiles', label: 'Tiles', max: 40000, low: 7000 },
  { key: 'plaster', label: 'Plaster', max: 20000, low: 3500 },
] as const

const GRADES = ['standard', 'premium', 'economy'] as const

export function Constraints() {
  const { jobId = '' } = useParams()
  const navigate = useNavigate()

  const [budget, setBudget] = React.useState<Record<string, number>>({
    bricks: 10000,
    rods: 8000,
    paint: 5000,
    tiles: 10000,
    plaster: 10000,
  })
  const [grades, setGrades] = React.useState<Record<string, string>>({})
  const [quality, setQuality] = React.useState<(typeof GRADES)[number]>('standard')
  const [open, setOpen] = React.useState<'price' | 'materials' | 'quality' | null>('price')
  const [warnings, setWarnings] = React.useState<string[]>([])
  const [error, setError] = React.useState<string | null>(null)
  const [saving, setSaving] = React.useState(false)

  const total = Object.values(budget).reduce((a, b) => a + b, 0)
  const lowQuality = MATERIALS.filter((m) => budget[m.key] < m.low)

  function overrides(): MaterialOverride[] {
    return Object.entries(grades)
      .filter(([, grade]) => grade && grade !== 'standard')
      .map(([material_name, preferred_grade_or_brand]) => ({
        material_name,
        preferred_grade_or_brand,
      }))
  }

  async function handleNext() {
    setError(null)
    setSaving(true)
    try {
      const res = await api.setConstraints(jobId, total, overrides())
      setWarnings(res.warnings)
      // Warnings are advisory, not blocking — the backend accepted the values.
      navigate(`/confirm/${jobId}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save constraints')
    } finally {
      setSaving(false)
    }
  }

  return (
    <FlowChrome step="Constraints and Exclusions">
      <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_minmax(300px,380px)]">
        <div className="space-y-4">
          <Accordion
            title="Price"
            icon="payments"
            open={open === 'price'}
            onToggle={() => setOpen(open === 'price' ? null : 'price')}
            summary={`₹${total.toLocaleString('en-IN')}`}
          >
            <p className="font-body text-navy/60 mb-6 text-sm">
              Allowance per material. Ranges depend on plot quality and finish level —
              these set the overall budget the estimate is checked against.
            </p>

            <div className="space-y-6">
              {MATERIALS.map((m) => {
                const value = budget[m.key]
                const isLow = value < m.low
                return (
                  <div key={m.key}>
                    <div className="flex items-baseline justify-between">
                      <label htmlFor={m.key} className="font-display text-navy text-lg font-bold">
                        {m.label}
                      </label>
                      <span className="font-body text-navy tabular-nums">
                        ₹{value.toLocaleString('en-IN')}
                      </span>
                    </div>

                    <input
                      id={m.key}
                      type="range"
                      min={0}
                      max={m.max}
                      step={500}
                      value={value}
                      onChange={(e) =>
                        setBudget((b) => ({ ...b, [m.key]: Number(e.target.value) }))
                      }
                      className="accent-navy mt-2 w-full cursor-pointer"
                    />

                    <AnimatePresence>
                      {isLow && (
                        <motion.p
                          initial={{ opacity: 0, x: -6 }}
                          animate={{
                            opacity: 1,
                            x: [0, -3, 3, -2, 2, 0],
                            transition: { x: { duration: 0.4 } },
                          }}
                          exit={{ opacity: 0 }}
                          className="font-ui text-destructive mt-2 flex items-center gap-2 text-sm"
                        >
                          <Icon name="warning" className="text-[18px]" />
                          Price range too low for good quality {m.label.toLowerCase()}
                        </motion.p>
                      )}
                    </AnimatePresence>
                  </div>
                )
              })}
            </div>
          </Accordion>

          <Accordion
            title="Materials"
            icon="category"
            open={open === 'materials'}
            onToggle={() => setOpen(open === 'materials' ? null : 'materials')}
            summary={`${overrides().length} override${overrides().length === 1 ? '' : 's'}`}
          >
            <p className="font-body text-navy/60 mb-5 text-sm">
              Pin a specific grade or brand for any material. Anything left on standard
              uses the schedule-of-rates default.
            </p>
            <div className="space-y-3">
              {MATERIALS.map((m) => (
                <div key={m.key} className="border-navy/10 flex items-center gap-3 border-b py-2">
                  <span className="font-ui text-navy/70 flex-1">{m.label}</span>
                  <input
                    value={grades[m.key] ?? ''}
                    onChange={(e) => setGrades((g) => ({ ...g, [m.key]: e.target.value }))}
                    placeholder="standard"
                    aria-label={`${m.label} grade or brand`}
                    className="font-body text-navy placeholder:text-navy/30 w-40 bg-transparent text-right outline-none"
                  />
                </div>
              ))}
            </div>
          </Accordion>

          <Accordion
            title="Quality"
            icon="workspace_premium"
            open={open === 'quality'}
            onToggle={() => setOpen(open === 'quality' ? null : 'quality')}
            summary={quality}
          >
            <p className="font-body text-navy/60 mb-5 text-sm">
              A quick preset. Applies the chosen grade to every material that doesn't
              already have an explicit override.
            </p>
            <div className="flex flex-wrap gap-3">
              {GRADES.map((g) => (
                <button
                  key={g}
                  onClick={() => {
                    setQuality(g)
                    setGrades((prev) => {
                      const next = { ...prev }
                      for (const m of MATERIALS) if (!prev[m.key]) next[m.key] = g
                      return next
                    })
                  }}
                  className={cn(
                    'font-ui cursor-pointer rounded-full border px-5 py-2 capitalize transition-colors',
                    quality === g
                      ? 'bg-navy text-cream border-navy'
                      : 'border-navy/20 text-navy hover:bg-navy/5',
                  )}
                >
                  {g}
                </button>
              ))}
            </div>
          </Accordion>
        </div>

        <aside className="bg-cream h-fit rounded-[32px] p-7">
          <p className="font-ui text-navy/50 text-sm tracking-[0.18em] uppercase">
            Total budget
          </p>
          <p className="font-display text-navy mt-2 text-4xl font-bold">
            ₹{total.toLocaleString('en-IN')}
          </p>

          {lowQuality.length > 0 && (
            <p className="font-body text-destructive mt-4 text-sm">
              {lowQuality.length} material{lowQuality.length === 1 ? '' : 's'} below the
              recommended range.
            </p>
          )}

          {warnings.length > 0 && (
            <ul className="font-body text-navy/70 mt-4 space-y-2 text-sm">
              {warnings.map((w) => (
                <li key={w} className="flex gap-2">
                  <Icon name="info" className="text-[18px]" />
                  {w}
                </li>
              ))}
            </ul>
          )}

          {error && (
            <p className="font-ui text-destructive mt-4 text-sm" role="alert">
              {error}
            </p>
          )}

          <motion.button
            onClick={handleNext}
            disabled={saving}
            whileTap={{ scale: 0.98 }}
            className="bg-navy text-cream font-ui mt-7 w-full cursor-pointer rounded-full py-4 disabled:opacity-60"
          >
            {saving ? 'Saving…' : 'Continue to Confirm'}
          </motion.button>
        </aside>
      </div>

      <MorphPanel
        onSubmit={async (message) => {
          const res = await api.chat(jobId, message)
          return res.reply
        }}
      />
    </FlowChrome>
  )
}

function Accordion({
  title,
  icon,
  open,
  onToggle,
  summary,
  children,
}: {
  title: string
  icon: string
  open: boolean
  onToggle: () => void
  summary?: string
  children: React.ReactNode
}) {
  return (
    <section className="bg-cream overflow-hidden rounded-[32px]">
      <button
        onClick={onToggle}
        aria-expanded={open}
        className="flex w-full cursor-pointer items-center gap-4 px-7 py-6 text-left"
      >
        <Icon name={icon} className="text-navy text-[26px]" />
        <span className="font-display text-navy flex-1 text-2xl font-bold">{title}</span>
        {summary && !open && (
          <span className="font-ui text-navy/50 text-sm capitalize">{summary}</span>
        )}
        <motion.span animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.25 }}>
          <Icon name="expand_more" className="text-navy/60 text-[24px]" />
        </motion.span>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="px-7 pb-7">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  )
}
