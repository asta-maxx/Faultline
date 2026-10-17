import type { Conflict } from '../types'

/** Side a first, then side b, whatever order the API sent them in. */
export function sides(c: Conflict) {
  return [c.claims.find((x) => x.side === 'a'), c.claims.find((x) => x.side === 'b')] as const
}
