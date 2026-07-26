import * as React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
import { AuthLayout, SocialRow } from '@/components/auth/AuthLayout'
import { Field } from '@/components/auth/Field'
import { api } from '@/lib/api'

export function Register() {
  const navigate = useNavigate()
  const [name, setName] = React.useState('')
  const [email, setEmail] = React.useState('')
  const [password, setPassword] = React.useState('')
  const [confirm, setConfirm] = React.useState('')
  const [error, setError] = React.useState<string | null>(null)
  const [busy, setBusy] = React.useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    if (password !== confirm) {
      setError('Passwords do not match')
      return
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    setBusy(true)
    try {
      const res = await api.register(email, password)
      // The backend has no name column; the design shows one on the dashboard
      // profile card, so it lives client-side until a users.name field exists.
      localStorage.setItem('by.display_name', name)
      navigate('/verify', {
        state: { email, emailSent: res.email_sent, message: res.message },
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout
      tagline={
        <>
          Built <em className="text-cream not-italic">by</em> engineers, trusted{' '}
          <em className="text-cream not-italic">by</em> builders
        </>
      }
    >
      <h2 className="font-display text-navy text-4xl font-bold">Register / Login</h2>

      <form onSubmit={handleSubmit} className="mt-6 space-y-1">
        <Field
          label="Name"
          value={name}
          onChange={setName}
          autoComplete="name"
          placeholder="First and Last Name"
          required
        />
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
          autoComplete="new-password"
          required
        />
        <Field
          label="Confirm Password"
          type="password"
          value={confirm}
          onChange={setConfirm}
          autoComplete="new-password"
          placeholder="Re-Enter the Password"
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
          {busy ? 'Creating account…' : 'Create Account'}
        </motion.button>
      </form>

      <SocialRow />

      <p className="font-ui text-navy/70 mt-8 text-center text-sm">
        Already have an account?{' '}
        <Link to="/login" className="text-navy font-bold underline-offset-4 hover:underline">
          Login!
        </Link>
      </p>
    </AuthLayout>
  )
}
