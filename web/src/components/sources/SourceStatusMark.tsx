import type { SourceStatus } from '../../types'
import type { IconName } from '../../lib/icons'
import { Icon } from '../Icon'

const MARK: Record<SourceStatus, { icon: IconName; word: string }> = {
  ready: { icon: 'resolved', word: 'Ready' },
  unsupported: { icon: 'conflict', word: 'Not read' },
  missing: { icon: 'state-contradicted', word: 'Missing' },
}

/**
 * Source status, glyph and word together. These are not claim states, so
 * they take no state colour: "ready" is muted, anything that stops a source
 * being read is set in full ink so it is noticed.
 */
export function SourceStatusMark({ status }: { status: SourceStatus }) {
  const m = MARK[status]
  return (
    <span
      className="state-mark"
      style={{ color: status === 'ready' ? 'var(--ink-muted)' : 'var(--ink)' }}
      title={status}
    >
      <Icon name={m.icon} size={14} />
      {m.word}
    </span>
  )
}
