import * as React from 'react'
import { motion } from 'motion/react'
import { Icon } from '@/components/Icon'

/**
 * Split-screen shell shared by Login, Register and OTP: tagline on the left,
 * cream card on the right, navy field behind both.
 */
export function AuthLayout({
  tagline,
  children,
}: {
  tagline: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <main className="bg-navy relative min-h-screen overflow-hidden">
      {/* Faint blueprint grid — ties the auth screens to the product's subject matter. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.07]"
        style={{
          backgroundImage:
            'linear-gradient(to right, #F6E3C5 1px, transparent 1px), linear-gradient(to bottom, #F6E3C5 1px, transparent 1px)',
          backgroundSize: '64px 64px',
        }}
      />

      <div className="relative mx-auto grid min-h-screen max-w-[1440px] items-center gap-8 px-6 py-10 lg:grid-cols-2 lg:px-16">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          className="hidden lg:block"
        >
          <h1 className="text-cream font-display text-5xl leading-[1.15] font-bold xl:text-6xl">
            {tagline}
          </h1>
        </motion.div>

        <motion.section
          initial={{ opacity: 0, y: 32 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
          className="bg-cream mx-auto w-full max-w-[560px] rounded-[32px] px-8 py-10 shadow-2xl sm:px-12 sm:py-14"
        >
          {children}
        </motion.section>
      </div>
    </main>
  )
}

/**
 * Social sign-in row. The backend has no OAuth provider wired up, so these are
 * rendered but disabled rather than shipped as buttons that silently do nothing.
 */
export function SocialRow() {
  const providers = [
    { name: 'Google', icon: 'g_translate' },
    { name: 'GitHub', icon: 'code' },
    { name: 'Facebook', icon: 'thumb_up' },
  ]

  return (
    <div className="mt-8">
      <div className="flex items-center gap-4">
        <span className="bg-navy/15 h-px flex-1" />
        <span className="font-ui text-navy/50 text-sm">Or Continue With</span>
        <span className="bg-navy/15 h-px flex-1" />
      </div>

      <div className="mt-5 flex justify-center gap-3">
        {providers.map((p, i) => (
          <motion.button
            key={p.name}
            type="button"
            disabled
            title="Social sign-in isn't available yet — use email and password"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 + i * 0.08, duration: 0.4 }}
            className="border-navy/15 flex h-9 flex-1 cursor-not-allowed items-center justify-center rounded-full border bg-white/40 opacity-50"
            aria-label={`Continue with ${p.name} (unavailable)`}
          >
            <Icon name={p.icon} className="text-navy text-[18px]" />
          </motion.button>
        ))}
      </div>
    </div>
  )
}
