import * as React from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
import { AuthLayout } from '@/components/auth/AuthLayout'
import { api, auth } from '@/lib/api'

const OTP_LENGTH = 6

/**
 * Not in the Figma file — added because the backend requires verification before
 * an account can log in. Styled on the same split-screen shell as Login/Register.
 */
export function VerifyOtp() {
  const navigate = useNavigate()
  const location = useLocation()
  const state = (location.state ?? {}) as {
    email?: string
    emailSent?: boolean
    message?: string
  }

  const [email] = React.useState(state.email ?? '')
  const [digits, setDigits] = React.useState<string[]>(Array(OTP_LENGTH).fill(''))
  const [error, setError] = React.useState<string | null>(null)
  const [notice, setNotice] = React.useState<string | null>(
    state.emailSent === false ? state.message ?? null : null,
  )
  const [busy, setBusy] = React.useState(false)
  const inputs = React.useRef<Array<HTMLInputElement | null>>([])

  const code = digits.join('')

  function setDigit(index: number, value: string) {
    const clean = value.replace(/\D/g, '')
    if (!clean) {
      setDigits((d) => d.map((v, i) => (i === index ? '' : v)))
      return
    }
    // Handle paste of a full code into any single box.
    if (clean.length > 1) {
      const chars = clean.slice(0, OTP_LENGTH).split('')
      setDigits(Array.from({ length: OTP_LENGTH }, (_, i) => chars[i] ?? ''))
      inputs.current[Math.min(chars.length, OTP_LENGTH - 1)]?.focus()
      return
    }
    setDigits((d) => d.map((v, i) => (i === index ? clean : v)))
    if (index < OTP_LENGTH - 1) inputs.current[index + 1]?.focus()
  }

  function handleKeyDown(index: number, e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      inputs.current[index - 1]?.focus()
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const { access_token } = await api.verifyOtp(email, code)
      auth.set(access_token)
      navigate('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Verification failed')
    } finally {
      setBusy(false)
    }
  }

  async function handleResend() {
    setError(null)
    setNotice(null)
    try {
      const res = await api.resendOtp(email)
      setNotice(
        res.email_sent
          ? 'A new code is on its way.'
          : "Couldn't send the email — check the server's mail settings.",
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not resend')
    }
  }

  return (
    <AuthLayout
      tagline={
        <>
          Verified <em className="text-cream not-italic">by</em> email, secured{' '}
          <em className="text-cream not-italic">by</em> design
        </>
      }
    >
      <h2 className="font-display text-navy text-4xl font-bold">Verify your email</h2>
      <p className="font-body text-navy/70 mt-3">
        We sent a {OTP_LENGTH}-digit code to{' '}
        <span className="font-bold">{email || 'your inbox'}</span>.
      </p>

      <form onSubmit={handleSubmit} className="mt-8">
        <div className="flex justify-between gap-2 sm:gap-3">
          {digits.map((digit, i) => (
            <input
              key={i}
              ref={(el) => {
                inputs.current[i] = el
              }}
              value={digit}
              onChange={(e) => setDigit(i, e.target.value)}
              onKeyDown={(e) => handleKeyDown(i, e)}
              inputMode="numeric"
              autoComplete={i === 0 ? 'one-time-code' : 'off'}
              maxLength={OTP_LENGTH}
              aria-label={`Digit ${i + 1}`}
              className="border-navy/25 text-navy focus:border-navy font-display h-14 w-full rounded-2xl border bg-white/40 text-center text-2xl font-bold outline-none transition-colors sm:h-16"
            />
          ))}
        </div>

        {notice && (
          <p className="font-ui text-navy/70 pt-4 text-sm" role="status">
            {notice}
          </p>
        )}
        {error && (
          <motion.p
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className="font-ui text-destructive pt-4 text-sm"
            role="alert"
          >
            {error}
          </motion.p>
        )}

        <motion.button
          type="submit"
          disabled={busy || code.length !== OTP_LENGTH}
          whileTap={{ scale: 0.98 }}
          className="bg-navy-ink text-cream font-ui mt-7 h-11 w-full cursor-pointer rounded-full transition-opacity disabled:opacity-40"
        >
          {busy ? 'Verifying…' : 'Verify'}
        </motion.button>
      </form>

      <p className="font-ui text-navy/70 mt-6 text-center text-sm">
        Didn't get it?{' '}
        <button
          type="button"
          onClick={handleResend}
          className="text-navy cursor-pointer font-bold underline-offset-4 hover:underline"
        >
          Resend code
        </button>
      </p>
    </AuthLayout>
  )
}
