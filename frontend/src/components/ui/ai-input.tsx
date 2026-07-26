import React from 'react'
import { cx } from 'class-variance-authority'
import { AnimatePresence, motion } from 'motion/react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import styles from '@/components/ui/color-orb.module.css'

interface OrbProps {
  dimension?: string
  className?: string
  tones?: {
    base?: string
    accent1?: string
    accent2?: string
    accent3?: string
  }
  spinDuration?: number
}

const ColorOrb: React.FC<OrbProps> = ({
  dimension = '192px',
  className,
  tones,
  spinDuration = 20,
}) => {
  // Brand palette rather than the component's default pink/cyan/violet, so the
  // agent reads as part of "by" instead of a bolted-on widget.
  const fallbackTones = {
    base: 'oklch(93% 0.04 85)',
    accent1: 'oklch(38% 0.08 285)',
    accent2: 'oklch(86% 0.07 80)',
    accent3: 'oklch(52% 0.1 290)',
  }

  const palette = { ...fallbackTones, ...tones }

  const dimValue = parseInt(dimension.replace('px', ''), 10)

  const blurStrength =
    dimValue < 50 ? Math.max(dimValue * 0.008, 1) : Math.max(dimValue * 0.015, 4)

  const contrastStrength =
    dimValue < 50 ? Math.max(dimValue * 0.004, 1.2) : Math.max(dimValue * 0.008, 1.5)

  const pixelDot =
    dimValue < 50 ? Math.max(dimValue * 0.004, 0.05) : Math.max(dimValue * 0.008, 0.1)

  const shadowRange =
    dimValue < 50 ? Math.max(dimValue * 0.004, 0.5) : Math.max(dimValue * 0.008, 2)

  const maskRadius =
    dimValue < 30 ? '0%' : dimValue < 50 ? '5%' : dimValue < 100 ? '15%' : '25%'

  const adjustedContrast =
    dimValue < 30 ? 1.1 : dimValue < 50 ? Math.max(contrastStrength * 1.2, 1.3) : contrastStrength

  return (
    <div
      className={cn(styles.colorOrb, className)}
      style={
        {
          width: dimension,
          height: dimension,
          '--base': palette.base,
          '--accent1': palette.accent1,
          '--accent2': palette.accent2,
          '--accent3': palette.accent3,
          '--spin-duration': `${spinDuration}s`,
          '--blur': `${blurStrength}px`,
          '--contrast': adjustedContrast,
          '--dot': `${pixelDot}px`,
          '--shadow': `${shadowRange}px`,
          '--mask': maskRadius,
        } as React.CSSProperties
      }
    />
  )
}

const SPEED_FACTOR = 1
const FORM_WIDTH = 360
const FORM_HEIGHT = 200

interface ContextShape {
  showForm: boolean
  successFlag: boolean
  triggerOpen: () => void
  triggerClose: () => void
  label: string
  busy: boolean
}

const FormContext = React.createContext({} as ContextShape)
const useFormContext = () => React.useContext(FormContext)

export function MorphPanel({
  label = 'QBQ',
  placeholder = 'e.g. use premium tiles in the kitchen, skip false ceiling in bedroom 2',
  onSubmit,
}: {
  label?: string
  placeholder?: string
  /** Resolve to a message to show the user; reject to surface an error. */
  onSubmit?: (message: string) => Promise<string | void>
}) {
  const wrapperRef = React.useRef<HTMLDivElement>(null)
  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null)

  const [showForm, setShowForm] = React.useState(false)
  const [successFlag, setSuccessFlag] = React.useState(false)
  const [busy, setBusy] = React.useState(false)
  const [reply, setReply] = React.useState<string | null>(null)

  const triggerClose = React.useCallback(() => {
    setShowForm(false)
    textareaRef.current?.blur()
  }, [])

  const triggerOpen = React.useCallback(() => {
    setShowForm(true)
    setTimeout(() => {
      textareaRef.current?.focus()
    })
  }, [])

  const handleSuccess = React.useCallback(
    (message?: string) => {
      triggerClose()
      setSuccessFlag(true)
      if (message) setReply(message)
      setTimeout(() => setSuccessFlag(false), 1500)
      setTimeout(() => setReply(null), 6000)
    },
    [triggerClose],
  )

  React.useEffect(() => {
    function clickOutsideHandler(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node) && showForm) {
        triggerClose()
      }
    }
    document.addEventListener('mousedown', clickOutsideHandler)
    return () => document.removeEventListener('mousedown', clickOutsideHandler)
  }, [showForm, triggerClose])

  const ctx = React.useMemo(
    () => ({ showForm, successFlag, triggerOpen, triggerClose, label, busy }),
    [showForm, successFlag, triggerOpen, triggerClose, label, busy],
  )

  return (
    <div className="pointer-events-none fixed right-6 bottom-6 z-50 flex flex-col items-end gap-3">
      <AnimatePresence>
        {reply && (
          <motion.p
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className="bg-cream text-navy font-body pointer-events-auto max-w-[320px] rounded-2xl px-4 py-3 text-sm shadow-xl"
            role="status"
          >
            {reply}
          </motion.p>
        )}
      </AnimatePresence>

      <div
        className="pointer-events-auto flex items-center justify-center"
        style={{ width: FORM_WIDTH, height: showForm ? FORM_HEIGHT : 56 }}
      >
        <motion.div
          ref={wrapperRef}
          data-panel
          className={cx(
            'bg-cream relative z-3 flex flex-col items-center overflow-hidden border shadow-2xl',
          )}
          initial={false}
          animate={{
            width: showForm ? FORM_WIDTH : 'auto',
            height: showForm ? FORM_HEIGHT : 44,
            borderRadius: showForm ? 14 : 20,
          }}
          transition={{
            type: 'spring',
            stiffness: 550 / SPEED_FACTOR,
            damping: 45,
            mass: 0.7,
            delay: showForm ? 0 : 0.08,
          }}
        >
          <FormContext.Provider value={ctx}>
            <DockBar />
            <InputForm
              ref={textareaRef}
              placeholder={placeholder}
              onSuccess={handleSuccess}
              onSubmit={onSubmit}
              setBusy={setBusy}
            />
          </FormContext.Provider>
        </motion.div>
      </div>
    </div>
  )
}

function DockBar() {
  const { showForm, triggerOpen, label } = useFormContext()
  return (
    <footer className="mt-auto flex h-[44px] items-center justify-center whitespace-nowrap select-none">
      <div className="flex items-center justify-center gap-2 px-3 max-sm:h-10 max-sm:px-2">
        <div className="flex w-fit items-center gap-2">
          <AnimatePresence mode="wait">
            {showForm ? (
              <motion.div
                key="blank"
                initial={{ opacity: 0 }}
                animate={{ opacity: 0 }}
                exit={{ opacity: 0 }}
                className="h-5 w-5"
              />
            ) : (
              <motion.div
                key="orb"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <ColorOrb dimension="24px" />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <Button
          type="button"
          className="text-navy font-ui flex h-fit flex-1 justify-end rounded-full px-2 !py-0.5 hover:bg-transparent"
          variant="ghost"
          onClick={triggerOpen}
        >
          <span className="truncate">{label}</span>
        </Button>
      </div>
    </footer>
  )
}

function InputForm({
  ref,
  placeholder,
  onSuccess,
  onSubmit,
  setBusy,
}: {
  ref: React.Ref<HTMLTextAreaElement>
  placeholder: string
  onSuccess: (message?: string) => void
  onSubmit?: (message: string) => Promise<string | void>
  setBusy: (b: boolean) => void
}) {
  const { triggerClose, showForm, label } = useFormContext()
  const btnRef = React.useRef<HTMLButtonElement>(null)

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget
    const message = String(new FormData(form).get('message') ?? '').trim()
    if (!message) return

    setBusy(true)
    try {
      const reply = await onSubmit?.(message)
      form.reset()
      onSuccess(typeof reply === 'string' ? reply : undefined)
    } catch (err) {
      onSuccess(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  function handleKeys(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Escape') triggerClose()
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      btnRef.current?.click()
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="absolute bottom-0"
      style={{
        width: FORM_WIDTH,
        height: FORM_HEIGHT,
        pointerEvents: showForm ? 'all' : 'none',
      }}
    >
      <AnimatePresence>
        {showForm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ type: 'spring', stiffness: 550 / SPEED_FACTOR, damping: 45, mass: 0.7 }}
            className="flex h-full flex-col p-1"
          >
            <div className="flex justify-between py-1">
              <p className="text-navy font-ui z-2 ml-[38px] flex items-center gap-[6px] select-none">
                {label}
              </p>
              <button
                type="submit"
                ref={btnRef}
                className="text-navy right-4 mt-1 flex -translate-y-[3px] cursor-pointer items-center justify-center gap-1 rounded-[12px] bg-transparent pr-1 text-center select-none"
              >
                <KeyHint>⌘</KeyHint>
                <KeyHint className="w-fit">Enter</KeyHint>
              </button>
            </div>
            <textarea
              ref={ref}
              placeholder={placeholder}
              name="message"
              className="text-navy placeholder:text-navy/40 font-body h-full w-full resize-none scroll-py-2 rounded-md bg-transparent p-4 outline-0"
              required
              onKeyDown={handleKeys}
              spellCheck={false}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showForm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute top-2 left-3"
          >
            <ColorOrb dimension="24px" />
          </motion.div>
        )}
      </AnimatePresence>
    </form>
  )
}

function KeyHint({ children, className }: { children: string; className?: string }) {
  return (
    <kbd
      className={cx(
        'text-navy/70 border-navy/20 flex h-6 w-fit items-center justify-center rounded-sm border px-[6px] font-sans text-xs',
        className,
      )}
    >
      {children}
    </kbd>
  )
}

export default MorphPanel
