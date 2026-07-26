import { cn } from '@/lib/utils'

/**
 * Material Symbols (Rounded) — the project's single icon source.
 * Pass the ligature name, e.g. <Icon name="upload_file" />.
 */
export function Icon({
  name,
  filled = false,
  className,
}: {
  name: string
  filled?: boolean
  className?: string
}) {
  return (
    <span
      aria-hidden="true"
      className={cn('icon', filled && 'icon-filled', className)}
    >
      {name}
    </span>
  )
}
