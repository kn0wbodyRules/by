import { motion } from 'motion/react'
import { cn } from '@/lib/utils'

/**
 * The flow's spine: `Bill of Quantity › Room-by-Room › Constraints and Exclusions › Confirm`.
 * Visible and accurate on every screen from Room-by-Room onward.
 */
export const FLOW_STEPS = [
  'Bill of Quantity',
  'Room-by-Room',
  'Constraints and Exclusions',
  'Confirm',
] as const

export type FlowStep = (typeof FLOW_STEPS)[number]

export function Breadcrumb({
  active,
  className,
}: {
  active: FlowStep
  className?: string
}) {
  const activeIndex = FLOW_STEPS.indexOf(active)

  return (
    <nav
      aria-label="Progress"
      className={cn('font-ui flex flex-wrap items-center gap-x-3 gap-y-1', className)}
    >
      {FLOW_STEPS.map((step, i) => {
        const isActive = i === activeIndex
        const isPast = i < activeIndex
        // Steps past the current one are dimmed rather than hidden, so the user
        // can always see how much of the flow is left.
        return (
          <span key={step} className="flex items-center gap-3">
            {i > 0 && (
              <span
                aria-hidden="true"
                className={cn(
                  'text-lg',
                  isPast || isActive ? 'text-cream/50' : 'text-cream/25',
                )}
              >
                ›
              </span>
            )}
            <span className="relative">
              <span
                className={cn(
                  'text-sm transition-colors duration-300 sm:text-base',
                  isActive && 'text-cream',
                  isPast && 'text-cream/60',
                  !isActive && !isPast && 'text-cream/30',
                )}
              >
                {step}
              </span>
              {isActive && (
                <motion.span
                  layoutId="breadcrumb-underline"
                  className="bg-cream absolute -bottom-1 left-0 h-px w-full"
                  transition={{ type: 'spring', stiffness: 320, damping: 30 }}
                />
              )}
            </span>
          </span>
        )
      })}
    </nav>
  )
}
