import type { Conflict } from '../types'

/** Side a first, then side b, whatever order the API sent them in. */
export function sides(c: Conflict) {
  return [c.claims.find((x) => x.side === 'a'), c.claims.find((x) => x.side === 'b')] as const
}

/** The queue's order: highest blast radius first, ties in the order the API sent them. */
export function rankConflicts(conflicts: Conflict[]): Conflict[] {
  return [...conflicts].sort((a, b) => b.blast_radius - a.blast_radius)
}

/** The conflict to show once `id` leaves the queue: the next one down, else the one above, else none. */
export function nextAfter(conflicts: Conflict[], id: string): Conflict | null {
  const ranked = rankConflicts(conflicts)
  const i = ranked.findIndex((c) => c.id === id)
  const rest = ranked.filter((c) => c.id !== id)
  if (rest.length === 0) return null
  return rest[i < 0 ? 0 : Math.min(i, rest.length - 1)]
}
