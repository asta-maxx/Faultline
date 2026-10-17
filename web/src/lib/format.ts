/** Formatting for system-generated values. Every one of these renders in mono. */

/** ISO date, UTC: 2026-09-14 */
export function isoDate(epochSeconds: number): string {
  return new Date(epochSeconds * 1000).toISOString().slice(0, 10)
}

/** Date and minute, UTC: 2026-10-17 02:14 */
export function isoMinute(epochSeconds: number): string {
  return new Date(epochSeconds * 1000).toISOString().slice(0, 16).replace('T', ' ')
}

/** Elapsed time between two epochs: 42s, 3m 05s, 1h 12m */
export function duration(fromSeconds: number, toSeconds: number): string {
  const s = Math.max(0, Math.round(toSeconds - fromSeconds))
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ${String(s % 60).padStart(2, '0')}s`
  return `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, '0')}m`
}

/** Month bucket, UTC: 2026-09 */
export function isoMonth(epochSeconds: number): string {
  return new Date(epochSeconds * 1000).toISOString().slice(0, 7)
}

export function relativeAge(epochSeconds: number, now = Date.now()): string {
  const minutes = Math.floor((now - epochSeconds * 1000) / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}d ago`
  return isoDate(epochSeconds)
}

export function count(n: number): string {
  return n.toLocaleString('en-US')
}

export function score(n: number): string {
  return n.toFixed(1)
}

export function confidence(n: number): string {
  return n.toFixed(2)
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${count(n)} ${n === 1 ? one : many}`
}

export function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

/** Shortened id for display. Full ids stay in titles and the inspector. */
export function shortId(id: string): string {
  return id.length > 14 ? id.slice(0, 8) : id
}
