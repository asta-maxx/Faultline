import { useEffect, useState } from 'react'
import type { AuditRun, AuditStage, AuditStageState } from '../../types'
import { currentWorkspaceId, errorText, getAudit, refreshWorkspaceData, setWorkspace } from '../../lib/api'
import { navigate } from '../../lib/router'
import { count, duration, isoMinute, plural } from '../../lib/format'
import { Icon } from '../Icon'
import type { IconName } from '../../lib/icons'
import styles from './AuditScreen.module.css'

const POLL_MS = 1000

interface PollState {
  run: AuditRun | null
  /** the latest poll failed; the last good run (if any) stays on screen */
  error: string | null
  /** the run was still going when this page first saw it, so the bars may move */
  live: boolean
  /** epoch seconds of the last good poll; elapsed time is measured to it */
  polledAt: number
}

/**
 * One audit run, polled every second until it is done or failed. A run that
 * is already finished when the page loads is shown finished, not replayed.
 */
export function AuditScreen({ runId }: { runId: string }) {
  const [state, setState] = useState<PollState>({ run: null, error: null, live: false, polledAt: 0 })

  useEffect(() => {
    let cancelled = false
    let timer: number | undefined
    let first = true
    let sawRunning = false

    const poll = async () => {
      try {
        const run = await getAudit(runId)
        if (cancelled) return
        if (first && run.status === 'running') sawRunning = true
        first = false
        setState({ run, error: null, live: sawRunning, polledAt: Date.now() / 1000 })
        if (run.status === 'running') {
          timer = window.setTimeout(poll, POLL_MS)
        } else if (sawRunning && run.workspace_id === currentWorkspaceId()) {
          // The graph behind the queue just changed under us.
          refreshWorkspaceData()
        }
      } catch (err) {
        if (cancelled) return
        first = false
        setState((s) => ({ ...s, error: errorText(err) }))
        // Keep trying while a run we saw running may still be going; a run never seen is not chased.
        if (sawRunning) timer = window.setTimeout(poll, POLL_MS)
      }
    }
    void poll()
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [runId])

  const { run, error, live, polledAt } = state

  if (!run) {
    if (!error) return <div className={styles.screen} />
    return (
      <div className={styles.screen}>
        <p className="notice" data-tone="error">
          <strong>Audit {runId} did not load.</strong>
          <code>{error}</code>
        </p>
      </div>
    )
  }

  const max = run.stages.reduce((m, s) => Math.max(m, s.count ?? 0), 0)

  return (
    <section className={styles.screen} aria-label={`Audit ${run.run_id}`}>
      <header className={styles.head}>
        <p className="cap">
          <span>Audit</span>
          <span className="dot">
            <span className={styles.id}>{run.workspace_id}</span>
          </span>
          <span className="dot">
            run <span className={styles.id}>{run.run_id}</span>
          </span>
          <span className="dot">started {isoMinute(run.started_at)} UTC</span>
          <span className="dot">{duration(run.started_at, run.ended_at ?? polledAt)}</span>
        </p>
        <RunMark status={run.status} />
      </header>

      <div className={styles.body}>
        <p className={`cap ${styles.axis}`}>
          <span>Stage</span>
          <span>Count</span>
          <span>Bar length · log scale, longest = {max ? count(max) : '0'}</span>
        </p>
        <ol className={styles.stages} data-live={live ? 'true' : 'false'}>
          {run.stages.map((s) => (
            <li key={s.name}>
              <StageRow stage={s} max={max} />
            </li>
          ))}
        </ol>

        <p className={styles.current} aria-live="polite">
          {run.status === 'running' ? (run.current ?? '') : ''}
        </p>

        {error ? (
          <p className={styles.pollError}>
            Last poll failed, retrying every second. <code>{error}</code>
          </p>
        ) : null}

        {run.status === 'done' ? <Finished run={run} /> : null}

        {run.status === 'failed' ? (
          <div className={styles.failed}>
            <p className={styles.failedHead}>
              <Icon name="state-contradicted" size={20} />
              The audit failed.
            </p>
            <code>{run.error ?? 'The API recorded no reason.'}</code>
          </div>
        ) : null}
      </div>
    </section>
  )
}

function Finished({ run }: { run: AuditRun }) {
  const viewConflicts = () => {
    if (run.workspace_id === currentWorkspaceId()) refreshWorkspaceData()
    else setWorkspace(run.workspace_id)
    navigate({ name: 'conflicts', conflictId: null })
  }

  return (
    <div className={styles.finished}>
      {run.summary ? (
        <p className="display">
          {plural(run.summary.contradictions, 'contradiction')} found in {plural(run.summary.documents, 'document')}
        </p>
      ) : (
        <p className={styles.missing}>The run is marked done but carries no summary.</p>
      )}
      <button type="button" className="btn btn-primary" onClick={viewConflicts}>
        View conflicts
      </button>
    </div>
  )
}

const STAGE_MARK: Record<AuditStageState, { icon: IconName; word: string }> = {
  done: { icon: 'resolved', word: 'Done' },
  active: { icon: 'pending', word: 'Running' },
  pending: { icon: 'pending', word: 'Pending' },
  failed: { icon: 'state-contradicted', word: 'Failed' },
}

function StageRow({ stage: s, max }: { stage: AuditStage; max: number }) {
  // log10(n + 1) keeps 296 and 1.7 million on the same ruler and both readable.
  const fraction = s.count !== null && max > 0 ? Math.log10(s.count + 1) / Math.log10(max + 1) : 0
  const mark = STAGE_MARK[s.state]

  return (
    <article className={styles.stage} data-state={s.state}>
      <div className={styles.name}>
        <h2>{s.name}</h2>
        <p className={styles.mark}>
          <Icon name={mark.icon} size={14} />
          {mark.word}
          {s.started_at !== null && s.ended_at !== null ? (
            <span className={styles.took}>{duration(s.started_at, s.ended_at)}</span>
          ) : null}
        </p>
      </div>
      <div className={styles.count}>
        <span className={styles.value}>{s.count === null ? '–' : count(s.count)}</span>
        <span className={styles.unit}>
          {s.unit}
          {s.detail ? <span className={styles.detail}>{s.detail}</span> : null}
        </span>
      </div>
      <div className={styles.track}>
        <span className={styles.bar} style={{ transform: `scaleX(${fraction})` }} />
      </div>
    </article>
  )
}

function RunMark({ status }: { status: AuditRun['status'] }) {
  const mark =
    status === 'done'
      ? { icon: 'resolved' as const, word: 'Finished' }
      : status === 'failed'
        ? { icon: 'state-contradicted' as const, word: 'Failed' }
        : { icon: 'pending' as const, word: 'Running' }
  return (
    <p className={styles.runMark} data-status={status}>
      <Icon name={mark.icon} size={14} />
      {mark.word}
    </p>
  )
}
