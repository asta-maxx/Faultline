import { useCallback, useMemo, useState } from 'react'
import type { Conflict, HealthResponse } from '../../types'
import { getConflict, useWorkspace } from '../../lib/api'
import type { Async } from '../../lib/useAsync'
import { useAsync } from '../../lib/useAsync'
import { buildGraphModel } from '../../lib/graphModel'
import { count, isoDate, score } from '../../lib/format'
import { EvidencePanel } from './EvidencePanel'
import type { Outcome } from './ConflictActions'
import { TraversalGraph } from '../graph/TraversalGraph'
import { GraphLegend } from '../graph/GraphLegend'
import { NodeInspector } from '../graph/NodeInspector'
import styles from './Workspace.module.css'

interface Props {
  conflictId: string
  health: Async<HealthResponse>
  onSettled: (conflict: Conflict, outcome: Outcome) => void
}

export function Workspace({ conflictId, health, onSettled }: Props) {
  const ws = useWorkspace()
  const detail = useAsync(() => getConflict(conflictId), `${ws.key}:${conflictId}`)
  // The inspected node lives in the URL (?node=<id>) so a view can be shared.
  const [inspected, setInspected] = useState<string | null>(readNodeParam)
  const inspect = useCallback((id: string | null) => {
    setInspected(id)
    writeNodeParam(id)
  }, [])

  const model = useMemo(
    () => (detail.status === 'ready' ? buildGraphModel(detail.data.conflict, detail.data.path) : null),
    [detail],
  )

  if (detail.status === 'error') {
    return (
      <p className="notice" data-tone="error">
        <strong>Conflict {conflictId} did not load.</strong>
        <code>{detail.error}</code>
      </p>
    )
  }
  if (detail.status === 'loading' || !model) return <div />

  const { conflict } = detail.data
  // /health counts the API's default graph; only quote it when that is this workspace's graph.
  const graphNodes =
    health.status === 'ready' && health.data.nodes > 0 && health.data.graph === `faultline:${ws.id}`
      ? health.data.nodes
      : null
  const inspectedNode = inspected ? (model.byId.get(inspected) ?? null) : null

  return (
    <section className={styles.workspace} aria-label={`Conflict ${conflict.id}`}>
      <header className={styles.head}>
        <p className="cap">
          <span>Conflict</span>
          <span className="dot">
            blast radius <b className={styles.radius}>{score(conflict.blast_radius)}</b>
          </span>
        </p>
        <p className="cap">
          <span>
            about <b className={styles.entity}>{conflict.entity.name}</b>
          </span>
          <span className="dot">{conflict.entity.type}</span>
          <span className="dot">found {isoDate(conflict.found_at)}</span>
        </p>
      </header>

      <div className={styles.graphRow} data-inspecting={inspectedNode ? 'true' : 'false'}>
        <div className={styles.graphCol}>
          <TraversalGraph model={model} selectedId={inspected} onSelect={inspect} />
          <GraphLegend
            model={model}
            caption={
              graphNodes !== null
                ? `${count(model.nodes.length)} of ${count(graphNodes)} nodes · the path behind this answer`
                : `${count(model.nodes.length)} nodes · the path behind this answer`
            }
          />
        </div>
        {inspectedNode ? (
          <NodeInspector
            model={model}
            node={inspectedNode}
            onSelect={inspect}
            onClose={() => inspect(null)}
          />
        ) : null}
      </div>

      <EvidencePanel conflict={conflict} precedent={detail.data.precedent} onSettled={onSettled} />
    </section>
  )
}

function readNodeParam(): string | null {
  return new URLSearchParams(window.location.search).get('node')
}

function writeNodeParam(id: string | null): void {
  const params = new URLSearchParams(window.location.search)
  if (id) params.set('node', id)
  else params.delete('node')
  const query = params.toString()
  window.history.replaceState(null, '', `${window.location.pathname}${query ? `?${query}` : ''}`)
}
