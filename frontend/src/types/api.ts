/**
 * Mirrors the backend's frozen v3 BOQ contract, field for field.
 *
 * The backend has a contract test asserting this exact shape; if something here
 * drifts, that test is the source of truth, not this file.
 */

export type JobStatus =
  | 'uploaded'
  | 'rooms_detected'
  | 'rooms_manual'
  | 'rooms_confirmed'
  | 'constraints_set'
  | 'calculated'
  | 'exported'

export type RoomType =
  | 'bedroom'
  | 'kitchen'
  | 'bathroom'
  | 'living_room'
  | 'utility'
  | 'pooja_room'
  | 'store_room'
  | 'balcony'
  | 'corridor'
  | 'other'

export type RoomSource = 'gemini_vision' | 'manual'

export type MaterialUnit = 'sqft' | 'kg' | 'bag' | 'unit' | 'tonne' | 'cft'

export type CorrectionConfidence = 'high' | 'low' | 'fallback'

export interface Dimensions {
  length_ft: number
  width_ft: number
  ceiling_height_ft: number
  wall_thickness_ft: number
}

export interface MaterialLine {
  material_name: string
  theoretical_quantity: number
  correction_factor: number
  correction_confidence: CorrectionConfidence
  quantity: number
  unit: MaterialUnit
  rate_per_unit: number
  total_cost: number
}

export interface RoomOut {
  room_id: string
  room_name: string
  room_name_raw: string
  room_type: RoomType
  area_sqft: number
  dimensions: Dimensions
  floor_type: string
  door_count: number
  window_count: number
  source: RoomSource
  confirmed: boolean
  /** Free-text special requirement for this room only, e.g. "no plaster here". */
  exception_text: string | null
  /** What the exception agent did with it — only set once /calculate has run. */
  exception_applied?: string | null
  /** Only populated once /calculate has run. */
  materials?: MaterialLine[]
  room_total_cost?: number
}

export interface MaterialOverride {
  material_name: string
  preferred_grade_or_brand: string
}

export interface BOQResponse {
  project_name: string
  location: string
  generated_at: string
  constraints: {
    budget_cap: number | null
    material_overrides: MaterialOverride[]
  }
  rooms: RoomOut[]
  total_cost: number
  currency: string
}

export interface JobOut {
  id: string
  project_name: string
  location: string
  status: JobStatus
  total_cost: number | null
  currency: string
  created_at: string
  updated_at: string
}

export interface UploadResponse {
  job_id: string
  status: JobStatus
}

export interface DetectRoomsResponse {
  rooms: RoomOut[]
  rejected_count: number
  rejections: Array<Record<string, unknown>>
}

export interface ConstraintsResponse {
  budget_cap: number | null
  material_overrides: MaterialOverride[]
  warnings: string[]
}

export interface ChatResponse {
  reply: string
  new_calculation_required: boolean
}

export interface RegisterResponse {
  user_id: string
  email: string
  /** False when the account was created but the OTP email could not be sent. */
  email_sent: boolean
  message: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

/** Payload for POST /manual-rooms/{job_id} — every dimension is required server-side. */
export interface ManualRoomInput {
  room_name: string
  length_ft: number
  width_ft: number
  ceiling_height_ft: number
  wall_thickness_ft: number
  floor_type: string
  door_count: number
  window_count: number
  /** Special requirement for this room only, e.g. "no plaster here". */
  exception_text?: string | null
}

/** Payload for PATCH /confirm-rooms/{job_id} — only changed fields need sending. */
export interface RoomEdit {
  room_id: string
  room_name?: string
  room_type?: RoomType
  length_ft?: number
  width_ft?: number
  ceiling_height_ft?: number
  wall_thickness_ft?: number
  floor_type?: string
  door_count?: number
  window_count?: number
  exception_text?: string | null
}
