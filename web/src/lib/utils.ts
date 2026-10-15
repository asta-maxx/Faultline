/** Date / time helpers */

export function formatEpoch(epochSeconds: number): string {
  return new Date(epochSeconds * 1000).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

export function formatEpochRelative(epochSeconds: number): string {
  const ms = epochSeconds * 1000
  const diff = Date.now() - ms
  const s = Math.floor(diff / 1000)
  if (s < 60) return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24)
  if (d < 30) return `${d}d ago`
  return formatEpoch(epochSeconds)
}

/** Number helpers */

export function formatNumber(n: number): string {
  return n.toLocaleString('en-US')
}

export function formatBlastRadius(score: number): string {
  return score.toFixed(1)
}

export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`
}

/** Capitalise first letter */
export function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}
