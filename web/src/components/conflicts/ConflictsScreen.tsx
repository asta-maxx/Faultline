import { useEffect, useState } from 'react'
import type { Conflict, ConflictsResponse, HealthResponse } from '../../types'
import type { Async } from '../../lib/useAsync'
import { navigate } from '../../lib/router'
import { refreshWorkspaceData, useWorkspace } from '../../lib/api'
import { nextAfter, rankConflicts } from '../../lib/conflict'
import { ConflictQueue, type SettledNote } from './ConflictQueue'
import { Workspace } from './Workspace'
import type { Outcome } from './ConflictActions'
import styles from './ConflictsScreen.module.css'

interface Props {
  open: Async<ConflictsResponse>
  selectedId: string | null
  health: Async<HealthResponse>
}

export function ConflictsScreen({ open, selectedId, health }: Props) {
  const ws = useWorkspace()
  const conflicts = open.status === 'ready' ? open.data.conflicts : null
  const top = conflicts?.length ? rankConflicts(conflicts)[0] : null
  // What the last resolve or dismiss did, shown above the queue. Set only after the API answered 2xx.
  const [settled, setSettled] = useState<(SettledNote & { workspace: string }) | null>(null)

  const onSettled = (conflict: Conflict, outcome: Outcome) => {
    const next = conflicts ? nextAfter(conflicts, conflict.id) : null
    setSettled({ workspace: ws.id, outcome, entity: conflict.entity.name, conflictId: conflict.id })
    refreshWorkspaceData()
    navigate({ name: 'conflicts', conflictId: next?.id ?? null }, true)
  }

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
          settled={settled?.workspace === ws.id ? settled : null}
          onSelect={(id) => {
            setSettled(null)
            navigate({ name: 'conflicts', conflictId: id })
          }}
        />
      ) : (
        <div />
      )}
      {selectedId ? <Workspace key={selectedId} conflictId={selectedId} health={health} onSettled={onSettled} /> : <div />}
    </div>
  )
}
