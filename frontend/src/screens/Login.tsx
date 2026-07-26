import * as React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
import { AuthLayout, SocialRow } from '@/components/auth/AuthLayout'
import { Field } from '@/components/auth/Field'
import { api, ApiError, auth } from '@/lib/api'

export function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = React.useState('')
  const [password, setPassword] = React.useState('')
  const [error, setError] = React.useState<string | null>(null)
  const [busy, setBusy] = React.useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const { access_token } = await api.login(email, password)
      auth.set(access_token)
      navigate('/dashboard')
    } catch (err) {
      // An unverified account is a routable state, not a dead end — send the
      // user to the OTP screen instead of showing a message they can't act on.
      if (err instanceof ApiError && /not verified/i.test(err.message)) {
        navigate('/verify', { state: { email } })
        return
      }
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout
      tagline={
        <>
          Precision built <em className="text-cream not-italic">by</em> default
        </>
      }
    >
      <h2 className="font-display text-navy text-4xl font-bold">Login / Register</h2>

      <form onSubmit={handleSubmit} className="mt-8 space-y-2">
        <Field
          label="Email"
          type="email"
          value={email}
          onChange={setEmail}
          autoComplete="email"
          placeholder="username@gmail.com"
          required
        />
        <Field
          label="Password"
          type="password"
          value={password}
          onChange={setPassword}
          autoComplete="current-password"
          required
        />

        {error && (
          <motion.p
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className="font-ui text-destructive pt-3 text-sm"
            role="alert"
          >
            {error}
          </motion.p>
        )}

        <motion.button
          type="submit"
          disabled={busy}
          whileTap={{ scale: 0.98 }}
          className="bg-navy-ink text-cream font-ui mt-7 h-11 w-full cursor-pointer rounded-full transition-opacity disabled:opacity-60"
        >
          {busy ? 'Signing in…' : 'Sign in'}
        </motion.button>

        <div className="pt-3 text-center">
          <button
            type="button"
            className="font-ui text-navy/60 hover:text-navy cursor-pointer text-sm underline-offset-4 hover:underline"
            onClick={() => navigate('/verify', { state: { email } })}
          >
            Forgot Password?
          </button>
        </div>
      </form>

      <SocialRow />

      <p className="font-ui text-navy/70 mt-8 text-center text-sm">
        Don't have an account yet?{' '}
        <Link to="/register" className="text-navy font-bold underline-offset-4 hover:underline">
          Register for free
        </Link>
      </p>
    </AuthLayout>
  )
}
