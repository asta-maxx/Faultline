import { useEffect, useState, useCallback } from 'react'
import { api } from '../../lib/api'
import type {
  Conflict,
  ConflictDetailResponse,
  GraphNode,
  GraphEdge,
  AsyncState,
} from '../../types'
import { ConflictSummary } from './ConflictSummary'
import { ClaimsComparison } from './ClaimsComparison'
import { EvidencePanel } from './EvidencePanel'
import { TraversalGraph } from './TraversalGraph'
import styles from './InvestigationWorkspace.module.css'

interface InvestigationWorkspaceProps {
  conflict: Conflict
  onBack: () => void
}

type Selection =
  | { kind: 'none' }
  | { kind: 'node'; node: GraphNode }
  | { kind: 'edge'; edge: GraphEdge }

export function InvestigationWorkspace({ conflict, onBack }: InvestigationWorkspaceProps) {
  const [detailState, setDetailState] = useState<AsyncState<ConflictDetailResponse>>({
    state: 'idle',
    data: null,
    error: null,
  })
  const [selection, setSelection] = useState<Selection>({ kind: 'none' })

  const load = useCallback(async () => {
    setDetailState({ state: 'loading', data: null, error: null })
    try {
      const data = await api.getConflict(conflict.id)
      setDetailState({ state: 'success', data, error: null })
    } catch (err) {
      setDetailState({
        state: 'error',
        data: null,
        error: err instanceof Error ? err.message : 'Unknown error',
      })
    }
  }, [conflict.id])

  useEffect(() => {
    void load()
    setSelection({ kind: 'none' })
  }, [load])

  // The conflict data we display — prefer the detail response (has GraphPath)
  // but fall back to the summary passed from the queue while loading.
  const displayConflict = detailState.data?.conflict ?? conflict

  return (
    <div className={styles.workspace}>
      {/* Back navigation */}
      <div className={styles.nav}>
        <button className={styles.backBtn} onClick={onBack} aria-label="Back to conflict queue">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M19 12H5M12 5l-7 7 7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Back to queue
        </button>
        <span className={styles.conflictId} aria-label={`Conflict ID ${conflict.id}`}>
          {conflict.id}
        </span>
      </div>

      <div className={styles.layout}>
        {/* Left column: summary + claims + evidence */}
        <div className={styles.leftCol}>
          <ConflictSummary conflict={displayConflict} />
          <ClaimsComparison claims={displayConflict.claims} />

          {detailState.state === 'error' && (
            <div className={styles.loadError} role="alert">
              <strong>Failed to load conflict detail</strong>
              <p>{detailState.error}</p>
              <button className={styles.retryBtn} onClick={() => void load()}>
                Retry
              </button>
            </div>
          )}

          <EvidencePanel
            conflict={displayConflict}
            selection={selection}
          />
        </div>

        {/* Right column: traversal graph */}
        <div className={styles.rightCol}>
          {detailState.state === 'loading' && (
            <div className={styles.graphLoading} role="status" aria-label="Loading traversal graph">
              <div className={styles.graphSpinner} aria-hidden="true" />
              <span>Loading traversal path…</span>
            </div>
          )}

          {detailState.state === 'success' && detailState.data && (
            <TraversalGraph
              path={detailState.data.path}
              conflictId={conflict.id}
              claims={displayConflict.claims}
              selection={selection}
              onNodeSelect={node => setSelection({ kind: 'node', node })}
              onEdgeSelect={edge => setSelection({ kind: 'edge', edge })}
              onDeselect={() => setSelection({ kind: 'none' })}
            />
          )}

          {detailState.state === 'error' && (
            <div className={styles.graphError}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <line x1="12" y1="9" x2="12" y2="13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                <line x1="12" y1="17" x2="12.01" y2="17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
              <p>Graph data unavailable</p>
              <button className={styles.retryBtn} onClick={() => void load()}>
                Retry
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
