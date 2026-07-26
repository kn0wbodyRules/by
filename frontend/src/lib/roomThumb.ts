/**
 * Builds a mini floor-plan thumbnail for a room as an SVG data URI.
 *
 * The carousel is WebGL and wants an image per card. Rather than a flat colour
 * placeholder, this draws the room to scale — the plan rectangle uses the real
 * length:width ratio, so a corridor reads as a corridor at a glance.
 */

const CREAM = '#F6E3C5'
const NAVY = '#36355B'

function escapeXml(value: string) {
  return value.replace(/[<>&'"]/g, (c) => {
    switch (c) {
      case '<':
        return '&lt;'
      case '>':
        return '&gt;'
      case '&':
        return '&amp;'
      case "'":
        return '&apos;'
      default:
        return '&quot;'
    }
  })
}

export function roomThumbnail({
  roomName,
  roomType,
  lengthFt,
  widthFt,
}: {
  roomName: string
  roomType: string
  lengthFt: number
  widthFt: number
}): string {
  const W = 700
  const H = 900
  const pad = 90

  // Fit the room's true proportions inside the available box.
  const boxW = W - pad * 2
  const boxH = H - pad * 2 - 120
  const ratio = lengthFt > 0 && widthFt > 0 ? widthFt / lengthFt : 1
  let planW = boxW
  let planH = boxW * ratio
  if (planH > boxH) {
    planH = boxH
    planW = boxH / ratio
  }
  const planX = (W - planW) / 2
  const planY = pad + 40

  const prettyType = roomType.replace(/_/g, ' ')

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <rect width="${W}" height="${H}" rx="48" fill="${CREAM}"/>
  <g stroke="${NAVY}" stroke-opacity="0.08" stroke-width="1">
    ${Array.from({ length: 14 }, (_, i) => `<line x1="0" y1="${i * 64}" x2="${W}" y2="${i * 64}"/>`).join('')}
    ${Array.from({ length: 11 }, (_, i) => `<line x1="${i * 64}" y1="0" x2="${i * 64}" y2="${H}"/>`).join('')}
  </g>
  <rect x="${planX}" y="${planY}" width="${planW}" height="${planH}" rx="10"
        fill="none" stroke="${NAVY}" stroke-width="6"/>
  <rect x="${planX + 14}" y="${planY + 14}" width="${Math.max(planW - 28, 0)}" height="${Math.max(planH - 28, 0)}" rx="6"
        fill="none" stroke="${NAVY}" stroke-width="1.5" stroke-opacity="0.35" stroke-dasharray="10 8"/>
  <text x="${W / 2}" y="${planY + planH + 78}" text-anchor="middle"
        font-family="Alexandria, sans-serif" font-size="42" font-weight="700" fill="${NAVY}">
    ${escapeXml(roomName)}
  </text>
  <text x="${W / 2}" y="${planY + planH + 130}" text-anchor="middle"
        font-family="Amaranth, sans-serif" font-size="30" fill="${NAVY}" fill-opacity="0.6">
    ${escapeXml(prettyType)}
  </text>
  <text x="${W / 2}" y="${planY + planH + 182}" text-anchor="middle"
        font-family="Amaranth, sans-serif" font-size="28" fill="${NAVY}" fill-opacity="0.45">
    ${lengthFt} × ${widthFt} ft
  </text>
</svg>`

  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
}

/** The trailing "add a room" card in the carousel. */
export function addRoomThumbnail(): string {
  const W = 700
  const H = 900
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <rect width="${W}" height="${H}" rx="48" fill="${CREAM}" fill-opacity="0.35"
        stroke="${CREAM}" stroke-width="4" stroke-dasharray="18 14"/>
  <g stroke="${CREAM}" stroke-width="10" stroke-linecap="round">
    <line x1="${W / 2 - 70}" y1="${H / 2}" x2="${W / 2 + 70}" y2="${H / 2}"/>
    <line x1="${W / 2}" y1="${H / 2 - 70}" x2="${W / 2}" y2="${H / 2 + 70}"/>
  </g>
  <text x="${W / 2}" y="${H / 2 + 170}" text-anchor="middle"
        font-family="Amaranth, sans-serif" font-size="34" fill="${CREAM}">
    Add more rooms
  </text>
</svg>`
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
}
