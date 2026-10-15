import type { ConflictKind, ClaimState, ConflictStatus } from '../../types'
import styles from './Badge.module.css'

interface KindBadgeProps {
  kind: ConflictKind
}

export function KindBadge({ kind }: KindBadgeProps) {
  const labels: Record<ConflictKind, string> = {
    direct: 'Direct',
    superseded: 'Superseded',
    undocumented: 'Undocumented',
  }
  return (
    <span className={`${styles.badge} ${styles[`kind_${kind}`]}`}>
      {labels[kind]}
    </span>
  )
}

interface StateBadgeProps {
  state: ClaimState
}

export function StateBadge({ state }: StateBadgeProps) {
  const labels: Record<ClaimState, string> = {
    live: 'Live',
    contradicted: 'Contradicted',
    superseded: 'Superseded',
  }
  const icons: Record<ClaimState, string> = {
    live: '✓',
    contradicted: '✕',
    superseded: '»',
  }
  return (
    <span
      className={`${styles.badge} ${styles[`state_${state}`]}`}
      title={labels[state]}
    >
      <span className={styles.icon} aria-hidden="true">{icons[state]}</span>
      {labels[state]}
    </span>
  )
}

interface StatusBadgeProps {
  status: ConflictStatus
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const labels: Record<ConflictStatus, string> = {
    open: 'Open',
    resolved: 'Resolved',
    dismissed: 'Dismissed',
  }
  return (
    <span className={`${styles.badge} ${styles[`status_${status}`]}`}>
      {labels[status]}
    </span>
  )
}
