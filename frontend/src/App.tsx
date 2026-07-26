import type * as React from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { auth } from '@/lib/api'
import { Confirm } from '@/screens/Confirm'
import { Constraints } from '@/screens/Constraints'
import { Dashboard } from '@/screens/Dashboard'
import { Intro } from '@/screens/Intro'
import { Login } from '@/screens/Login'
import { OAuthCallback } from '@/screens/OAuthCallback'
import { Register } from '@/screens/Register'
import { Results } from '@/screens/Results'
import { RoomByRoom } from '@/screens/RoomByRoom'
import { VerifyOtp } from '@/screens/VerifyOtp'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  if (!auth.isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }
  return <>{children}</>
}

function AnimatedRoutes() {
  const location = useLocation()
  return (
    /*
      Routes are deliberately NOT wrapped in <AnimatePresence>.

      These screens own heavy children — a WebGL carousel, nested AnimatePresence
      overlays — and any one of them failing to report exit-complete leaves the
      outgoing screen mounted after the URL has already changed, so the app looks
      frozen on the previous page. Route-level exit animations aren't worth that
      failure mode: each screen animates its own entrance on mount, and the two
      signature transitions don't need them — the intro→dashboard wordmark uses a
      shared layoutId (which spans unmount/mount on its own), and the
      Confirm→Processing→Results sequence is choreographed inside Results.
    */
    <Routes location={location} key={location.pathname}>
        <Route path="/" element={<Intro />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/verify" element={<VerifyOtp />} />
        {/* Where the backend lands the browser after a provider sign-in. */}
        <Route path="/auth/callback" element={<OAuthCallback />} />

        <Route
          path="/dashboard"
          element={
            <RequireAuth>
              <Dashboard />
            </RequireAuth>
          }
        />
        <Route
          path="/rooms/:jobId"
          element={
            <RequireAuth>
              <RoomByRoom />
            </RequireAuth>
          }
        />
        <Route
          path="/constraints/:jobId"
          element={
            <RequireAuth>
              <Constraints />
            </RequireAuth>
          }
        />
        <Route
          path="/confirm/:jobId"
          element={
            <RequireAuth>
              <Confirm />
            </RequireAuth>
          }
        />
        <Route
          path="/results/:jobId"
          element={
            <RequireAuth>
              <Results />
            </RequireAuth>
          }
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AnimatedRoutes />
    </BrowserRouter>
  )
}
