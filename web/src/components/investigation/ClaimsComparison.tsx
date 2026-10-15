import type { ConflictClaim } from '../../types'
import { StateBadge } from '../ui/Badge'
import { formatConfidence, formatEpoch } from '../../lib/utils'
import styles from './ClaimsComparison.module.css'

interface ClaimsComparisonProps {
  claims: ConflictClaim[]
}

export function ClaimsComparison({ claims }: ClaimsComparisonProps) {
  const claimA = claims.find(c => c.side === 'a')
  const claimB = claims.find(c => c.side === 'b')

  if (!claimA || !claimB) return null

  return (
    <section className={styles.section} aria-labelledby="claims-heading">
      <h3 id="claims-heading" className={styles.heading}>Conflicting claims</h3>
      <div className={styles.grid}>
        <ClaimCard claim={claimA} />
        <div className={styles.vsLabel} aria-hidden="true">vs</div>
        <ClaimCard claim={claimB} />
      </div>
    </section>
  )
}

function ClaimCard({ claim }: { claim: ConflictClaim }) {
  const isA = claim.side === 'a'

  return (
    <article
      className={`${styles.card} ${isA ? styles.cardA : styles.cardB}`}
      aria-label={`Claim ${claim.side.toUpperCase()}: ${claim.state}`}
    >
      <div className={styles.cardHeader}>
        <span className={`${styles.sideChip} ${isA ? styles.sideChipA : styles.sideChipB}`}>
          {claim.side.toUpperCase()}
        </span>
        <StateBadge state={claim.state} />
        <span className={styles.confidence} title="Extraction confidence">
          {formatConfidence(claim.confidence)}
        </span>
      </div>

      <blockquote className={styles.claimText}>
        &ldquo;{claim.text}&rdquo;
      </blockquote>

      {/* Evidence span */}
      <div className={styles.evidenceBlock}>
        <span className={styles.evidenceLabel}>Evidence span</span>
        <mark className={styles.evidenceMark}>{claim.evidence_span}</mark>
      </div>

      {/* Source */}
      <div className={styles.sourceBlock}>
        <span className={styles.sourceLabel}>Source</span>
        <div className={styles.sourceInfo}>
          <span className={styles.sourceTitle}>{claim.source.title}</span>
          <code className={styles.sourcePath}>{claim.source.path}</code>
          {claim.source.updated_at && (
            <span className={styles.sourceDate}>
              Updated {formatEpoch(claim.source.updated_at)}
            </span>
          )}
        </div>
      </div>
    </article>
  )
}
