import { motion } from 'motion/react'
import { cn } from '@/lib/utils'

/**
 * Placeholder wordmark. Deliberately the only place the mark is drawn — swap the
 * span for an <svg> here and nothing else in the app needs to change.
 *
 * `layoutId` is shared with the intro scroll story's final "by": when the intro
 * unmounts and the dashboard mounts, Framer Motion tweens between the two
 * positions so it reads as one continuous motion rather than a cut.
 */
export const LOGO_LAYOUT_ID = 'by-wordmark'

export function Logo({
  className,
  animateFromIntro = false,
}: {
  className?: string
  animateFromIntro?: boolean
}) {
  const content = (
    <span
      className={cn(
        'font-display leading-none tracking-tight select-none',
        'text-4xl font-bold',
        className,
      )}
    >
      by
    </span>
  )

  if (!animateFromIntro) return content

  return (
    <motion.span
      layoutId={LOGO_LAYOUT_ID}
      transition={{ type: 'spring', stiffness: 180, damping: 26 }}
      className="inline-block"
    >
      {content}
    </motion.span>
  )
}
