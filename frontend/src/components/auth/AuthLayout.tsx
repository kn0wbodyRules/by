import * as React from 'react'
import { motion } from 'motion/react'
import { oauthSignInUrl, type OAuthProvider } from '@/lib/api'

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
 * Social sign-in row (Google and GitHub).
 *
 * These are anchors, not fetch calls: OAuth needs a real full-page navigation to
 * the provider's consent screen, and the backend redirects back to
 * /auth/callback once it has issued a token.
 */
export function SocialRow() {
  const providers: Array<{ id: OAuthProvider; label: string }> = [
    { id: 'google', label: 'Google' },
    { id: 'github', label: 'GitHub' },
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
          <motion.a
            key={p.id}
            href={oauthSignInUrl(p.id)}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 + i * 0.08, duration: 0.4 }}
            whileTap={{ scale: 0.97 }}
            className="border-navy/20 font-ui text-navy hover:bg-navy hover:text-cream flex h-10 flex-1 cursor-pointer items-center justify-center gap-2 rounded-full border bg-white/40 transition-colors"
          >
            <ProviderMark provider={p.id} />
            <span className="text-sm">{p.label}</span>
          </motion.a>
        ))}
      </div>
    </div>
  )
}

/**
 * Provider marks as inline SVG. Material Symbols has no Google or GitHub glyph,
 * and these are the one place the design calls for real brand marks.
 */
function ProviderMark({ provider }: { provider: OAuthProvider }) {
  if (provider === 'google') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true" className="h-[18px] w-[18px]">
        <path
          fill="#4285F4"
          d="M23.06 12.25c0-.79-.07-1.54-.2-2.27H12v4.3h6.2a5.3 5.3 0 0 1-2.3 3.48v2.9h3.72c2.18-2 3.44-4.96 3.44-8.41Z"
        />
        <path
          fill="#34A853"
          d="M12 23.5c3.1 0 5.71-1.03 7.62-2.79l-3.72-2.89c-1.03.69-2.35 1.1-3.9 1.1-3 0-5.540-2.02-6.45-4.74H1.7v2.98A11.5 11.5 0 0 0 12 23.5Z"
        />
        <path
          fill="#FBBC05"
          d="M5.55 14.18a6.9 6.9 0 0 1 0-4.36V6.84H1.7a11.51 11.51 0 0 0 0 10.32l3.85-2.98Z"
        />
        <path
          fill="#EA4335"
          d="M12 4.75c1.69 0 3.2.58 4.4 1.72l3.29-3.29C17.7 1.3 15.1.25 12 .25 7.52.25 3.64 2.82 1.7 6.84l3.85 2.98C6.46 7.1 9 4.75 12 4.75Z"
        />
      </svg>
    )
  }
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-[18px] w-[18px] fill-current">
      <path d="M12 .5C5.37.5 0 5.87 0 12.5c0 5.3 3.44 9.8 8.21 11.39.6.11.82-.26.82-.58l-.01-2.03c-3.34.73-4.04-1.61-4.04-1.61-.55-1.39-1.34-1.76-1.34-1.76-1.09-.75.08-.73.08-.73 1.2.09 1.84 1.24 1.84 1.24 1.07 1.84 2.81 1.31 3.5 1 .11-.78.42-1.31.76-1.61-2.67-.3-5.47-1.34-5.47-5.96 0-1.32.47-2.39 1.24-3.23-.12-.3-.54-1.53.12-3.18 0 0 1.01-.32 3.3 1.23a11.5 11.5 0 0 1 6.01 0c2.29-1.55 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.77.84 1.24 1.91 1.24 3.23 0 4.63-2.81 5.65-5.49 5.95.43.37.81 1.1.81 2.22l-.01 3.29c0 .32.21.7.83.58A12.01 12.01 0 0 0 24 12.5C24 5.87 18.63.5 12 .5Z" />
    </svg>
  )
}
