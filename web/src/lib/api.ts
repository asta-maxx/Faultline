/**
 * Faultline API client — CONTRACT §9.
 *
 * In LIVE mode (VITE_API_BASE set), hits the real FastAPI backend.
 * In FIXTURE mode (default), reads from /fixtures/*.json via Vite's proxy.
 *
 * Live mode NEVER falls back silently to fixtures after a real error.
 * If the request fails, the returned AsyncState has state='error'.
 */

import type {
  ConflictDetailResponse,
  ConflictsResponse,
  ConflictStatusFilter,
  HealthResponse,
  ResolveConflictRequest,
  Stats,
} from '../types'

// Vite exposes VITE_* env vars as import.meta.env
const API_BASE = import.meta.env.VITE_API_BASE ?? ''

// When empty, requests go to same origin → Vite dev proxy serves /api/* from
// the FastAPI backend (configured in vite.config.ts).
// In production, FastAPI serves the built frontend and handles /api/* itself.

async function get<T>(path: string): Promise<T> {
  const url = `${API_BASE}${path}`
  const res = await fetch(url, {
    headers: { Accept: 'application/json' },
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`GET ${url} → ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const url = `${API_BASE}${path}`
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`POST ${url} → ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  /** GET /health */
  health(): Promise<HealthResponse> {
    return get<HealthResponse>('/api/health')
  },

  /** GET /conflicts?status=open&limit=20 */
  listConflicts(
    status: ConflictStatusFilter = 'all',
    limit = 50,
  ): Promise<ConflictsResponse> {
    const params = new URLSearchParams({ limit: String(limit) })
    if (status !== 'all') params.set('status', status)
    return get<ConflictsResponse>(`/api/conflicts?${params}`)
  },

  /** GET /conflicts/{id} */
  getConflict(id: string): Promise<ConflictDetailResponse> {
    return get<ConflictDetailResponse>(`/api/conflicts/${encodeURIComponent(id)}`)
  },

  /** GET /stats */
  getStats(): Promise<Stats> {
    return get<Stats>('/api/stats')
  },

  /** POST /conflicts/{id}/resolve */
  resolveConflict(
    id: string,
    body: ResolveConflictRequest,
  ): Promise<{ ok: true }> {
    return post(`/api/conflicts/${encodeURIComponent(id)}/resolve`, body)
  },
}
