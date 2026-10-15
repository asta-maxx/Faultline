import { useEffect, useState, useCallback } from 'react'
import { api } from '../../lib/api'
import type {
  Conflict,
  ConflictsResponse,
  ConflictStatusFilter,
  ConflictSortField,
  SortDirection,
  AsyncState,
} from '../../types'
import { ConflictRow } from './ConflictRow'
import { StatsBar } from './StatsBar'
import { QueueFilters } from './QueueFilters'
import styles from './ConflictQueue.module.css'

interface ConflictQueueProps {
  onSelect: (conflict: Conflict) => void
}

export function ConflictQueue({ onSelect }: ConflictQueueProps) {
  const [listState, setListState] = useState<AsyncState<ConflictsResponse>>({
    state: 'idle',
    data: null,
    error: null,
  })
  const [statusFilter, setStatusFilter] = useState<ConflictStatusFilter>('all')
  const [sortBy, setSortBy] = useState<ConflictSortField>('blast_radius')
  const [sortDir] = useState<SortDirection>('desc')

  const load = useCallback(async () => {
    setListState(prev => ({ ...prev, state: 'loading', error: null }))
    try {
      const data = await api.listConflicts(statusFilter, 50)
      setListState({ state: 'success', data, error: null })
    } catch (err) {
      setListState({
        state: 'error',
        data: null,
        error: err instanceof Error ? err.message : 'Unknown error',
      })
    }
  }, [statusFilter])

  useEffect(() => {
    void load()
  }, [load])

  // Client-side sort (server returns all conflicts for the filter)
  const sorted = (() => {
    if (!listState.data) return []
    const items = [...listState.data.conflicts]
    items.sort((a, b) => {
      const av = a[sortBy]
      const bv = b[sortBy]
      return sortDir === 'desc' ? bv - av : av - bv
    })
    return items
  })()

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        {/* Page header */}
        <header className={styles.header}>
          <div className={styles.titleRow}>
            <h1 className={styles.title}>Conflict Queue</h1>
            {listState.data && (
              <span className={styles.total}>
                {listState.data.total} conflict{listState.data.total !== 1 ? 's' : ''}
              </span>
            )}
          </div>
          <p className={styles.subtitle}>
            Ranked by blast radius — the downstream systems, documents and
            decisions each conflict puts at risk.
          </p>
        </header>

        {/* Stats funnel bar */}
        {listState.data && (
          <StatsBar stats={listState.data.stats} />
        )}

        {/* Filters + sort */}
        <QueueFilters
          status={statusFilter}
          sortBy={sortBy}
          onStatusChange={setStatusFilter}
          onSortChange={setSortBy}
        />

        {/* Conflict list */}
        <section aria-label="Conflicts" className={styles.listSection}>
          {listState.state === 'loading' && <QueueSkeleton />}

          {listState.state === 'error' && (
            <div className={styles.error} role="alert">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
                <line x1="12" y1="8" x2="12" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                <line x1="12" y1="16" x2="12.01" y2="16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
              <div>
                <strong>Could not load conflicts</strong>
                <p>{listState.error}</p>
              </div>
              <button className={styles.retryBtn} onClick={() => void load()}>
                Retry
              </button>
            </div>
          )}

          {listState.state === 'success' && sorted.length === 0 && (
            <div className={styles.empty}>
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" />
              </svg>
              <h2>No conflicts found</h2>
              <p>
                {statusFilter === 'all'
                  ? 'The system has not detected any contradictions yet.'
                  : `No ${statusFilter} conflicts match the current filter.`}
              </p>
            </div>
          )}

          {listState.state === 'success' && sorted.length > 0 && (
            <ol className={styles.list} aria-label="Conflict list">
              {sorted.map((conflict, i) => (
                <li key={conflict.id} style={{ animationDelay: `${i * 40}ms` }}>
                  <ConflictRow
                    conflict={conflict}
                    rank={i + 1}
                    onSelect={onSelect}
                  />
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>
    </div>
  )
}

function QueueSkeleton() {
  return (
    <div aria-label="Loading conflicts" aria-busy="true">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className={styles.skeletonRow}>
          <div className={`skeleton ${styles.skeletonBlast}`} />
          <div className={styles.skeletonBody}>
            <div className={`skeleton ${styles.skeletonTitle}`} />
            <div className={`skeleton ${styles.skeletonSub}`} />
          </div>
        </div>
      ))}
    </div>
  )
}
