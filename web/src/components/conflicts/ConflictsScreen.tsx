import { useEffect, useState } from 'react'
import type { Conflict, ConflictsResponse, HealthResponse } from '../../types'
import type { Async } from '../../lib/useAsync'
import { navigate } from '../../lib/router'
import { readStorage, refreshWorkspaceData, useWorkspace, writeStorage } from '../../lib/api'
import { count } from '../../lib/format'
import { Icon } from '../Icon'
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
    <div className={styles.page}>
      {ws.id === DEMO_WORKSPACE && conflicts && conflicts.length > 0 ? <DemoBanner open={conflicts.length} /> : null}
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
    </div>
  )
}

const DEMO_WORKSPACE = 'northwind'
const BANNER_KEY = 'faultline.demo_banner_dismissed'

/** First visit to the sample workspace: say what it is and where to go next. Dismissal is remembered. */
function DemoBanner({ open }: { open: number }) {
  const [dismissed, setDismissed] = useState(() => readStorage(BANNER_KEY) === '1')
  if (dismissed) return null
  return (
    <aside className={styles.banner} aria-label="About this workspace">
      <p className={styles.bannerText}>
        <strong>Sample company.</strong> Northwind Logistics is generated data; Faultline found{' '}
        {open === 1 ? 'this contradiction' : `these ${count(open)} contradictions`} on its own.
      </p>
      <a
        className="link"
        href="/setup"
        onClick={(e) => {
          e.preventDefault()
          navigate({ name: 'setup', workspace: null })
        }}
      >
        Audit your own repository <Icon name="arrow-right" size={14} />
      </a>
      <button
        type="button"
        className={styles.bannerClose}
        aria-label="Dismiss"
        title="Dismiss"
        onClick={() => {
          writeStorage(BANNER_KEY, '1')
          setDismissed(true)
        }}
      >
        <Icon name="close" size={14} />
      </button>
    </aside>
  )
}
