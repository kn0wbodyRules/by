import * as React from 'react'
import { useNavigate } from 'react-router-dom'
import { auth } from '@/lib/api'

/**
 * Landing point after a provider sign-in.
 *
 * The backend puts the token in the URL *fragment* (`#access_token=…`) rather
 * than the query string, because fragments are never sent to servers and stay
 * out of referrer headers and access logs. It is read once, stored, and stripped
 * from the address bar so it cannot be copied out of a shared URL.
 */
export function OAuthCallback() {
  const navigate = useNavigate()
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    const fragment = new URLSearchParams(window.location.hash.replace(/^#/, ''))
    const token = fragment.get('access_token')

    if (token) {
      auth.set(token)
      window.history.replaceState({}, '', window.location.pathname)
      navigate('/dashboard', { replace: true })
      return
    }

    const query = new URLSearchParams(window.location.search)
    const reason = query.get('error')
    setError(
      reason === 'cancelled' || reason === 'access_denied'
        ? 'Sign-in was cancelled.'
        : reason
          ? `Sign-in failed: ${reason}`
          : 'Sign-in failed — no token was returned.',
    )
  }, [navigate])

  return (
    <main className="bg-navy grid min-h-screen place-items-center px-6">
      <div className="text-center">
        {error ? (
          <>
            <p className="font-display text-cream text-2xl">{error}</p>
            <button
              onClick={() => navigate('/login', { replace: true })}
              className="font-ui text-cream/70 hover:text-cream mt-4 cursor-pointer underline underline-offset-4"
            >
              Back to login
            </button>
          </>
        ) : (
          <p className="font-display text-cream text-2xl">Signing you in…</p>
        )}
      </div>
    </main>
  )
}
