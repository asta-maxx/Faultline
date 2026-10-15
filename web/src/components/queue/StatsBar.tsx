import type { Stats } from '../../types'
import { formatNumber } from '../../lib/utils'
import styles from './StatsBar.module.css'

interface StatsBarProps {
  stats: Stats
}

export function StatsBar({ stats }: StatsBarProps) {
  const stages = [
    {
      label: 'Naive pairs',
      value: stats.naive_pair_count,
      sublabel: 'Stage 1 — n·(n−1)/2',
    },
    {
      label: 'After graph collapse',
      value: stats.collapsed_pair_count,
      sublabel: 'Stage 2 — shared Entity',
    },
    {
      label: 'After prefilter',
      value: stats.prefiltered_pair_count,
      sublabel: 'Stage 3 — deterministic',
    },
    {
      label: 'LLM judgements',
      value: stats.judged_pair_count,
      sublabel: 'Stage 4 — Adjudicator',
    },
  ]

  return (
    <section className={styles.bar} aria-label="Funnel statistics">
      <div className={styles.stages}>
        {stages.map((s, i) => (
          <div key={s.label} className={styles.stage}>
            <div className={styles.stageInner}>
              <span className={styles.stageNum}>{i + 1}</span>
              <div>
                <div className={styles.stageValue}>{formatNumber(s.value)}</div>
                <div className={styles.stageLabel}>{s.label}</div>
                <div className={styles.stageSub}>{s.sublabel}</div>
              </div>
            </div>
            {i < stages.length - 1 && (
              <svg
                className={styles.arrow}
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M5 12h14M12 5l7 7-7 7"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </div>
        ))}
      </div>
      <div className={styles.totals}>
        <span className={styles.totalItem}>
          <strong>{formatNumber(stats.claims)}</strong> claims
        </span>
        <span className={styles.sep} aria-hidden="true">·</span>
        <span className={styles.totalItem}>
          <strong>{formatNumber(stats.documents)}</strong> docs
        </span>
        <span className={styles.sep} aria-hidden="true">·</span>
        <span className={styles.totalItem}>
          <strong>{formatNumber(stats.entities)}</strong> entities
        </span>
        <span className={styles.sep} aria-hidden="true">·</span>
        <span className={`${styles.totalItem} ${styles.openConflicts}`}>
          <strong>{stats.conflicts_open}</strong> open
        </span>
        <span className={styles.sep} aria-hidden="true">·</span>
        <span className={styles.totalItem}>
          <strong>{stats.conflicts_resolved}</strong> resolved
        </span>
      </div>
    </section>
  )
}
