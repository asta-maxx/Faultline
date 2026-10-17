import { useEffect } from 'react'
import type { ConflictsResponse, HealthResponse } from '../../types'
import type { Async } from '../../lib/useAsync'
import { navigate } from '../../lib/router'
import { ConflictQueue } from './ConflictQueue'
import { Workspace } from './Workspace'
import styles from './ConflictsScreen.module.css'

interface Props {
  open: Async<ConflictsResponse>
  selectedId: string | null
  health: Async<HealthResponse>
}

export function ConflictsScreen({ open, selectedId, health }: Props) {
  const conflicts = open.status === 'ready' ? open.data.conflicts : null
  const top = conflicts?.length
    ? conflicts.reduce((best, c) => (c.blast_radius > best.blast_radius ? c : best))
    : null

  // With nothing selected, open the highest-ranked conflict.
  useEffect(() => {
    if (!selectedId && top) navigate({ name: 'conflicts', conflictId: top.id }, true)
  }, [selectedId, top])

  if (open.status === 'error') {
    return (
      <p className="notice" data-tone="error">
        <strong>The conflict queue did not load.</strong>
        <code>{open.error}</code> Check that the API is running on port 8000, then reload.
      </p>
    )
  }

  return (
    <div className={styles.screen}>
      {conflicts ? (
        <ConflictQueue
          conflicts={conflicts}
          selectedId={selectedId}
          onSelect={(id) => navigate({ name: 'conflicts', conflictId: id })}
        />
      ) : (
        <div />
      )}
      {selectedId ? <Workspace key={selectedId} conflictId={selectedId} health={health} /> : <div />}
    </div>
  )
}
