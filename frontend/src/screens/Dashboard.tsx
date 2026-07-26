import * as React from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'motion/react'
import { Icon } from '@/components/Icon'
import { Logo } from '@/components/Logo'
import { api, auth } from '@/lib/api'
import type { JobOut, JobStatus } from '@/types/api'
import { cn } from '@/lib/utils'

const TABS = ['Bill of Quantity', 'BOP', 'FPG'] as const
type Tab = (typeof TABS)[number]

/** Where a job should resume, based on how far through the flow it got. */
function routeForJob(job: JobOut): string {
  const map: Partial<Record<JobStatus, string>> = {
    uploaded: `/rooms/${job.id}`,
    rooms_detected: `/rooms/${job.id}`,
    rooms_manual: `/rooms/${job.id}`,
    rooms_confirmed: `/constraints/${job.id}`,
    constraints_set: `/confirm/${job.id}`,
    calculated: `/results/${job.id}`,
    exported: `/results/${job.id}`,
  }
  return map[job.status] ?? `/rooms/${job.id}`
}

export function Dashboard() {
  const navigate = useNavigate()
  const fileInput = React.useRef<HTMLInputElement>(null)

  const [tab, setTab] = React.useState<Tab>('Bill of Quantity')
  const [plans, setPlans] = React.useState<JobOut[]>([])
  const [selected, setSelected] = React.useState<string | null>(null)
  const [query, setQuery] = React.useState('')
  const [busy, setBusy] = React.useState<string | null>(null)
  const [error, setError] = React.useState<string | null>(null)

  // Read from the account rather than local storage, so the name follows the
  // user to any browser — and OAuth sign-ins bring one along automatically.
  const [displayName, setDisplayName] = React.useState('Estimator')

  const load = React.useCallback(async () => {
    try {
      setPlans(await api.listPlans())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load plans')
    }
  }, [])

  React.useEffect(() => {
    void load()
    void api
      .me()
      .then((user) => setDisplayName(user.name || user.email.split('@')[0] || 'Estimator'))
      // A failed profile fetch shouldn't blank the dashboard — the greeting just
      // stays generic.
      .catch(() => undefined)
  }, [load])

  const visible = plans.filter((p) =>
    p.project_name.toLowerCase().includes(query.trim().toLowerCase()),
  )

  async function handleUpload(file: File) {
    setError(null)
    setBusy('Uploading floor plan…')
    try {
      const { job_id } = await api.upload(file, file.name.replace(/\.[^.]+$/, ''))
      setBusy('Reading the plan…')
      await api.detectRooms(job_id)
      navigate(`/rooms/${job_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
      setBusy(null)
    }
  }

  async function handleManual() {
    setError(null)
    setBusy('Creating project…')
    try {
      const { job_id } = await api.createManualJob('Untitled Project')
      setBusy(null)
      navigate(`/rooms/${job_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create project')
      setBusy(null)
    }
  }

  async function handleDelete() {
    if (!selected) return
    setError(null)
    try {
      await api.deletePlan(selected)
      setSelected(null)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  return (
    <motion.main
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="bg-navy text-cream min-h-screen"
    >
      <div className="mx-auto max-w-[1440px] px-6 py-8 lg:px-12">
        <header className="flex flex-wrap items-center gap-6">
          <Logo animateFromIntro className="text-cream text-5xl" />

          <nav className="border-cream/15 bg-cream/5 flex flex-1 items-center gap-1 rounded-full border p-1 backdrop-blur">
            {TABS.map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={cn(
                  'font-ui relative cursor-pointer rounded-full px-5 py-2 text-sm transition-colors',
                  tab === t ? 'text-navy' : 'text-cream/60 hover:text-cream',
                )}
              >
                {tab === t && (
                  <motion.span
                    layoutId="dashboard-tab"
                    className="bg-cream absolute inset-0 rounded-full"
                    transition={{ type: 'spring', stiffness: 380, damping: 32 }}
                  />
                )}
                <span className="relative">{t}</span>
              </button>
            ))}

            <div className="ml-auto flex items-center gap-2 px-3">
              <Icon name="search" className="text-cream/50 text-[20px]" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search plans"
                className="font-body text-cream placeholder:text-cream/35 w-32 bg-transparent outline-none sm:w-48"
              />
            </div>
          </nav>

          <button
            onClick={() => {
              auth.clear()
              navigate('/login')
            }}
            className="font-ui text-cream/60 hover:text-cream cursor-pointer text-sm"
          >
            Sign out
          </button>
        </header>

        <AnimatePresence mode="wait">
          {tab !== 'Bill of Quantity' ? (
            <motion.section
              key={tab}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              className="border-cream/15 mt-10 grid min-h-[420px] place-items-center rounded-[32px] border border-dashed"
            >
              <div className="text-center">
                <Icon name="construction" className="text-cream/40 text-[48px]" />
                <p className="font-display text-cream mt-4 text-2xl">{tab}</p>
                <p className="font-body text-cream/50 mt-2">Coming soon</p>
              </div>
            </motion.section>
          ) : (
            <motion.section
              key="boq"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              className="mt-10 grid gap-8 lg:grid-cols-[minmax(280px,390px)_1fr]"
            >
              <aside className="bg-cream/8 border-cream/15 h-fit rounded-[32px] border p-7 backdrop-blur-md">
                <div className="flex flex-col items-center text-center">
                  <div className="bg-cream/15 text-cream grid h-16 w-16 place-items-center rounded-full">
                    <Icon name="person" className="text-[32px]" />
                  </div>
                  <p className="font-display text-cream mt-4 text-xl font-bold">
                    {displayName}
                  </p>
                  <p className="font-ui text-cream/50 mt-1 text-sm tracking-[0.2em] uppercase">
                    Welcome
                  </p>
                </div>

                <div className="bg-cream/15 my-6 h-px" />

                <div className="space-y-3">
                  <SidebarAction
                    icon="upload_file"
                    label="Upload Plan"
                    onClick={() => fileInput.current?.click()}
                  />
                  <SidebarAction
                    icon="edit_note"
                    label="Manually enter plan"
                    onClick={handleManual}
                  />
                  <SidebarAction
                    icon="delete"
                    label="Delete Plan"
                    onClick={handleDelete}
                    disabled={!selected}
                    hint={selected ? undefined : 'Select a plan first'}
                  />
                </div>

                <input
                  ref={fileInput}
                  type="file"
                  accept="image/*,.pdf"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) void handleUpload(file)
                    e.target.value = ''
                  }}
                />
              </aside>

              <div>
                {error && (
                  <p className="font-ui text-destructive bg-destructive/10 mb-4 rounded-2xl px-4 py-3 text-sm">
                    {error}
                  </p>
                )}

                {visible.length === 0 ? (
                  <div className="border-cream/15 grid min-h-[300px] place-items-center rounded-[32px] border border-dashed text-center">
                    <div>
                      <p className="font-display text-cream text-xl">
                        {plans.length === 0 ? 'No plans yet' : 'Nothing matches that search'}
                      </p>
                      <p className="font-body text-cream/50 mt-2">
                        {plans.length === 0
                          ? 'Upload a floor plan, or enter rooms manually to begin.'
                          : 'Try a different name.'}
                      </p>
                    </div>
                  </div>
                ) : (
                  <ul className="space-y-5">
                    {visible.map((plan, i) => (
                      <motion.li
                        key={plan.id}
                        initial={{ opacity: 0, y: 24 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.07, duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
                      >
                        <PlanCard
                          plan={plan}
                          selected={selected === plan.id}
                          onSelect={() => setSelected(plan.id === selected ? null : plan.id)}
                          onOpen={() => navigate(routeForJob(plan))}
                        />
                      </motion.li>
                    ))}
                  </ul>
                )}
              </div>
            </motion.section>
          )}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {busy && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="bg-navy/80 fixed inset-0 z-50 grid place-items-center backdrop-blur-sm"
          >
            <p className="font-display text-cream text-2xl">{busy}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.main>
  )
}

function SidebarAction({
  icon,
  label,
  onClick,
  disabled,
  hint,
}: {
  icon: string
  label: string
  onClick: () => void
  disabled?: boolean
  hint?: string
}) {
  return (
    <motion.button
      onClick={onClick}
      disabled={disabled}
      title={hint}
      // Without this the title attribute wins the accessible-name calculation,
      // so the button announces "Select a plan first" instead of "Delete Plan".
      aria-label={hint ? `${label} — ${hint}` : label}
      whileTap={disabled ? undefined : { scale: 0.98 }}
      className={cn(
        'font-ui border-cream/15 flex w-full items-center gap-3 rounded-2xl border px-5 py-4 text-left transition-colors',
        disabled
          ? 'text-cream/30 cursor-not-allowed'
          : 'text-cream hover:bg-cream hover:text-navy cursor-pointer',
      )}
    >
      <Icon name={icon} className="text-[22px]" />
      {label}
    </motion.button>
  )
}

function PlanCard({
  plan,
  selected,
  onSelect,
  onOpen,
}: {
  plan: JobOut
  selected: boolean
  onSelect: () => void
  onOpen: () => void
}) {
  const status = plan.status.replace(/_/g, ' ')
  return (
    <div
      className={cn(
        'group border-cream/15 bg-cream/8 relative flex items-center gap-6 rounded-[28px] border p-6 backdrop-blur-md transition-all',
        'hover:bg-cream/15 hover:backdrop-blur-xl',
        selected && 'border-cream/60 bg-cream/15',
      )}
    >
      <button
        onClick={onSelect}
        aria-label={selected ? `Deselect ${plan.project_name}` : `Select ${plan.project_name}`}
        className={cn(
          'grid h-6 w-6 shrink-0 cursor-pointer place-items-center rounded-full border transition-colors',
          selected ? 'bg-cream border-cream text-navy' : 'border-cream/40',
        )}
      >
        {selected && <Icon name="check" className="text-[16px]" />}
      </button>

      <button onClick={onOpen} className="flex-1 cursor-pointer text-left">
        <p className="font-display text-cream text-2xl font-bold">{plan.project_name}</p>
        <p className="font-ui text-cream/60 mt-1 text-sm capitalize">
          {status} · {plan.location}
        </p>
        {plan.total_cost != null && (
          <p className="font-body text-cream/80 mt-2">
            ₹{plan.total_cost.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </p>
        )}
      </button>

      <Icon
        name="arrow_forward"
        className="text-cream/40 group-hover:text-cream text-[24px] transition-colors"
      />
    </div>
  )
}
