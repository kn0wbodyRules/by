import * as React from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { AnimatePresence, motion } from 'motion/react'
import { FlowChrome } from '@/components/FlowChrome'
import { Icon } from '@/components/Icon'
import { TickingNumber } from '@/components/TickingNumber'
import { CircularGallery, type GalleryItem } from '@/components/ui/circular-gallery-2'
import { api } from '@/lib/api'
import { addRoomThumbnail, roomThumbnail } from '@/lib/roomThumb'
import type { ManualRoomInput, RoomOut } from '@/types/api'

/** Backend `floor_type` selects the flooring rate, so these are materials, not storeys. */
const FLOOR_TYPES = ['tile', 'vitrified tile', 'wood', 'concrete', 'granite', 'marble']

const BLANK_ROOM: ManualRoomInput = {
  room_name: 'Room 1',
  length_ft: 10,
  width_ft: 10,
  ceiling_height_ft: 10,
  wall_thickness_ft: 0.75,
  floor_type: 'tile',
  door_count: 1,
  window_count: 1,
  exception_text: '',
}

export function RoomByRoom() {
  const { jobId = '' } = useParams()
  const navigate = useNavigate()

  const [rooms, setRooms] = React.useState<ManualRoomInput[]>([])
  const [persisted, setPersisted] = React.useState<RoomOut[]>([])
  const [active, setActive] = React.useState(0)
  const [loading, setLoading] = React.useState(true)
  const [saving, setSaving] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  // Rooms already on the server (Gemini-detected, or a resumed manual session)
  // seed the form; an empty job starts with one blank room to fill in.
  React.useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const existing = await api.listRooms(jobId)
        if (cancelled) return
        setPersisted(existing)
        setRooms(
          existing.length > 0
            ? existing.map((r) => ({
                room_name: r.room_name,
                length_ft: r.dimensions.length_ft,
                width_ft: r.dimensions.width_ft,
                ceiling_height_ft: r.dimensions.ceiling_height_ft,
                wall_thickness_ft: r.dimensions.wall_thickness_ft,
                floor_type: r.floor_type || 'tile',
                door_count: r.door_count,
                window_count: r.window_count,
                exception_text: r.exception_text ?? '',
              }))
            : [BLANK_ROOM],
        )
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load rooms')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [jobId])

  const current = rooms[active]

  function patch(changes: Partial<ManualRoomInput>) {
    setRooms((rs) => rs.map((r, i) => (i === active ? { ...r, ...changes } : r)))
  }

  function addRoom() {
    setRooms((rs) => [...rs, { ...BLANK_ROOM, room_name: `Room ${rs.length + 1}` }])
    setActive(rooms.length)
  }

  function removeRoom() {
    if (rooms.length <= 1) return
    setRooms((rs) => rs.filter((_, i) => i !== active))
    setActive((a) => Math.max(0, a - 1))
  }

  // The carousel needs one image per card; a trailing card acts as "add a room".
  const items: GalleryItem[] = React.useMemo(
    () => [
      ...rooms.map((r) => ({
        image: roomThumbnail({
          roomName: r.room_name,
          roomType: guessTypeLabel(r.room_name),
          lengthFt: r.length_ft,
          widthFt: r.width_ft,
        }),
        text: r.room_name,
      })),
      { image: addRoomThumbnail(), text: 'Add more rooms' },
    ],
    [rooms],
  )

  const handleSettle = React.useCallback(
    (index: number) => {
      // The last card is the add affordance, not a room.
      if (index < rooms.length) setActive(index)
    },
    [rooms.length],
  )

  async function handleNext() {
    setError(null)
    setSaving(true)
    try {
      // The backend gates /constraints behind ROOMS_CONFIRMED, so rooms are
      // persisted and confirmed on the way out of this screen. The later
      // "Confirm" screen is the final review that triggers calculation.
      let saved = persisted
      if (saved.length === 0) {
        saved = await api.manualRooms(jobId, rooms)
      }

      await api.confirmRooms(
        jobId,
        saved.map((room, i) => ({
          room_id: room.room_id,
          room_name: rooms[i]?.room_name,
          length_ft: rooms[i]?.length_ft,
          width_ft: rooms[i]?.width_ft,
          ceiling_height_ft: rooms[i]?.ceiling_height_ft,
          wall_thickness_ft: rooms[i]?.wall_thickness_ft,
          floor_type: rooms[i]?.floor_type,
          door_count: rooms[i]?.door_count,
          window_count: rooms[i]?.window_count,
          // "" (not null) — the backend's edit-apply logic drops null fields to
          // mean "unchanged", so clearing a previously-set exception has to be a
          // real empty string, not the field's absence.
          exception_text: (rooms[i]?.exception_text ?? '').trim(),
        })),
      )

      navigate(`/constraints/${jobId}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save rooms')
    } finally {
      setSaving(false)
    }
  }

  return (
    <FlowChrome step="Room-by-Room">
      {loading ? (
        <p className="font-body text-cream/60 mt-16">Loading rooms…</p>
      ) : (
        <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_minmax(320px,460px)]">
          <section className="h-[520px] lg:h-[640px]">
            <CircularGallery
              items={items}
              bend={2}
              borderRadius={0.06}
              onSettle={handleSettle}
              className="text-cream font-display"
            />
            <p className="font-ui text-cream/40 mt-2 text-center text-sm">
              Drag or scroll to move between rooms
            </p>
          </section>

          <AnimatePresence mode="wait">
            {current && (
              <motion.section
                key={active}
                initial={{ opacity: 0, x: 40, rotate: 1.5 }}
                animate={{ opacity: 1, x: 0, rotate: 0 }}
                exit={{ opacity: 0, x: -30, rotate: -1 }}
                transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
                className="bg-cream h-fit rounded-[32px] p-7 sm:p-9"
              >
                <input
                  value={current.room_name}
                  onChange={(e) => patch({ room_name: e.target.value })}
                  aria-label="Room name"
                  className="font-display text-navy w-full bg-transparent text-3xl font-bold outline-none"
                />
                <p className="font-ui text-navy/50 mt-1 text-sm">
                  Room {active + 1} of {rooms.length} · area{' '}
                  {(current.length_ft * current.width_ft).toFixed(0)} sqft
                </p>

                <div className="mt-6">
                  <TickingNumber
                    label="Length"
                    value={current.length_ft}
                    onChange={(v) => patch({ length_ft: v })}
                    min={1}
                    suffix="ft"
                  />
                  <TickingNumber
                    label="Width"
                    value={current.width_ft}
                    onChange={(v) => patch({ width_ft: v })}
                    min={1}
                    suffix="ft"
                  />
                  <TickingNumber
                    label="Ceiling Height"
                    value={current.ceiling_height_ft}
                    onChange={(v) => patch({ ceiling_height_ft: v })}
                    min={6}
                    suffix="ft"
                  />
                  <TickingNumber
                    label="Wall Width"
                    value={current.wall_thickness_ft}
                    onChange={(v) => patch({ wall_thickness_ft: v })}
                    min={0.25}
                    step={0.25}
                    decimals={2}
                    suffix="ft"
                  />
                  <TickingNumber
                    label="Doors"
                    value={current.door_count}
                    onChange={(v) => patch({ door_count: Math.round(v) })}
                  />
                  <TickingNumber
                    label="Windows"
                    value={current.window_count}
                    onChange={(v) => patch({ window_count: Math.round(v) })}
                  />

                  <div className="border-navy/10 flex items-center justify-between gap-4 border-b py-3">
                    <label htmlFor="floor-type" className="font-ui text-navy/70">
                      Floor Type
                    </label>
                    <select
                      id="floor-type"
                      value={current.floor_type}
                      onChange={(e) => patch({ floor_type: e.target.value })}
                      className="font-display text-navy cursor-pointer bg-transparent text-right text-lg font-bold outline-none"
                    >
                      {FLOOR_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="pt-4">
                    <label htmlFor="exception-text" className="font-ui text-navy/70 flex items-center gap-2">
                      <Icon name="auto_awesome" className="text-[16px]" />
                      Special requirement for this room (optional)
                    </label>
                    <textarea
                      id="exception-text"
                      value={current.exception_text ?? ''}
                      onChange={(e) => patch({ exception_text: e.target.value })}
                      placeholder='e.g. "no plaster in this room", "extra 20% tiles for cutting waste"'
                      rows={2}
                      className="font-body text-navy placeholder:text-navy/35 border-navy/15 mt-2 w-full resize-none rounded-xl border bg-white/40 p-3 text-sm outline-none"
                    />
                    <p className="font-ui text-navy/40 mt-1 text-xs">
                      Applied to this room only when the estimate is calculated — grade/brand changes
                      belong on the Constraints screen instead.
                    </p>
                  </div>
                </div>

                <div className="mt-7 flex flex-wrap gap-3">
                  <motion.button
                    onClick={addRoom}
                    whileTap={{ scale: 0.97, rotate: 90 }}
                    className="bg-navy-ink text-cream font-ui flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-full py-3"
                  >
                    <Icon name="add" className="text-[20px]" />
                    Add room
                  </motion.button>
                  <button
                    onClick={removeRoom}
                    disabled={rooms.length <= 1}
                    className="border-navy/20 text-navy/70 font-ui hover:bg-navy/5 cursor-pointer rounded-full border px-5 py-3 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Remove
                  </button>
                </div>

                {error && (
                  <p className="font-ui text-destructive mt-4 text-sm" role="alert">
                    {error}
                  </p>
                )}

                <motion.button
                  onClick={handleNext}
                  disabled={saving}
                  whileTap={{ scale: 0.98 }}
                  className="bg-navy text-cream font-ui mt-4 w-full cursor-pointer rounded-full py-4 disabled:opacity-60"
                >
                  {saving ? 'Saving…' : 'Continue to Constraints'}
                </motion.button>
              </motion.section>
            )}
          </AnimatePresence>
        </div>
      )}
    </FlowChrome>
  )
}

/** Cosmetic only — the backend runs the real classifier when rooms are saved. */
function guessTypeLabel(name: string): string {
  const n = name.toLowerCase()
  if (/bath|toilet|wc|wash/.test(n)) return 'bathroom'
  if (/kitchen|cook/.test(n)) return 'kitchen'
  if (/hall|living|drawing|lounge/.test(n)) return 'living room'
  if (/bed|mbr/.test(n)) return 'bedroom'
  if (/pooja|puja|prayer/.test(n)) return 'pooja room'
  if (/balcon|sit.?out|terrace/.test(n)) return 'balcony'
  if (/store|storage/.test(n)) return 'store room'
  if (/corridor|passage|lobby|foyer/.test(n)) return 'corridor'
  if (/utility|laundry/.test(n)) return 'utility'
  return 'room'
}
