import { ICON_PATHS, STATE_ICON, type IconName } from '../lib/icons'
import type { ClaimState } from '../types'

export function Icon({ name, size = 16, className }: { name: IconName; size?: number; className?: string }) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="square"
      strokeLinejoin="miter"
      aria-hidden="true"
      focusable="false"
    >
      <path d={ICON_PATHS[name]} />
    </svg>
  )
}

const STATE_WORD: Record<ClaimState, string> = {
  live: 'Current',
  contradicted: 'Contradicted',
  superseded: 'Superseded',
}

/** A claim state always carries a glyph and a word, never colour alone. */
export function StateMark({ state, word = STATE_WORD[state] }: { state: ClaimState; word?: string }) {
  return (
    <span className="state-mark" data-state={state}>
      <Icon name={STATE_ICON[state]} size={14} />
      {word}
    </span>
  )
}
