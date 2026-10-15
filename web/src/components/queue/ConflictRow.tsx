import type { Conflict } from '../../types'
import { KindBadge } from '../ui/Badge'
import { formatBlastRadius, formatEpochRelative } from '../../lib/utils'
import styles from './ConflictRow.module.css'

interface ConflictRowProps {
  conflict: Conflict
  rank: number
  onSelect: (conflict: Conflict) => void
}

export function ConflictRow({ conflict, rank, onSelect }: ConflictRowProps) {
  const claimA = conflict.claims.find(c => c.side === 'a')
  const claimB = conflict.claims.find(c => c.side === 'b')

  return (
    <article className={styles.row} aria-label={`Conflict ${rank}: ${conflict.entity.name}`}>
      <div className={styles.blastCol} aria-label={`Blast radius ${conflict.blast_radius}`}>
        <span className={styles.blastScore}>{formatBlastRadius(conflict.blast_radius)}</span>
        <span className={styles.blastLabel}>blast</span>
      </div>

      <div className={styles.body}>
        <div className={styles.topRow}>
          <span className={styles.entityName}>{conflict.entity.name}</span>
          <div className={styles.badges}>
            <KindBadge kind={conflict.kind} />
          </div>
          <time className={styles.timestamp} dateTime={new Date(conflict.found_at * 1000).toISOString()}>
            {formatEpochRelative(conflict.found_at)}
          </time>
        </div>

        {/* Claim comparison summary */}
        {claimA && claimB && (
          <div className={styles.claimPreview}>
            <div className={styles.claimSide}>
              <span className={`${styles.sideLabel} ${styles.sideA}`}>A</span>
              <span className={styles.claimText}>{claimA.text}</span>
            </div>
            <div className={styles.claimDivider} aria-hidden="true">vs</div>
            <div className={styles.claimSide}>
              <span className={`${styles.sideLabel} ${styles.sideB}`}>B</span>
              <span className={styles.claimText}>{claimB.text}</span>
            </div>
          </div>
        )}

        <div className={styles.bottomRow}>
          <div className={styles.impact} aria-label="Impact">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span>{conflict.impact.system_count} system{conflict.impact.system_count !== 1 ? 's' : ''}</span>
            <span className={styles.dot} aria-hidden="true">·</span>
            <span>{conflict.impact.doc_count} doc{conflict.impact.doc_count !== 1 ? 's' : ''}</span>
          </div>
          {conflict.owner && (
            <span className={styles.owner} title={conflict.owner.role}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="2" />
                <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
              {conflict.owner.name}
            </span>
          )}

          <button
            className={styles.investigateBtn}
            onClick={() => onSelect(conflict)}
            aria-label={`Investigate conflict about ${conflict.entity.name}`}
          >
            Investigate
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      </div>
    </article>
  )
}
