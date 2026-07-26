import * as React from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'motion/react'
import { FlowChrome } from '@/components/FlowChrome'
import { Icon } from '@/components/Icon'
import { MorphPanel } from '@/components/ui/ai-input'
import { CircularGallery, type GalleryItem } from '@/components/ui/circular-gallery-2'
import { api } from '@/lib/api'
import { roomThumbnail } from '@/lib/roomThumb'
import type { RoomOut } from '@/types/api'

export function Confirm() {
  const { jobId = '' } = useParams()
  const navigate = useNavigate()

  const [rooms, setRooms] = React.useState<RoomOut[]>([])
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const data = await api.listRooms(jobId)
        if (!cancelled) setRooms(data)
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

  const items: GalleryItem[] = React.useMemo(
    () =>
      rooms.map((r) => ({
        image: roomThumbnail({
          roomName: r.room_name,
          roomType: r.room_type,
          lengthFt: r.dimensions.length_ft,
          widthFt: r.dimensions.width_ft,
        }),
        text: r.room_name,
      })),
    [rooms],
  )

  const totalArea = rooms.reduce((sum, r) => sum + r.area_sqft, 0)

  return (
    <FlowChrome step="Confirm">
      <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_minmax(320px,460px)]">
        <section className="h-[420px] lg:h-[560px]">
          {loading ? (
            <p className="font-body text-cream/60">Loading rooms…</p>
          ) : (
            <CircularGallery
              items={items}
              bend={2}
              borderRadius={0.06}
              className="text-cream font-display"
            />
          )}
        </section>

        <section className="bg-cream h-fit rounded-[32px] p-7 sm:p-9">
          <h2 className="font-display text-navy text-3xl font-bold">
            Constraints &amp; Exceptions
          </h2>

          <dl className="mt-6 space-y-3">
            <Row label="Rooms" value={String(rooms.length)} />
            <Row label="Total area" value={`${totalArea.toFixed(0)} sqft`} />
            <Row
              label="Room types"
              value={[...new Set(rooms.map((r) => r.room_type.replace(/_/g, ' ')))]
                .slice(0, 4)
                .join(', ')}
            />
          </dl>

          <p className="font-body text-navy/60 mt-6 text-sm">
            Check the rooms opposite before calculating. Anything still wrong is faster
            to fix now than after the Bill of Quantity is generated.
          </p>

          {error && (
            <p className="font-ui text-destructive mt-4 text-sm" role="alert">
              {error}
            </p>
          )}

          <motion.button
            onClick={() => navigate(`/results/${jobId}`)}
            disabled={loading || rooms.length === 0}
            whileTap={{ scale: 0.98 }}
            className="bg-navy text-cream font-ui relative mt-7 w-full cursor-pointer overflow-hidden rounded-full py-4 tracking-[0.2em] uppercase disabled:opacity-50"
          >
            <span className="relative z-10">Confirm</span>
          </motion.button>

          <button
            onClick={() => navigate(`/constraints/${jobId}`)}
            className="font-ui text-navy/60 hover:text-navy mt-3 flex w-full cursor-pointer items-center justify-center gap-1 text-sm"
          >
            <Icon name="arrow_back" className="text-[16px]" />
            Back to constraints
          </button>
        </section>
      </div>

      <MorphPanel
        onSubmit={async (message) => {
          const res = await api.chat(jobId, message)
          return res.reply
        }}
      />
    </FlowChrome>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-navy/10 flex items-baseline justify-between gap-4 border-b py-2">
      <dt className="font-ui text-navy/60">{label}</dt>
      <dd className="font-body text-navy text-right capitalize">{value || '—'}</dd>
    </div>
  )
}
