import type { Conflict } from '../../types'
import { count, plural, relativeAge, score } from '../../lib/format'
import { rankConflicts, sides } from '../../lib/conflict'
import { navigate } from '../../lib/router'
import styles from './ConflictQueue.module.css'

/** The last conflict this session resolved or dismissed. */
export interface SettledNote {
  outcome: 'resolved' | 'dismissed'
  entity: string
  conflictId: string
}

interface QueueProps {
  conflicts: Conflict[]
  selectedId: string | null
  settled: SettledNote | null
  onSelect: (id: string) => void
}

export function ConflictQueue({ conflicts, selectedId, settled, onSelect }: QueueProps) {
  const ranked = rankConflicts(conflicts)
  const max = ranked.reduce((m, c) => Math.max(m, c.blast_radius), 0)

  return (
    <section className={styles.queue} aria-label="Conflict queue">
      <header className={styles.head}>
        <p className="cap">
          <span>{count(ranked.length)} open</span>
          <span className="dot">sorted by blast radius</span>
        </p>
      </header>
      <p className={styles.settled} role="status" hidden={!settled}>
        {settled ? (
          settled.outcome === 'resolved' ? (
            <>
              Resolved <b>{settled.entity}</b>. It is listed under{' '}
              <a
                className="link"
                href="/resolved"
                onClick={(e) => {
                  if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return
                  e.preventDefault()
                  navigate({ name: 'resolved' })
                }}
              >
                Resolved
              </a>
              .
            </>
          ) : (
            <>
              Dismissed <b>{settled.entity}</b>. It no longer appears in this queue.
            </>
          )
        ) : null}
      </p>
      {ranked.length === 0 ? (
        <p className="notice">
          <strong>No open conflicts.</strong>
          Every conflict found so far is resolved or dismissed. Resolved ones are listed under Resolved.
        </p>
      ) : (
        <ol className={styles.list}>
          {ranked.map((c) => (
            <li key={c.id}>
              <QueueRow conflict={c} max={max} selected={c.id === selectedId} onSelect={onSelect} />
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

function QueueRow({
  conflict: c,
  max,
  selected,
  onSelect,
}: {
  conflict: Conflict
  max: number
  selected: boolean
  onSelect: (id: string) => void
}) {
  const [a, b] = sides(c)
  const share = max > 0 ? c.blast_radius / max : 0

  return (
    <button
      type="button"
      className={styles.row}
      aria-current={selected ? 'true' : undefined}
      onClick={() => onSelect(c.id)}
    >
      <span className={styles.score}>
        <span className={styles.scoreValue}>{score(c.blast_radius)}</span>
        <span className={styles.bar} aria-hidden="true">
          <span style={{ width: `${share * 100}%` }} />
        </span>
      </span>

      <span className={styles.body}>
        <span className={styles.top}>
          <span className="chip" data-kind={c.kind}>
            {c.kind}
          </span>
          <span className={styles.found}>found {relativeAge(c.found_at)}</span>
        </span>
        <span className={styles.claims}>
          {a ? <span>{a.text}</span> : null}
          {b ? (
            <span>
              <span className={styles.vs}>vs </span>
              {b.text}
            </span>
          ) : null}
        </span>
        <span className={styles.meta}>
          <span>{plural(c.impact.doc_count, 'doc')}</span>
          <span className="dot">{plural(c.impact.system_count, 'system')}</span>
          {c.owner ? <span className="dot">{c.owner.name}</span> : null}
        </span>
      </span>
    </button>
  )
}
