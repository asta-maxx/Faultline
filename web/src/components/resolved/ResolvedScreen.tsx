import type { Conflict } from '../../types'
import { listConflicts, useWorkspace } from '../../lib/api'
import { useAsync } from '../../lib/useAsync'
import { count, isoDate, isoMonth } from '../../lib/format'
import { Icon } from '../Icon'
import styles from './ResolvedScreen.module.css'

interface Group {
  key: string
  /** "2026-09", or null when the response carries no resolution date */
  month: string | null
  conflicts: Conflict[]
}

/** Resolved conflicts, newest settlement first, banded by the month they were settled in. */
export function ResolvedScreen() {
  const ws = useWorkspace()
  const resolved = useAsync(() => listConflicts('resolved'), `resolved:${ws.key}`)

  if (resolved.status === 'loading') return <div />
  if (resolved.status === 'error') {
    return (
      <p className="notice" data-tone="error">
        <strong>The resolved list did not load.</strong>
        <code>{resolved.error}</code>
      </p>
    )
  }

  const { conflicts } = resolved.data
  const groups = byMonth(conflicts)

  return (
    <section className={styles.screen} aria-label="Resolved conflicts">
      <header className={styles.head}>
        <p className="cap">
          <span>{count(conflicts.length)} resolved</span>
          {conflicts.length ? <span className="dot">newest settlement first</span> : null}
        </p>
      </header>

      {conflicts.length === 0 ? (
        <p className="notice">
          <strong>Nothing has been resolved yet.</strong>
          A conflict appears here once someone picks the claim that stands, which records a RESOLVED_AS edge from
          the conflict to that claim. Open conflicts are under Conflicts.
        </p>
      ) : (
        <div className={styles.list}>
          {groups.map((g) => (
            <section key={g.key} className={styles.group} aria-label={g.month ?? 'No resolution date'}>
              <h2 className={styles.gutter}>{g.month ?? 'undated'}</h2>
              <ol className={styles.rows}>
                {g.conflicts.map((c) => (
                  <li key={c.id}>
                    <ResolvedRow conflict={c} />
                  </li>
                ))}
              </ol>
            </section>
          ))}
        </div>
      )}
    </section>
  )
}

function ResolvedRow({ conflict: c }: { conflict: Conflict }) {
  const r = c.resolution ?? null
  const winner = r ? c.claims.find((x) => x.id === r.winner_claim_id) : undefined
  const losers = winner ? c.claims.filter((x) => x.id !== winner.id) : []

  return (
    <article className={styles.row}>
      <div className={styles.main}>
        <p className={styles.top}>
          <span className="chip" data-status="resolved">
            <Icon name="resolved" size={14} />
            Settled
          </span>
          <span className={styles.entity}>{c.entity.name}</span>
          <span className="chip" data-kind={c.kind}>
            {c.kind}
          </span>
        </p>

        {winner ? (
          <>
            <p className={styles.winner}>{winner.text}</p>
            {losers.map((l) => (
              <p key={l.id} className={styles.loser}>
                <span className={styles.vs}>over </span>
                <s>{l.text}</s>
              </p>
            ))}
          </>
        ) : (
          <>
            {c.claims.map((x) => (
              <p key={x.id} className={styles.unknown}>
                {x.text}
              </p>
            ))}
            <p className={styles.missing}>
              {r
                ? `The winning claim ${r.winner_claim_id} is not one of this conflict's claims.`
                : 'The response carries no resolution record, so the winning claim is not known.'}
            </p>
          </>
        )}

        {r ? (
          <p className={styles.settled}>
            settled <time dateTime={new Date(r.resolved_at * 1000).toISOString()}>{isoDate(r.resolved_at)}</time> by{' '}
            {r.resolved_by}
          </p>
        ) : null}
      </div>

      <div className={styles.rationale}>
        <h3 className="cap">Rationale</h3>
        {r?.rationale ? <p>{r.rationale}</p> : <p className={styles.missing}>None recorded.</p>}
      </div>
    </article>
  )
}

function byMonth(conflicts: Conflict[]): Group[] {
  const sorted = [...conflicts].sort((a, b) => (b.resolution?.resolved_at ?? -1) - (a.resolution?.resolved_at ?? -1))
  const groups: Group[] = []
  for (const c of sorted) {
    const month = c.resolution ? isoMonth(c.resolution.resolved_at) : null
    const key = month ?? 'undated'
    const last = groups[groups.length - 1]
    if (last && last.key === key) last.conflicts.push(c)
    else groups.push({ key, month, conflicts: [c] })
  }
  return groups
}
