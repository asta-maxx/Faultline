import type { Conflict } from '../../types'
import { KindBadge, StatusBadge } from '../ui/Badge'
import { formatBlastRadius, formatEpoch } from '../../lib/utils'
import styles from './ConflictSummary.module.css'

interface ConflictSummaryProps {
  conflict: Conflict
}

export function ConflictSummary({ conflict }: ConflictSummaryProps) {
  return (
    <section className={styles.card} aria-labelledby="conflict-summary-heading">
      <div className={styles.topRow}>
        <div className={styles.badges}>
          <KindBadge kind={conflict.kind} />
          <StatusBadge status={conflict.status} />
        </div>
        <time
          className={styles.timestamp}
          dateTime={new Date(conflict.found_at * 1000).toISOString()}
          title="Discovery time"
        >
          Detected {formatEpoch(conflict.found_at)}
        </time>
      </div>

      <h2 id="conflict-summary-heading" className={styles.entityName}>
        {conflict.entity.name}
      </h2>
      <p className={styles.entityMeta}>
        Subject entity · <span className={styles.entityType}>{conflict.entity.type}</span>
      </p>

      <div className={styles.metrics}>
        {/* Blast radius */}
        <div className={styles.metric}>
          <span className={styles.metricValue}>{formatBlastRadius(conflict.blast_radius)}</span>
          <span className={styles.metricLabel}>Blast radius</span>
        </div>

        {/* Systems affected */}
        <div className={styles.metric}>
          <span className={styles.metricValue}>{conflict.impact.system_count}</span>
          <span className={styles.metricLabel}>Systems</span>
        </div>

        {/* Documents affected */}
        <div className={styles.metric}>
          <span className={styles.metricValue}>{conflict.impact.doc_count}</span>
          <span className={styles.metricLabel}>Documents</span>
        </div>
      </div>

      {/* Affected systems list */}
      {conflict.impact.systems.length > 0 && (
        <div className={styles.systems}>
          <span className={styles.systemsLabel}>Affected systems</span>
          <div className={styles.systemTags}>
            {conflict.impact.systems.map(s => (
              <span key={s} className={styles.systemTag}>{s}</span>
            ))}
          </div>
        </div>
      )}

      {/* Owner */}
      {conflict.owner && (
        <div className={styles.owner}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="2" />
            <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <div>
            <span className={styles.ownerName}>{conflict.owner.name}</span>
            <span className={styles.ownerRole}> — {conflict.owner.role}</span>
          </div>
        </div>
      )}
    </section>
  )
}
