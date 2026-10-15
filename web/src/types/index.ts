/**
 * Faultline frontend types — derived from CONTRACT.md §9 (frozen).
 * Field names must match the backend response exactly.
 */

// ── Claim state ───────────────────────────────────────────────────────────────
export type ClaimState = 'live' | 'contradicted' | 'superseded'

// ── Conflict kinds and statuses ───────────────────────────────────────────────
export type ConflictKind = 'direct' | 'superseded' | 'undocumented'
export type ConflictStatus = 'open' | 'resolved' | 'dismissed'

// ── Source document reference ─────────────────────────────────────────────────
export interface ClaimSource {
  doc_id: string
  title: string
  path: string
  updated_at: number // epoch seconds
}

// ── A claim as it appears on a Conflict ───────────────────────────────────────
export interface ConflictClaim {
  side: 'a' | 'b'
  id: string
  text: string
  confidence: number
  evidence_span: string
  state: ClaimState
  source: ClaimSource
}

// ── Impact / blast radius summary ─────────────────────────────────────────────
export interface ConflictImpact {
  doc_count: number
  system_count: number
  systems: string[]
}

// ── Person / owner ────────────────────────────────────────────────────────────
export interface Person {
  id: string
  name: string
  role: string
}

// ── Entity ────────────────────────────────────────────────────────────────────
export type EntityType = 'system' | 'policy' | 'metric' | 'process' | 'artifact'

export interface Entity {
  id: string
  name: string
  type: EntityType
}

// ── Full Conflict (CONTRACT §9) ───────────────────────────────────────────────
export interface Conflict {
  id: string
  kind: ConflictKind
  status: ConflictStatus
  blast_radius: number
  found_at: number // epoch seconds
  entity: Entity
  claims: ConflictClaim[]
  impact: ConflictImpact
  owner: Person | null
}

// ── Graph path node (CONTRACT §9) ─────────────────────────────────────────────
export type NodeType =
  | 'claim'
  | 'document'
  | 'decision'
  | 'system'
  | 'person'
  | 'message'
  | 'ticket'
  | 'entity'
  | 'conflict'

export interface GraphNode {
  id: string
  label: string
  type: NodeType
  state?: ClaimState
}

// ── Graph path edge (CONTRACT §9) ─────────────────────────────────────────────
export type EdgeType =
  | 'ASSERTS'
  | 'ABOUT'
  | 'CONTRADICTS'
  | 'SUPERSEDES'
  | 'CITES'
  | 'GOVERNS'
  | 'AUTHORED'
  | 'OWNS'
  | 'DERIVED_FROM'
  | 'INVOLVES'
  | 'RESOLVED_AS'

export interface GraphEdge {
  source: string
  target: string
  type: EdgeType
}

// ── GraphPath (CONTRACT §9) ───────────────────────────────────────────────────
export interface GraphPath {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

// ── Stats (CONTRACT §9) ───────────────────────────────────────────────────────
export interface Stats {
  claims: number
  documents: number
  entities: number
  naive_pair_count: number
  collapsed_pair_count: number
  prefiltered_pair_count: number
  judged_pair_count: number
  conflicts_open: number
  conflicts_resolved: number
}

// ── API list response ─────────────────────────────────────────────────────────
export interface ConflictsResponse {
  conflicts: Conflict[]
  total: number
  stats: Stats
}

// ── API single conflict response ──────────────────────────────────────────────
export interface ConflictDetailResponse {
  conflict: Conflict
  path: GraphPath
}

// ── Health response ───────────────────────────────────────────────────────────
export interface HealthResponse {
  ok: boolean
  graph: string
  nodes: number
  edges: number
  falkor: 'up' | 'down'
}

// ── Resolve conflict request ──────────────────────────────────────────────────
export interface ResolveConflictRequest {
  winner_claim_id: string
  rationale: string
  resolved_by: string
}

// ── API error ─────────────────────────────────────────────────────────────────
export interface ApiError {
  error: string
}

// ── Filter / sort options ─────────────────────────────────────────────────────
export type ConflictStatusFilter = 'all' | ConflictStatus
export type ConflictSortField = 'blast_radius' | 'found_at'
export type SortDirection = 'asc' | 'desc'

export interface ConflictFilters {
  status: ConflictStatusFilter
  kind?: ConflictKind
  sortBy: ConflictSortField
  sortDir: SortDirection
  limit: number
}

// ── UI State ──────────────────────────────────────────────────────────────────
export type LoadingState = 'idle' | 'loading' | 'success' | 'error'

export interface AsyncState<T> {
  state: LoadingState
  data: T | null
  error: string | null
}
