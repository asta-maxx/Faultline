import type { Conflict, GraphNode, GraphEdge } from '../../types'
import { formatEpoch } from '../../lib/utils'
import styles from './EvidencePanel.module.css'

type Selection =
  | { kind: 'none' }
  | { kind: 'node'; node: GraphNode }
  | { kind: 'edge'; edge: GraphEdge }

interface EvidencePanelProps {
  conflict: Conflict
  selection: Selection
}

export function EvidencePanel({ conflict, selection }: EvidencePanelProps) {
  if (selection.kind === 'node') {
    return <NodeDetail node={selection.node} conflict={conflict} />
  }

  if (selection.kind === 'edge') {
    return <EdgeDetail edge={selection.edge} />
  }

  return <DefaultPanel conflict={conflict} />
}

function DefaultPanel({ conflict }: { conflict: Conflict }) {
  return (
    <section className={styles.panel} aria-labelledby="evidence-heading">
      <h3 id="evidence-heading" className={styles.heading}>Evidence</h3>
      <p className={styles.hint}>
        Select a node or edge in the traversal graph to inspect its provenance.
      </p>

      {/* Quick evidence from claims */}
      {conflict.claims.map(claim => (
        <div key={claim.id} className={styles.evidenceItem}>
          <div className={styles.evidenceHeader}>
            <span className={`${styles.sideChip} ${claim.side === 'a' ? styles.chipA : styles.chipB}`}>
              {claim.side.toUpperCase()}
            </span>
            <span className={styles.claimSource}>{claim.source.title}</span>
          </div>
          <div className={styles.evidenceSpan}>
            <span className={styles.evidenceLabel}>Evidence span</span>
            <mark className={styles.evidenceMark}>{claim.evidence_span}</mark>
          </div>
          <code className={styles.sourcePath}>{claim.source.path}</code>
        </div>
      ))}
    </section>
  )
}

function NodeDetail({ node, conflict }: { node: GraphNode; conflict: Conflict }) {
  // Try to enrich from conflict claims if it matches a known claim id
  const matchingClaim = conflict.claims.find(c => c.id === node.id)

  return (
    <section className={styles.panel} aria-labelledby="node-detail-heading" aria-live="polite">
      <h3 id="node-detail-heading" className={styles.heading}>
        Node detail
      </h3>

      <div className={styles.nodeType}>
        <NodeTypeIcon type={node.type} />
        <span className={styles.typeName}>{node.type}</span>
        {node.state && <StateIndicator state={node.state} />}
      </div>

      <div className={styles.fieldGroup}>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Label</span>
          <span className={styles.fieldValue}>{node.label}</span>
        </div>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>ID</span>
          <code className={styles.fieldMono}>{node.id}</code>
        </div>
      </div>

      {/* Claim-specific enrichment */}
      {matchingClaim && (
        <div className={styles.enrichment}>
          <div className={styles.field}>
            <span className={styles.fieldLabel}>Full claim text</span>
            <blockquote className={styles.claimText}>&ldquo;{matchingClaim.text}&rdquo;</blockquote>
          </div>
          <div className={styles.field}>
            <span className={styles.fieldLabel}>Evidence span</span>
            <mark className={styles.evidenceMark}>{matchingClaim.evidence_span}</mark>
          </div>
          <div className={styles.field}>
            <span className={styles.fieldLabel}>Confidence</span>
            <span className={styles.fieldValue}>
              {Math.round(matchingClaim.confidence * 100)}%
            </span>
          </div>
          <div className={styles.field}>
            <span className={styles.fieldLabel}>Source</span>
            <span className={styles.fieldValue}>{matchingClaim.source.title}</span>
          </div>
          <div className={styles.field}>
            <span className={styles.fieldLabel}>Source path</span>
            <code className={styles.fieldMono}>{matchingClaim.source.path}</code>
          </div>
          {matchingClaim.source.updated_at && (
            <div className={styles.field}>
              <span className={styles.fieldLabel}>Document updated</span>
              <span className={styles.fieldValue}>
                {formatEpoch(matchingClaim.source.updated_at)}
              </span>
            </div>
          )}
        </div>
      )}
    </section>
  )
}

function EdgeDetail({ edge }: { edge: GraphEdge }) {
  return (
    <section className={styles.panel} aria-labelledby="edge-detail-heading" aria-live="polite">
      <h3 id="edge-detail-heading" className={styles.heading}>Edge detail</h3>

      <div className={styles.edgeType}>
        <span className={styles.edgeTypeName}>{edge.type}</span>
      </div>

      <div className={styles.fieldGroup}>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>From</span>
          <code className={styles.fieldMono}>{edge.source}</code>
        </div>
        <svg className={styles.edgeArrow} width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>To</span>
          <code className={styles.fieldMono}>{edge.target}</code>
        </div>
      </div>
    </section>
  )
}

function NodeTypeIcon({ type }: { type: string }) {
  const iconMap: Record<string, string> = {
    claim: '◆',
    document: '▤',
    decision: '⬡',
    system: '⬢',
    person: '◉',
    message: '◎',
    ticket: '◫',
    entity: '◈',
  }
  return (
    <span className={`${styles.typeIcon} ${styles[`icon_${type}`]}`} aria-hidden="true">
      {iconMap[type] ?? '◇'}
    </span>
  )
}

function StateIndicator({ state }: { state: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    live: { label: '✓ Live', cls: styles.stateLive },
    contradicted: { label: '✕ Contradicted', cls: styles.stateContradicted },
    superseded: { label: '» Superseded', cls: styles.stateSuperseded },
  }
  const info = map[state] ?? { label: state, cls: '' }
  return <span className={`${styles.stateIndicator} ${info.cls}`}>{info.label}</span>
}
