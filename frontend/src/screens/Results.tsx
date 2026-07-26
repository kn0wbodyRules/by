import * as React from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { AnimatePresence, motion } from 'motion/react'
import { Icon } from '@/components/Icon'
import { Logo } from '@/components/Logo'
import { MorphPanel } from '@/components/ui/ai-input'
import { api, ApiError } from '@/lib/api'
import type { BOQResponse } from '@/types/api'

/**
 * Signature animation 2 — Confirm → Processing → Results.
 *
 * A blueprint scrolls continuously upward while the calculation runs; the field
 * colour animates navy → cream, timed to land as the work finishes; then the BOQ
 * sheet enters from the opposite direction to the blueprint's travel.
 *
 * The colour transition is driven by real progress rather than a fixed timer: it
 * completes when /calculate resolves, so a slow estimate never reveals an empty
 * sheet.
 */
export function Results() {
  const { jobId = '' } = useParams()
  const navigate = useNavigate()

  const [boq, setBoq] = React.useState<BOQResponse | null>(null)
  const [phase, setPhase] = React.useState<'processing' | 'revealing' | 'done'>('processing')
  const [error, setError] = React.useState<string | null>(null)

  /*
    /calculate is a mutation and React StrictMode runs effects twice in dev, so
    this deduplicates the *promise* rather than the effect body.

    Guarding the effect with a plain boolean ref does not work: the first run's
    cleanup marks its own result stale, the second run is skipped by the guard,
    and the screen hangs on "Going room by room" forever. Caching the promise
    lets the second run re-subscribe to the first run's in-flight request — one
    network call, and whichever mount survives still receives the result.

    Two concurrent calculates would otherwise race on the backend's
    delete-then-insert and duplicate every material line.
  */
  const pending = React.useRef<Promise<BOQResponse> | null>(null)

  React.useEffect(() => {
    let alive = true

    if (!pending.current) {
      pending.current = (async () => {
        const startedAt = Date.now()
        try {
          return await api.calculate(jobId)
        } catch (err) {
          // Re-entering an already-calculated job is a 409, not a failure — read
          // the stored BOQ rather than forcing a recalculation.
          if (err instanceof ApiError && err.status === 409) {
            return await api.getBoq(jobId)
          }
          throw err
        } finally {
          // Let the blueprint travel read as deliberate even on a fast backend.
          const elapsed = Date.now() - startedAt
          if (elapsed < 2200) {
            await new Promise((r) => setTimeout(r, 2200 - elapsed))
          }
        }
      })()
    }

    pending.current
      .then((data) => {
        if (!alive) return
        setBoq(data)
        setPhase('revealing')
        setTimeout(() => alive && setPhase('done'), 900)
      })
      .catch((err: unknown) => {
        if (!alive) return
        setError(err instanceof Error ? err.message : 'Calculation failed')
        setPhase('done')
      })

    return () => {
      alive = false
    }
  }, [jobId])

  const processing = phase === 'processing'

  return (
    <motion.main
      className="min-h-screen"
      initial={false}
      animate={{ backgroundColor: processing ? '#36355B' : '#F6E3C5' }}
      transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1] }}
    >
      <AnimatePresence>
        {processing && (
          <motion.div
            key="processing"
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
            className="fixed inset-0 z-20 flex flex-col items-center justify-center overflow-hidden"
          >
            <motion.h1
              className="font-display text-cream relative z-10 px-6 text-center text-4xl font-bold sm:text-6xl"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              Going room <em className="not-italic">by</em> room
            </motion.h1>

            {/* Continuous upward travel — two stacked copies so it never seams. */}
            <motion.div
              className="pointer-events-none absolute inset-x-0 top-0 flex flex-col items-center opacity-30"
              animate={{ y: ['0%', '-50%'] }}
              transition={{ duration: 9, repeat: Infinity, ease: 'linear' }}
            >
              <BlueprintSheet />
              <BlueprintSheet />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="mx-auto max-w-[1440px] px-6 py-8 lg:px-12">
        <header className="flex items-center justify-between">
          <button onClick={() => navigate('/dashboard')} aria-label="Back to dashboard">
            <Logo className={processing ? 'text-cream' : 'text-navy'} />
          </button>
        </header>

        <AnimatePresence>
          {boq && phase !== 'processing' && (
            // Enters from the right — the blueprint travelled up, so the sheet
            // arrives on a different axis rather than repeating the same motion.
            <motion.div
              initial={{ opacity: 0, x: 220 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.85, ease: [0.22, 1, 0.36, 1] }}
              className="mt-10"
            >
              <h1 className="font-display text-navy text-center text-4xl font-bold sm:text-5xl">
                Analyzed Room <em className="not-italic">by</em> Room
              </h1>

              <p className="font-body text-navy/60 mt-3 text-center">
                {boq.project_name} · {boq.rooms.length} rooms · {boq.location}
              </p>

              <div className="mt-8 flex flex-col items-center gap-4">
                <p className="font-ui text-navy/50 text-sm tracking-[0.2em] uppercase">
                  Download as
                </p>
                <div className="flex flex-wrap items-center justify-center gap-4">
                  <DownloadButton
                    icon="picture_as_pdf"
                    label="PDF"
                    onClick={() => api.download(jobId, 'pdf', boq.project_name)}
                    delay={0}
                  />
                  <DownloadButton
                    icon="table_view"
                    label="Excel"
                    onClick={() => api.download(jobId, 'excel', boq.project_name)}
                    delay={0.1}
                  />
                  <DownloadButton
                    icon="csv"
                    label="CSV"
                    onClick={() => api.download(jobId, 'csv', boq.project_name)}
                    delay={0.2}
                  />
                </div>
              </div>

              <BoqTable boq={boq} />
            </motion.div>
          )}
        </AnimatePresence>

        {error && (
          <div className="mt-16 text-center">
            <p className="font-ui text-destructive">{error}</p>
            <button
              onClick={() => navigate(`/confirm/${jobId}`)}
              className="font-ui text-navy mt-4 cursor-pointer underline underline-offset-4"
            >
              Back to Confirm
            </button>
          </div>
        )}
      </div>

      {boq && (
        <MorphPanel
          onSubmit={async (message) => {
            const res = await api.chat(jobId, message)
            if (res.new_calculation_required) navigate(`/rooms/${jobId}`)
            return res.reply
          }}
        />
      )}
    </motion.main>
  )
}

function BoqTable({ boq }: { boq: BOQResponse }) {
  // Every seeded rate is still placeholder data; saying so here matches the
  // disclaimer the PDF/Excel exports carry.
  const placeholderRates = boq.rooms.some((r) =>
    r.materials?.some((m) => m.correction_confidence === 'fallback'),
  )

  return (
    <section className="mt-12">
      <div className="border-navy/15 overflow-hidden rounded-[28px] border">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse text-left">
            <thead>
              <tr className="bg-navy text-cream font-ui text-sm">
                <th className="px-5 py-4">Room</th>
                <th className="px-5 py-4">Material</th>
                <th className="px-5 py-4 text-right">Qty</th>
                <th className="px-5 py-4">Unit</th>
                <th className="px-5 py-4 text-right">Rate</th>
                <th className="px-5 py-4 text-right">Amount</th>
              </tr>
            </thead>
            <tbody className="font-body text-navy">
              {boq.rooms.flatMap((room, ri) =>
                (room.materials ?? []).map((m, mi) => (
                  <motion.tr
                    key={`${room.room_id}-${m.material_name}`}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3 + (ri * 5 + mi) * 0.02 }}
                    className="border-navy/10 border-t"
                  >
                    <td className="px-5 py-3">{mi === 0 ? room.room_name : ''}</td>
                    <td className="px-5 py-3 capitalize">
                      {m.material_name.replace(/_/g, ' ')}
                    </td>
                    <td className="px-5 py-3 text-right tabular-nums">
                      {m.quantity.toFixed(2)}
                    </td>
                    <td className="px-5 py-3">{m.unit}</td>
                    <td className="px-5 py-3 text-right tabular-nums">
                      ₹{m.rate_per_unit.toLocaleString('en-IN')}
                    </td>
                    <td className="px-5 py-3 text-right tabular-nums">
                      ₹{m.total_cost.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                    </td>
                  </motion.tr>
                )),
              )}
            </tbody>
            <tfoot>
              <tr className="bg-navy/5 font-display text-navy border-navy/15 border-t-2">
                <td className="px-5 py-4 font-bold" colSpan={5}>
                  Total
                </td>
                <td className="px-5 py-4 text-right text-lg font-bold tabular-nums">
                  ₹{boq.total_cost.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {placeholderRates && (
        <p className="font-body text-navy/50 mt-4 flex items-start gap-2 text-sm">
          <Icon name="info" className="text-[18px]" />
          Quantities are uncorrected (no historical project data yet) and rates are
          placeholder values, not verified PWD Schedule of Rates figures.
        </p>
      )}
    </section>
  )
}

function DownloadButton({
  icon,
  label,
  onClick,
  delay,
}: {
  icon: string
  label: string
  onClick: () => void
  delay: number
}) {
  return (
    <motion.button
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: 0.45 + delay, type: 'spring', stiffness: 320, damping: 22 }}
      whileHover={{ y: -3 }}
      whileTap={{ scale: 0.96 }}
      onClick={onClick}
      className="border-navy/20 hover:bg-navy hover:text-cream text-navy font-ui flex cursor-pointer flex-col items-center gap-2 rounded-3xl border px-9 py-6 transition-colors"
    >
      <Icon name={icon} className="text-[36px]" />
      {label}
    </motion.button>
  )
}

/** Decorative blueprint used only during the processing phase. */
function BlueprintSheet() {
  return (
    <svg viewBox="0 0 900 700" className="w-[min(90vw,900px)] shrink-0" aria-hidden="true">
      <g stroke="#F6E3C5" strokeWidth="1" strokeOpacity="0.35" fill="none">
        {Array.from({ length: 15 }, (_, i) => (
          <line key={`h${i}`} x1="0" y1={i * 50} x2="900" y2={i * 50} />
        ))}
        {Array.from({ length: 19 }, (_, i) => (
          <line key={`v${i}`} x1={i * 50} y1="0" x2={i * 50} y2="700" />
        ))}
      </g>
      <g stroke="#F6E3C5" strokeWidth="3" fill="none">
        <rect x="80" y="70" width="360" height="250" />
        <rect x="460" y="70" width="360" height="250" />
        <rect x="80" y="340" width="230" height="290" />
        <rect x="330" y="340" width="230" height="290" />
        <rect x="580" y="340" width="240" height="290" />
        <line x1="230" y1="320" x2="290" y2="320" strokeWidth="6" />
        <line x1="620" y1="320" x2="680" y2="320" strokeWidth="6" />
      </g>
    </svg>
  )
}
