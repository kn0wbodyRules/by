import type * as React from 'react'
import { motion } from 'motion/react'
import { Link } from 'react-router-dom'
import { Breadcrumb, type FlowStep } from '@/components/Breadcrumb'
import { Logo } from '@/components/Logo'

/** Shared navy shell for every step from Room-by-Room onward. */
export function FlowChrome({
  step,
  children,
}: {
  step: FlowStep
  children: React.ReactNode
}) {
  return (
    <motion.main
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.35 }}
      className="bg-navy text-cream min-h-screen"
    >
      <div className="mx-auto max-w-[1440px] px-6 py-8 lg:px-12">
        <header>
          <Link to="/dashboard" aria-label="Back to dashboard">
            <Logo className="text-cream text-5xl" />
          </Link>
          <Breadcrumb active={step} className="mt-6" />
        </header>
        {children}
      </div>
    </motion.main>
  )
}
