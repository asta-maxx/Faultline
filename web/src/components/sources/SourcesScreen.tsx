import { useState } from 'react'
import type { AuditRun, Source, Workspace } from '../../types'
import { errorText, getAudit, listSources, listWorkspaces, startAudit, useWorkspace } from '../../lib/api'
import { navigate } from '../../lib/router'
import { useAsync, type Async } from '../../lib/useAsync'
import { count, isoMinute, plural, relativeAge } from '../../lib/format'
import { Icon } from '../Icon'
import { SourceStatusMark } from './SourceStatusMark'
import styles from './SourcesScreen.module.css'

/** The current workspace's sources, and the way back into its latest audit. */
export function SourcesScreen() {
  const ws = useWorkspace()
  const sources = useAsync(() => listSources(ws.id), `sources:${ws.key}`)
  const workspaces = useAsync(listWorkspaces, `sources-workspaces:${ws.key}`)
  const workspace = workspaces.status === 'ready' ? (workspaces.data.find((w) => w.id === ws.id) ?? null) : null
  const latest = workspace?.latest_run ?? null
  // Summary counts live on the run; only a finished latest run speaks for last_audit.
  const doneRunId = latest?.status === 'done' ? latest.run_id : null
  const lastRun = useAsync<AuditRun | null>(
    () => (doneRunId ? getAudit(doneRunId) : Promise.resolve(null)),
    `last-run:${doneRunId ?? ''}:${ws.key}`,
  )

  const [busy, setBusy] = useState(false)
  const [auditError, setAuditError] = useState<string | null>(null)

  const rerun = async () => {
    setBusy(true)
    setAuditError(null)
    try {
      const { run_id } = await startAudit(ws.id)
      navigate({ name: 'audit', runId: run_id })
    } catch (err) {
      setAuditError(errorText(err))
      setBusy(false)
    }
  }

  return (
    <section className={styles.screen} aria-label="Sources">
      <header className={styles.head}>
        <p className="cap">
          <span>{sources.status === 'ready' ? plural(sources.data.length, 'source') : 'Sources'}</span>
          {workspace ? <span className="dot">{workspace.name}</span> : null}
          {workspace ? <span className="dot">{workspace.graph}</span> : null}
        </p>
        <div className={styles.actions}>
          <button
            type="button"
            className="btn"
            onClick={() => navigate({ name: 'setup', workspace: ws.id })}
          >
            Add source
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={
              busy || latest?.status === 'running' || (sources.status === 'ready' && sources.data.length === 0)
            }
            onClick={() => void rerun()}
          >
            Re-run audit
          </button>
        </div>
      </header>

      {auditError ? (
        <p className={styles.auditError} role="alert">
          {auditError}
        </p>
      ) : null}

      {latest?.status === 'running' ? (
        <p className={styles.running}>
          <Icon name="pending" size={14} />
          <span className={styles.runningWord}>Audit running</span>
          <span className={styles.meta}>
            {latest.run_id} · started {isoMinute(latest.started_at)} UTC
          </span>
          <a
            className="link"
            href={`/audit/${encodeURIComponent(latest.run_id)}`}
            onClick={(e) => {
              e.preventDefault()
              navigate({ name: 'audit', runId: latest.run_id })
            }}
          >
            View progress <Icon name="arrow-right" size={14} />
          </a>
        </p>
      ) : null}

      <div className={styles.body}>
        <SourceTable sources={sources} workspaceId={ws.id} />
        {workspace ? <LastAudit workspace={workspace} lastRun={lastRun} /> : null}
        {workspaces.status === 'error' ? (
          <p className={styles.footLine}>Workspace record did not load. {workspaces.error}</p>
        ) : null}
      </div>
    </section>
  )
}

function SourceTable({ sources, workspaceId }: { sources: Async<Source[]>; workspaceId: string }) {
  if (sources.status === 'loading') return null
  if (sources.status === 'error') {
    return (
      <p className="notice" data-tone="error">
        <strong>The sources for {workspaceId} did not load.</strong>
        <code>{sources.error}</code>
      </p>
    )
  }
  if (sources.data.length === 0) {
    return (
      <p className="notice">
        <strong>This workspace has no sources.</strong>
        Its graph was built some other way, or nothing has been added yet. Add a folder to audit it from here.
      </p>
    )
  }
  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th className="cap">Kind</th>
          <th className="cap">Location</th>
          <th className={`cap ${styles.numCol}`}>Documents</th>
          <th className={`cap ${styles.numCol}`}>Claims extracted</th>
          <th className="cap">Last read</th>
          <th className="cap">Status</th>
        </tr>
      </thead>
      <tbody>
        {sources.data.map((s) => (
          <tr key={s.id}>
            <td>
              <span className="chip">{s.kind}</span>
            </td>
            <td className={styles.locationCell}>
              <p className={styles.location} title={s.location}>
                {s.location}
              </p>
              {s.message ? <p className={styles.message}>{s.message}</p> : null}
              {s.has_token && !s.message ? (
                <p className={styles.message}>Token received but not stored: cloning is not implemented.</p>
              ) : null}
            </td>
            <td className={`${styles.num} ${styles.numCol}`}>
              {s.docs === null ? <span className={styles.none}>not scanned</span> : count(s.docs)}
            </td>
            <td className={`${styles.num} ${styles.numCol}`}>
              {s.claims === null ? <span className={styles.none}>not read</span> : count(s.claims)}
            </td>
            <td className={styles.num}>
              {s.last_read_at === null ? (
                <span className={styles.none}>never</span>
              ) : (
                <time dateTime={new Date(s.last_read_at * 1000).toISOString()} title={`${isoMinute(s.last_read_at)} UTC`}>
                  {relativeAge(s.last_read_at)}
                </time>
              )}
            </td>
            <td>
              <SourceStatusMark status={s.status} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/**
 * "Last audit <date> · N claims · N pairs compared · N judged". The date is the
 * workspace's last_audit; the counts come from the run's summary, and only
 * when the latest run is the finished one (otherwise the workspace's own claim
 * count is all that is known).
 */
function LastAudit({ workspace: w, lastRun }: { workspace: Workspace; lastRun: Async<AuditRun | null> }) {
  if (w.last_audit === null) {
    return <p className={styles.footLine}>No finished audit yet.</p>
  }
  const run = lastRun.status === 'ready' ? lastRun.data : null
  return (
    <p className={styles.footLine}>
      <span>Last audit {isoMinute(w.last_audit)} UTC</span>
      {run?.summary ? (
        <>
          <span className="dot">{plural(run.summary.claims, 'claim')}</span>
          <span className="dot">{count(run.summary.pairs_compared)} pairs compared</span>
          <span className="dot">{count(run.summary.judged)} judged</span>
          <a
            className={`link ${styles.runLink}`}
            href={`/audit/${encodeURIComponent(run.run_id)}`}
            onClick={(e) => {
              e.preventDefault()
              navigate({ name: 'audit', runId: run.run_id })
            }}
          >
            {run.run_id}
          </a>
        </>
      ) : (
        <span className="dot">{plural(w.claims, 'claim')} in the graph</span>
      )}
      {lastRun.status === 'error' ? <span className="dot">run summary did not load: {lastRun.error}</span> : null}
    </p>
  )
}
