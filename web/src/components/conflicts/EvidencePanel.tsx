import type { Conflict, ConflictClaim } from '../../types'
import { confidence, isoDate } from '../../lib/format'
import { Icon, StateMark } from '../Icon'
import { sides } from '../../lib/conflict'
import styles from './EvidencePanel.module.css'

export function EvidencePanel({ conflict }: { conflict: Conflict }) {
  const [a, b] = sides(conflict)
  // v5: the CONTRADICTS edge that produced this conflict. Absent or null means no badge.
  const judgement = conflict.judgement ?? null
  return (
    <section className={styles.panel} aria-label="Evidence">
      <div className={styles.claims} data-judged={judgement ? 'true' : 'false'}>
        {a ? <ClaimBlock claim={a} /> : <MissingSide side="A" />}
        {judgement ? (
          <div className={styles.judge}>
            <p className={styles.badge} title={`CONTRADICTS edge, method ${judgement.method}`}>
              <span className="cap">Judged by</span>
              <span className={styles.method}>{judgement.method}</span>
            </p>
          </div>
        ) : null}
        {b ? <ClaimBlock claim={b} /> : <MissingSide side="B" />}
      </div>
      {/* Inert until the Reconciler lands: no handlers by design. */}
      <div className={styles.actions}>
        <button type="button" className="btn btn-primary">
          Draft correction
        </button>
        <button type="button" className="btn">
          {conflict.owner ? `Assign to ${conflict.owner.name}` : 'Assign owner'}
        </button>
        <button type="button" className="btn">
          Dismiss
        </button>
      </div>
    </section>
  )
}

function ClaimBlock({ claim }: { claim: ConflictClaim }) {
  const span = splitOnSpan(claim.text, claim.evidence_span)
  return (
    <article className={styles.claim} data-state={claim.state}>
      <header className={styles.claimHead}>
        <span className="cap">Claim {claim.side.toUpperCase()}</span>
        <StateMark state={claim.state} />
      </header>

      <p className={styles.text}>
        {span ? (
          <>
            {span.before}
            <mark>{span.match}</mark>
            {span.after}
          </>
        ) : (
          claim.text
        )}
      </p>

      {span ? null : (
        <div className={styles.field}>
          <span className="cap">Evidence in source</span>
          <q className={styles.quote}>{claim.evidence_span}</q>
        </div>
      )}

      <footer className={styles.field}>
        <div className={styles.footHead}>
          <span className="cap">Source</span>
          <span className={styles.confidence}>
            <span className="cap">Confidence</span>
            <span>{confidence(claim.confidence)}</span>
          </span>
        </div>
        <div className={styles.source}>
          <Icon name="document" size={20} />
          <span className={styles.sourceTitle}>{claim.source.title}</span>
          <span className={styles.sourceDate}>{isoDate(claim.source.updated_at)}</span>
          <span className={styles.sourcePath}>{claim.source.path}</span>
        </div>
      </footer>
    </article>
  )
}

function MissingSide({ side }: { side: string }) {
  return (
    <p className="notice" data-tone="error">
      <strong>Claim {side} is missing from this conflict.</strong>
      The API returned no claim with side {side.toLowerCase()}. Every conflict should involve two claims.
    </p>
  )
}

/** Locates the evidence span inside the claim text, ignoring case. */
function splitOnSpan(text: string, span: string) {
  if (!span) return null
  const i = text.toLowerCase().indexOf(span.toLowerCase())
  if (i < 0) return null
  return { before: text.slice(0, i), match: text.slice(i, i + span.length), after: text.slice(i + span.length) }
}
