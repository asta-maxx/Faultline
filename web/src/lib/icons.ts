/**
 * One stroke icon set, 24-unit grid, 1.5 stroke. The same path data feeds the
 * React <Icon> component and the Cytoscape node images, so the graph and the
 * panels never drift apart.
 */
import type { ClaimState, NodeType } from '../types'

export type IconName =
  | NodeType
  | 'state-live'
  | 'state-contradicted'
  | 'state-superseded'
  | 'conflicts'
  | 'resolved'
  | 'sources'
  | 'chevron-down'
  | 'pending'
  | 'arrow-right'
  | 'close'
  | 'plus'

export const ICON_PATHS: Record<IconName, string> = {
  claim: 'M5 4h14v16H5z M8.5 8.5h7 M8.5 12h7 M8.5 15.5h4',
  document: 'M6 3h8.5L19 7.5V21H6z M14 3v5h5 M9 12.5h7 M9 16h7',
  decision: 'M3.5 9 12 4l8.5 5z M6 9v8 M10 9v8 M14 9v8 M18 9v8 M3.5 20h17',
  system: 'M4 4.5h16v6H4z M4 13.5h16v6H4z M7.5 7.5h1 M7.5 16.5h1',
  person: 'M12 12a3.75 3.75 0 1 0 0-7.5 3.75 3.75 0 0 0 0 7.5z M4.5 20.5c.8-3.6 3.8-5.5 7.5-5.5s6.7 1.9 7.5 5.5',
  message: 'M4 5h16v11H10l-4.5 3.5V16H4z',
  ticket: 'M3.5 7h17v3a2 2 0 0 0 0 4v3h-17v-3a2 2 0 0 0 0-4z M14 7v10',
  entity:
    'M5 6c0-1.66 3.13-3 7-3s7 1.34 7 3-3.13 3-7 3-7-1.34-7-3z M5 6v12c0 1.66 3.13 3 7 3s7-1.34 7-3V6 M5 12c0 1.66 3.13 3 7 3s7-1.34 7-3',
  conflict: 'M12 3.5 21 19.5H3z M12 9.5v5 M12 17h.01',
  'state-live': 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M8 12.2l2.7 2.7L16 9.5',
  'state-contradicted': 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M9 9l6 6 M15 9l-6 6',
  'state-superseded': 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M8.5 8l3.5 3.5L15.5 8 M8.5 12.5l3.5 3.5 3.5-3.5',
  conflicts: 'M6 3h8.5L19 7.5V21H6z M14 3v5h5 M9 12.5h7 M9 16h7',
  resolved: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M8 12.2l2.7 2.7L16 9.5',
  sources: 'M3.5 5.5h6l2 2.5h9v11.5h-17z M3.5 11h17',
  'chevron-down': 'M6.5 9.5 12 15l5.5-5.5',
  pending: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z',
  'arrow-right': 'M4 12h15 M13.5 6.5 19 12l-5.5 5.5',
  close: 'M6 6l12 12 M18 6 6 18',
  plus: 'M12 5v14 M5 12h14',
}

export const STATE_ICON: Record<ClaimState, IconName> = {
  live: 'state-live',
  contradicted: 'state-contradicted',
  superseded: 'state-superseded',
}

/** SVG markup as a data URI, for canvas renderers that cannot use CSS colour. */
export function iconDataUri(name: IconName, stroke: string): string {
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="48" height="48" fill="none" ` +
    `stroke="${stroke}" stroke-width="1.5" stroke-linecap="square" stroke-linejoin="miter">` +
    `<path d="${ICON_PATHS[name]}"/></svg>`
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`
}
