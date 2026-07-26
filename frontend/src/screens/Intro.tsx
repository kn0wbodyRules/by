import * as React from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, useScroll, useTransform, type MotionValue } from 'motion/react'
import { LOGO_LAYOUT_ID } from '@/components/Logo'
import { auth } from '@/lib/api'

/**
 * Signature animation 1 — the scroll story.
 *
 * Buildings start rendered (filled, detailed) and de-render into blueprint line
 * art as the user scrolls; every headline except the word "by" leaves the frame;
 * the surviving "by" carries a shared layoutId, so navigating to the dashboard
 * tweens it into the header slot as one continuous motion rather than a cut.
 *
 * The buildings are drawn as SVG rather than sourced as image pairs: a stroke
 * reveal on real geometry is what makes "de-rendering into a blueprint" legible,
 * and it avoids shipping two raster versions of the same artwork.
 */
export function Intro() {
  const navigate = useNavigate()
  const ref = React.useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end end'] })

  // Rendered fill fades out early; blueprint strokes draw in behind it.
  const fillOpacity = useTransform(scrollYProgress, [0, 0.45], [1, 0])
  const strokeProgress = useTransform(scrollYProgress, [0.15, 0.75], [0, 1])
  const gridOpacity = useTransform(scrollYProgress, [0.2, 0.6], [0, 0.25])

  // Everything except "by" exits the frame.
  const headlineOpacity = useTransform(scrollYProgress, [0, 0.3], [1, 0])
  const headlineY = useTransform(scrollYProgress, [0, 0.3], [0, -80])
  const subOpacity = useTransform(scrollYProgress, [0.35, 0.55], [0, 1])

  // "by" drifts to where the dashboard header will hold it.
  const byScale = useTransform(scrollYProgress, [0.5, 1], [1, 0.42])
  const byY = useTransform(scrollYProgress, [0.5, 1], [0, -140])

  const ctaOpacity = useTransform(scrollYProgress, [0.82, 0.95], [0, 1])

  function enter() {
    navigate(auth.isAuthenticated ? '/dashboard' : '/login')
  }

  return (
    <div ref={ref} className="bg-navy relative h-[320vh]">
      <div className="sticky top-0 flex h-screen items-center justify-center overflow-hidden">
        <motion.div
          aria-hidden="true"
          style={{ opacity: gridOpacity }}
          className="pointer-events-none absolute inset-0"
        >
          <div
            className="h-full w-full"
            style={{
              backgroundImage:
                'linear-gradient(to right, #F6E3C5 1px, transparent 1px), linear-gradient(to bottom, #F6E3C5 1px, transparent 1px)',
              backgroundSize: '80px 80px',
            }}
          />
        </motion.div>

        <Building
          className="absolute -left-24 bottom-0 h-[85vh] opacity-90 lg:left-4"
          fillOpacity={fillOpacity}
          strokeProgress={strokeProgress}
        />
        <Building
          className="absolute -right-24 bottom-0 h-[70vh] opacity-90 lg:right-4"
          fillOpacity={fillOpacity}
          strokeProgress={strokeProgress}
          variant={1}
        />

        <div className="relative z-10 flex flex-col items-center px-6 text-center">
          <motion.p
            style={{ opacity: headlineOpacity, y: headlineY }}
            className="font-display text-cream/80 text-3xl font-light sm:text-5xl"
          >
            room
          </motion.p>

          <motion.div style={{ scale: byScale, y: byY }} className="my-2">
            <motion.span
              layoutId={LOGO_LAYOUT_ID}
              transition={{ type: 'spring', stiffness: 180, damping: 26 }}
              className="font-display text-cream inline-block text-[7rem] leading-none font-bold sm:text-[11rem]"
            >
              by
            </motion.span>
          </motion.div>

          <motion.p
            style={{ opacity: headlineOpacity, y: headlineY }}
            className="font-display text-cream/80 text-3xl font-light sm:text-5xl"
          >
            room
          </motion.p>

          <motion.p
            style={{ opacity: subOpacity }}
            className="font-body text-cream/70 mt-10 max-w-md text-lg"
          >
            Every wall, every finish, every rate — measured the way an estimator would,
            then corrected by what real projects actually consumed.
          </motion.p>

          <motion.button
            style={{ opacity: ctaOpacity }}
            onClick={enter}
            whileTap={{ scale: 0.97 }}
            className="bg-cream text-navy font-ui mt-10 cursor-pointer rounded-full px-8 py-3"
          >
            Start a Bill of Quantity
          </motion.button>
        </div>

        <motion.p
          style={{ opacity: headlineOpacity }}
          className="font-ui text-cream/40 absolute bottom-8 text-sm"
        >
          scroll
        </motion.p>
      </div>
    </div>
  )
}

/**
 * A building drawn twice in the same geometry: once filled (the "rendered" pass)
 * and once as strokes with an animated dash offset (the blueprint pass).
 */
function Building({
  className,
  fillOpacity,
  strokeProgress,
  variant = 0,
}: {
  className?: string
  fillOpacity: MotionValue<number>
  strokeProgress: MotionValue<number>
  variant?: 0 | 1
}) {
  const floors = variant === 0 ? 11 : 8
  const cols = variant === 0 ? 4 : 3
  const w = 260
  const floorH = 62
  const h = floors * floorH

  const windows: Array<{ x: number; y: number; w: number; h: number }> = []
  for (let f = 0; f < floors; f++) {
    for (let c = 0; c < cols; c++) {
      const gap = w / cols
      windows.push({
        x: 22 + c * gap,
        y: 26 + f * floorH,
        w: gap - 30,
        h: floorH - 30,
      })
    }
  }

  const pathLength = strokeProgress

  return (
    <svg
      aria-hidden="true"
      viewBox={`0 0 ${w} ${h}`}
      preserveAspectRatio="xMidYMax meet"
      className={className}
    >
      {/* rendered pass */}
      <motion.g style={{ opacity: fillOpacity }}>
        <rect x="0" y="0" width={w} height={h} fill="#F6E3C5" fillOpacity="0.16" rx="4" />
        {windows.map((win, i) => (
          <rect
            key={i}
            x={win.x}
            y={win.y}
            width={win.w}
            height={win.h}
            rx="2"
            fill="#F6E3C5"
            fillOpacity={0.1 + ((i * 37) % 5) * 0.06}
          />
        ))}
      </motion.g>

      {/* blueprint pass */}
      <motion.rect
        x="0"
        y="0"
        width={w}
        height={h}
        rx="4"
        fill="none"
        stroke="#F6E3C5"
        strokeWidth="1.5"
        style={{ pathLength }}
      />
      {windows.map((win, i) => (
        <motion.rect
          key={i}
          x={win.x}
          y={win.y}
          width={win.w}
          height={win.h}
          rx="1"
          fill="none"
          stroke="#F6E3C5"
          strokeWidth="1"
          strokeOpacity="0.75"
          style={{ pathLength }}
        />
      ))}
      {Array.from({ length: floors }, (_, f) => (
        <motion.line
          key={`f${f}`}
          x1="0"
          y1={f * floorH}
          x2={w}
          y2={f * floorH}
          stroke="#F6E3C5"
          strokeWidth="0.75"
          strokeOpacity="0.5"
          style={{ pathLength }}
        />
      ))}
    </svg>
  )
}
