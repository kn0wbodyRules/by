/**
 * Typed client for the "by" FastAPI backend.
 *
 * All calls go through `/api/*`, which Vite proxies to http://127.0.0.1:8000 in
 * dev (see vite.config.ts) — so nothing here hardcodes a host and there is no
 * CORS preflight locally.
 */

import type {
  BOQResponse,
  ChatResponse,
  ConstraintsResponse,
  DetectRoomsResponse,
  JobOut,
  ManualRoomInput,
  MaterialOverride,
  RegisterResponse,
  RoomEdit,
  RoomOut,
  TokenResponse,
  UploadResponse,
} from '@/types/api'

const TOKEN_KEY = 'by.access_token'

export const auth = {
  get token() {
    return localStorage.getItem(TOKEN_KEY)
  },
  set(token: string) {
    localStorage.setItem(TOKEN_KEY, token)
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY)
  },
  get isAuthenticated() {
    return Boolean(localStorage.getItem(TOKEN_KEY))
  },
}

/** Carries the backend's own error message and status so screens can react to 409s. */
export class ApiError extends Error {
  // Declared explicitly rather than as a constructor parameter property —
  // `erasableSyntaxOnly` (on by default in this scaffold) forbids those.
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (!(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  if (auth.token) headers.set('Authorization', `Bearer ${auth.token}`)

  const res = await fetch(`/api${path}`, { ...init, headers })

  if (!res.ok) {
    // FastAPI puts domain errors in `detail`; fall back to status text otherwise.
    let message = res.statusText
    try {
      const body = await res.json()
      if (typeof body?.detail === 'string') message = body.detail
      else if (Array.isArray(body?.detail)) message = body.detail[0]?.msg ?? message
    } catch {
      /* non-JSON error body — keep statusText */
    }
    if (res.status === 401) auth.clear()
    throw new ApiError(res.status, message)
  }

  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const api = {
  // ---- auth ----
  register: (email: string, password: string) =>
    request<RegisterResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  verifyOtp: (email: string, otp_code: string) =>
    request<TokenResponse>('/auth/verify-otp', {
      method: 'POST',
      body: JSON.stringify({ email, otp_code }),
    }),

  resendOtp: (email: string) =>
    request<{ email_sent: boolean; message: string }>('/auth/resend-otp', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),

  login: (email: string, password: string) =>
    request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<{ id: string; email: string; is_verified: boolean }>('/auth/me'),

  // ---- plans / jobs ----
  listPlans: () => request<JobOut[]>('/plans'),

  deletePlan: (jobId: string) =>
    request<void>(`/plans/${jobId}`, { method: 'DELETE' }),

  upload: (file: File, projectName: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('project_name', projectName)
    return request<UploadResponse>('/upload', { method: 'POST', body: form })
  },

  /** Creates a job with no floor-plan image, for the manual-entry path. */
  createManualJob: (projectName: string) => {
    // The backend's only job-creating endpoint is /upload, so the manual path
    // sends a 1x1 placeholder rather than adding a second creation route.
    const blob = new Blob([PLACEHOLDER_PNG], { type: 'image/png' })
    const form = new FormData()
    form.append('file', new File([blob], 'manual.png', { type: 'image/png' }))
    form.append('project_name', projectName)
    return request<UploadResponse>('/upload', { method: 'POST', body: form })
  },

  // ---- rooms ----
  /** Reads a job's rooms at any status — used when resuming a job mid-flow. */
  listRooms: (jobId: string) => request<RoomOut[]>(`/rooms/${jobId}`),

  detectRooms: (jobId: string) =>
    request<DetectRoomsResponse>(`/detect-rooms/${jobId}`, { method: 'POST' }),

  manualRooms: (jobId: string, rooms: ManualRoomInput[]) =>
    request<RoomOut[]>(`/manual-rooms/${jobId}`, {
      method: 'POST',
      body: JSON.stringify({ rooms }),
    }),

  confirmRooms: (jobId: string, rooms: RoomEdit[]) =>
    request<RoomOut[]>(`/confirm-rooms/${jobId}`, {
      method: 'PATCH',
      body: JSON.stringify({ rooms }),
    }),

  // ---- constraints / calculate / results ----
  setConstraints: (
    jobId: string,
    budget_cap: number | null,
    material_overrides: MaterialOverride[] = [],
  ) =>
    request<ConstraintsResponse>(`/constraints/${jobId}`, {
      method: 'PATCH',
      body: JSON.stringify({ budget_cap, material_overrides }),
    }),

  calculate: (jobId: string) =>
    request<BOQResponse>(`/calculate/${jobId}`, { method: 'POST' }),

  getBoq: (jobId: string) => request<BOQResponse>(`/boq/${jobId}`),

  chat: (jobId: string, message: string) =>
    request<ChatResponse>(`/chat/${jobId}`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),

  /** Streams the generated file straight to a browser download. */
  async download(jobId: string, format: 'pdf' | 'excel', projectName: string) {
    const res = await fetch(`/api/export/${jobId}?format=${format}`, {
      headers: auth.token ? { Authorization: `Bearer ${auth.token}` } : {},
    })
    if (!res.ok) throw new ApiError(res.status, 'Export failed')

    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${projectName.replace(/\s+/g, '-')}-BOQ.${format === 'pdf' ? 'pdf' : 'xlsx'}`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  },
}

/** Smallest valid PNG — stands in for the image on the manual-entry path. */
const PLACEHOLDER_PNG = Uint8Array.from([
  0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x0d, 0x49,
  0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x08, 0x06,
  0x00, 0x00, 0x00, 0x1f, 0x15, 0xc4, 0x89, 0x00, 0x00, 0x00, 0x0a, 0x49, 0x44,
  0x41, 0x54, 0x78, 0x9c, 0x63, 0x00, 0x01, 0x00, 0x00, 0x05, 0x00, 0x01, 0x0d,
  0x0a, 0x2d, 0xb4, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4e, 0x44, 0xae, 0x42,
  0x60, 0x82,
])
