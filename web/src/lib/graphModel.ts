/**
 * Derived view of one conflict's GraphPath. Everything here is computed from
 * the API response; nothing is filled in.
 *
 * Dates: a node's `at` (CONTRACT §9 v5) is used when the API sends it. Without
 * it (v4 responses, the fixtures), the only dates are each claim's
 * `source.updated_at`: a document is dated when its id matches a claim's
 * `source.doc_id`, and a claim takes its source's date. Anything else is undated.
 */
import type { ClaimState, Conflict, ConflictClaim, EdgeType, GraphEdge, GraphNode, GraphPath, NodeType } from '../types'
import { capitalize, isoMonth, shortId } from './format'

export interface ModelNode extends GraphNode {
  /** "Claim A", "Document", ... */
  heading: string
  /** epoch seconds, when the response provides one */
  date: number | null
  claim: ConflictClaim | null
}

export interface GraphModel {
  nodes: ModelNode[]
  edges: GraphEdge[]
  byId: Map<string, ModelNode>
  typeCounts: { type: NodeType; count: number }[]
  stateCounts: { state: ClaimState; count: number }[]
}

const TYPE_ORDER: NodeType[] = ['claim', 'document', 'decision', 'system', 'entity', 'person', 'message', 'ticket', 'conflict']
const STATE_ORDER: ClaimState[] = ['live', 'contradicted', 'superseded']

export function buildGraphModel(conflict: Conflict, path: GraphPath): GraphModel {
  const claimById = new Map(conflict.claims.map((c) => [c.id, c]))
  const sourceDate = new Map(conflict.claims.map((c) => [c.source.doc_id, c.source.updated_at]))

  const nodes: ModelNode[] = path.nodes.map((n) => {
    const claim = claimById.get(n.id) ?? null
    return {
      ...n,
      heading: claim ? `Claim ${claim.side.toUpperCase()}` : capitalize(n.type),
      date: n.at ?? (claim ? claim.source.updated_at : (sourceDate.get(n.id) ?? null)),
      claim,
    }
  })
  const byId = new Map(nodes.map((n) => [n.id, n]))
  // Drop edges whose endpoints are not in the path (Cytoscape rejects them) and
  // repeated rows, which §7.5's OPTIONAL MATCHes can produce.
  const seen = new Set<string>()
  const edges = path.edges.filter((e) => {
    const key = `${e.source}|${e.type}|${e.target}`
    if (seen.has(key) || !byId.has(e.source) || !byId.has(e.target)) return false
    seen.add(key)
    return true
  })

  const typeCounts = TYPE_ORDER.map((type) => ({ type, count: nodes.filter((n) => n.type === type).length })).filter(
    (t) => t.count > 0,
  )
  const stateCounts = STATE_ORDER.map((state) => ({ state, count: nodes.filter((n) => n.state === state).length })).filter(
    (s) => s.count > 0,
  )

  return { nodes, edges, byId, typeCounts, stateCounts }
}

const CANVAS_LABEL_MAX = 40 // two wrapped lines at the canvas label width

/**
 * Label drawn under a node on the canvas: at most two lines. The icon carries
 * the type, the gutter carries the month, and the inspector carries the rest.
 * Claims keep their side, which the icon cannot show.
 */
export function canvasLabel(n: ModelNode): string {
  const text = n.claim ? `${n.claim.side.toUpperCase()} · ${n.label}` : n.label || `#${shortId(n.id)}`
  return text.length > CANVAS_LABEL_MAX ? `${text.slice(0, CANVAS_LABEL_MAX - 1).trimEnd()}…` : text
}

// ── Date bands ───────────────────────────────────────────────────────────────

/** §5 gives these labels no date property at all, so they sit outside time. */
export const TIMELESS: ReadonlySet<NodeType> = new Set<NodeType>(['system', 'entity', 'person'])

export interface Band {
  key: string
  /** "2026-09", or null for the undated band */
  month: string | null
  nodeIds: string[]
}

/**
 * Newest month first, then an undated band for nodes whose label has a date in
 * §5 that the response did not carry. Timeless nodes are not banded.
 */
export function dateBands(nodes: ModelNode[]): Band[] {
  const months = new Map<string, string[]>()
  const undated: string[] = []
  for (const n of nodes) {
    if (TIMELESS.has(n.type)) continue
    if (n.date === null) undated.push(n.id)
    else {
      const m = isoMonth(n.date)
      months.set(m, [...(months.get(m) ?? []), n.id])
    }
  }
  const bands: Band[] = [...months.entries()]
    .sort(([a], [b]) => (a < b ? 1 : -1))
    .map(([month, nodeIds]) => ({ key: month, month, nodeIds }))
  if (undated.length) bands.push({ key: 'undated', month: null, nodeIds: undated })
  return bands
}

// ── Relationships for the inspector ──────────────────────────────────────────

export interface RelationGroup {
  edge: EdgeType
  direction: 'out' | 'in'
  nodes: ModelNode[]
}

export function relationships(model: GraphModel, id: string): RelationGroup[] {
  const groups = new Map<string, RelationGroup>()
  for (const e of model.edges) {
    const direction = e.source === id ? 'out' : e.target === id ? 'in' : null
    if (!direction) continue
    const other = model.byId.get(direction === 'out' ? e.target : e.source)
    if (!other) continue
    const key = `${e.type}:${direction}`
    const group = groups.get(key) ?? { edge: e.type, direction, nodes: [] }
    group.nodes.push(other)
    groups.set(key, group)
  }
  return [...groups.values()]
}

/**
 * Systems this node reaches in the path: through the documents that assert it
 * (claims), cite it (decisions), assert claims derived from it (messages,
 * tickets), or the document itself, then along GOVERNS.
 */
export function involvedSystems(model: GraphModel, id: string): ModelNode[] {
  const node = model.byId.get(id)
  if (!node) return []
  if (node.type === 'system') return [node]

  const sourcesOf = (target: string, type: EdgeType) =>
    model.edges.filter((e) => e.target === target && e.type === type).map((e) => e.source)

  let docs: string[] = []
  if (node.type === 'document') docs = [id]
  else if (node.type === 'claim') docs = sourcesOf(id, 'ASSERTS')
  else if (node.type === 'decision') docs = sourcesOf(id, 'CITES')
  else if (node.type === 'message' || node.type === 'ticket') {
    docs = sourcesOf(id, 'DERIVED_FROM').flatMap((claimId) => sourcesOf(claimId, 'ASSERTS'))
  }

  const systems = new Map<string, ModelNode>()
  for (const e of model.edges) {
    if (e.type === 'GOVERNS' && docs.includes(e.source)) {
      const s = model.byId.get(e.target)
      if (s) systems.set(s.id, s)
    }
  }
  return [...systems.values()]
}
