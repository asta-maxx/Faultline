import { useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent, type ReactNode } from 'react'
import type { Conflict, DraftResponse, Precedent } from '../../types'
import {
  ApiError,
  currentWorkspaceId,
  dismissConflict,
  draftCorrection,
  errorText,
  refreshWorkspaceData,
  resolveConflict,
} from '../../lib/api'
import { navigate, routePath } from '../../lib/router'
import { sides } from '../../lib/conflict'
import { isoDate } from '../../lib/format'
import { Icon, StateMark } from '../Icon'
import styles from './ConflictActions.module.css'

export type Outcome = 'resolved' | 'dismissed'

interface Props {
  conflict: Conflict
  /** v7. Undefined when the response has no precedent field: the line is then hidden. */
  precedent: Precedent | undefined
  /** Called only after the API answered 2xx to /resolve or /dismiss. */
  onSettled: (conflict: Conflict, outcome: Outcome) => void
}

type Panel = 'draft' | 'ticket' | 'resolve' | 'dismiss' | null

type DraftState =
  | { status: 'idle' }
  | { status: 'busy'; via: 'draft' | 'ticket' }
  | { status: 'ready'; data: DraftResponse }
  | { status: 'error'; error: unknown }

/** The action strip under the evidence, and the one inline tray it opens. */
export function ConflictActions({ conflict, precedent, onSettled }: Props) {
  const [panel, setPanel] = useState<Panel>(null)
  const [draft, setDraft] = useState<DraftState>({ status: 'idle' })
  const [settling, setSettling] = useState(false)
  const alive = useRef(true)
  const trayId = useId()
  const triggers = useRef<Partial<Record<Exclude<Panel, null>, HTMLButtonElement | null>>>({})

  useEffect(() => {
    alive.current = true
    return () => {
      alive.current = false
    }
  }, [])

  const close = () => {
    const from = panel
    setPanel(null)
    if (from) triggers.current[from]?.focus()
  }

  const toggle = (next: Exclude<Panel, null>) => {
    if (panel === next) {
      setPanel(null)
      return
    }
    setPanel(next)
    if (next === 'draft' || next === 'ticket') requestDraft(next)
  }

  // One /draft call serves both views; it is only repeated after a failure.
  const requestDraft = (via: 'draft' | 'ticket') => {
    if (draft.status === 'busy' || draft.status === 'ready') return
    setDraft({ status: 'busy', via })
    draftCorrection(conflict.id).then(
      (data) => alive.current && setDraft({ status: 'ready', data }),
      (error: unknown) => alive.current && setDraft({ status: 'error', error }),
    )
  }

  if (conflict.status !== 'open') {
    return (
      <div className={styles.strip}>
        <SettledStatus conflict={conflict} />
        <PrecedentLine precedent={precedent} currentId={conflict.id} />
      </div>
    )
  }

  const drafting = draft.status === 'busy'
  const owner = conflict.owner

  return (
    <div onKeyDown={(e: KeyboardEvent) => e.key === 'Escape' && panel && !settling && close()}>
      <div className={styles.strip}>
        <button
          ref={(el) => {
            triggers.current.draft = el
          }}
          type="button"
          className="btn btn-primary"
          aria-expanded={panel === 'draft'}
          aria-controls={trayId}
          aria-busy={drafting && draft.via === 'draft'}
          disabled={drafting || settling}
          onClick={() => toggle('draft')}
        >
          {drafting && draft.via === 'draft' ? 'Drafting…' : 'Draft correction'}
        </button>
        <button
          ref={(el) => {
            triggers.current.ticket = el
          }}
          type="button"
          className="btn"
          aria-expanded={panel === 'ticket'}
          aria-controls={trayId}
          aria-busy={drafting && draft.via === 'ticket'}
          disabled={!owner || drafting || settling}
          title={
            owner
              ? `Opens a ticket addressed to ${owner.name}. Faultline has no assignment endpoint; you send the ticket.`
              : 'No person owns a system downstream of either claim, so there is nobody to address a ticket to.'
          }
          onClick={() => toggle('ticket')}
        >
          {!owner ? 'No owner to assign' : drafting && draft.via === 'ticket' ? 'Drafting ticket…' : `Assign to ${owner.name}`}
        </button>
        <button
          ref={(el) => {
            triggers.current.resolve = el
          }}
          type="button"
          className="btn"
          aria-expanded={panel === 'resolve'}
          aria-controls={trayId}
          disabled={settling}
          onClick={() => toggle('resolve')}
        >
          Resolve
        </button>
        <button
          ref={(el) => {
            triggers.current.dismiss = el
          }}
          type="button"
          className="btn"
          aria-expanded={panel === 'dismiss'}
          aria-controls={trayId}
          disabled={settling}
          onClick={() => toggle('dismiss')}
        >
          Dismiss
        </button>
        <PrecedentLine precedent={precedent} currentId={conflict.id} />
      </div>

      <div id={trayId} className={styles.tray} hidden={!panel}>
        {panel === 'draft' || panel === 'ticket' ? (
          <DraftView
            draft={draft}
            focus={panel}
            onShowCorrection={() => setPanel('draft')}
            onRetry={() => requestDraft(panel)}
          />
        ) : null}
        {panel === 'resolve' ? (
          <SettleForm
            mode="resolve"
            conflict={conflict}
            onBusy={setSettling}
            onCancel={close}
            onDone={(c) => onSettled(c, 'resolved')}
          />
        ) : null}
        {panel === 'dismiss' ? (
          <SettleForm
            mode="dismiss"
            conflict={conflict}
            onBusy={setSettling}
            onCancel={close}
            onDone={(c) => onSettled(c, 'dismissed')}
          />
        ) : null}
      </div>
    </div>
  )
}

// ── Draft ────────────────────────────────────────────────────────────────────

function DraftView({
  draft,
  focus,
  onShowCorrection,
  onRetry,
}: {
  draft: DraftState
  focus: 'draft' | 'ticket'
  onShowCorrection: () => void
  onRetry: () => void
}) {
  if (draft.status === 'idle' || draft.status === 'busy') {
    // The button carries the busy state; the tray says what is happening in words.
    return (
      <p className={styles.waiting} role="status">
        Asking the API to draft a correction for this conflict. The first draft takes a few seconds; later ones
        are cached.
      </p>
    )
  }

  if (draft.status === 'error') {
    const err = draft.error
    const refused = err instanceof ApiError && err.status === 422
    return (
      <div className={`notice ${styles.notice}`} data-tone="error" role="alert">
        <strong>{refused ? 'The API declined to draft a correction.' : 'Drafting the correction failed.'}</strong>
        <code>{errorText(err)}</code>
        <span className={styles.todo}>
          {refused
            ? ' Nothing was drafted. The conflict can still be resolved or dismissed from this strip.'
            : ' Nothing was drafted. Check that the API is running, then try again.'}
        </span>
        {refused ? null : (
          <button type="button" className={styles.textButton} onClick={onRetry}>
            Try again
          </button>
        )}
      </div>
    )
  }

  const { correction, owner, ticket } = draft.data
  const ticketText = `${ticket.title}\n\n${ticket.body}`
  const ticketBlock = (
    <DraftBlock
      label={focus === 'ticket' ? `Ticket for ${owner.name} · ${owner.role}` : `Ticket for ${owner.name}`}
      copyLabel="Copy ticket"
      copyText={ticketText}
      takeFocus={focus === 'ticket'}
    >
      {focus === 'ticket' ? null : <p className={styles.role}>{owner.role}</p>}
      <p className={styles.ticketTitle}>{ticket.title}</p>
      <p className={styles.generated}>{ticket.body}</p>
    </DraftBlock>
  )

  if (focus === 'ticket') {
    return (
      <div className={styles.draftOne}>
        {ticketBlock}
        <p className={styles.aside}>
          Faultline does not assign work itself: copy this ticket into your tracker for {owner.name}.{' '}
          <button type="button" className={styles.textButton} onClick={onShowCorrection}>
            Show the drafted correction
          </button>
        </p>
      </div>
    )
  }

  return (
    <div className={styles.draftTwo}>
      <DraftBlock label="Drafted correction" copyLabel="Copy correction" copyText={correction} takeFocus>
        <p className={styles.generated}>{correction}</p>
      </DraftBlock>
      {ticketBlock}
    </div>
  )
}

function DraftBlock({
  label,
  copyLabel,
  copyText,
  takeFocus,
  children,
}: {
  label: string
  copyLabel: string
  copyText: string
  takeFocus: boolean
  children: ReactNode
}) {
  const headingRef = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    if (takeFocus) headingRef.current?.focus()
  }, [takeFocus])

  return (
    <section className={styles.block} aria-label={label}>
      <header className={styles.blockHead}>
        <h3 ref={headingRef} tabIndex={-1} className="cap">
          {label}
        </h3>
        <CopyButton label={copyLabel} text={copyText} />
      </header>
      {children}
    </section>
  )
}

function CopyButton({ label, text }: { label: string; text: string }) {
  const [state, setState] = useState<'idle' | 'copied' | 'failed'>('idle')
  useEffect(() => {
    if (state !== 'copied') return
    const t = window.setTimeout(() => setState('idle'), 2000)
    return () => window.clearTimeout(t)
  }, [state])

  const copy = () => {
    if (!navigator.clipboard) {
      setState('failed')
      return
    }
    navigator.clipboard.writeText(text).then(
      () => setState('copied'),
      () => setState('failed'),
    )
  }

  return (
    <span className={styles.copyWrap}>
      {state === 'failed' ? (
        <span className={styles.copyError} role="alert">
          The browser blocked the clipboard. Select the text and copy it by hand.
        </span>
      ) : null}
      <button type="button" className={styles.copy} onClick={copy} aria-live="polite">
        {state === 'copied' ? 'Copied' : label}
      </button>
    </span>
  )
}

// ── Resolve and dismiss ──────────────────────────────────────────────────────

const NAME_KEY = 'faultline.settled_by'

function rememberedName(): string {
  try {
    return window.localStorage.getItem(NAME_KEY) ?? ''
  } catch {
    return ''
  }
}

function rememberName(name: string): void {
  try {
    window.localStorage.setItem(NAME_KEY, name)
  } catch {
    // Storage blocked: the name is asked for again next time.
  }
}

function SettleForm({
  mode,
  conflict,
  onBusy,
  onCancel,
  onDone,
}: {
  mode: 'resolve' | 'dismiss'
  conflict: Conflict
  onBusy: (busy: boolean) => void
  onCancel: () => void
  onDone: (conflict: Conflict) => void
}) {
  const [a, b] = sides(conflict)
  const live = conflict.claims.filter((c) => c.state === 'live')
  const [winner, setWinner] = useState<string>(live.length === 1 ? live[0].id : '')
  const [rationale, setRationale] = useState('')
  const [by, setBy] = useState(rememberedName)
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState<ReactNode>(null)
  const firstRef = useRef<HTMLElement | null>(null)
  const id = useId()
  const resolving = mode === 'resolve'

  useEffect(() => {
    firstRef.current?.focus()
  }, [])

  // A stale "fill in …" line must not sit under fields that are now filled.
  const changed = <T,>(set: (v: T) => void) => (v: T) => {
    set(v)
    setProblem(null)
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const missing = [
      resolving && !winner ? 'which claim is current' : null,
      !rationale.trim() ? (resolving ? 'a rationale' : 'a reason') : null,
      !by.trim() ? (resolving ? 'who resolved it' : 'who dismissed it') : null,
    ].filter(Boolean)
    if (missing.length) {
      const list = missing.length > 1 ? `${missing.slice(0, -1).join(', ')} and ${missing[missing.length - 1]}` : missing[0]
      setProblem(
        <p className={styles.formError} role="alert">
          Nothing was sent. Fill in {list}.
        </p>,
      )
      return
    }
    setBusy(true)
    onBusy(true)
    setProblem(null)
    try {
      const res = resolving
        ? await resolveConflict(conflict.id, {
            winner_claim_id: winner,
            rationale: rationale.trim(),
            resolved_by: by.trim(),
          })
        : await dismissConflict(conflict.id, { rationale: rationale.trim(), dismissed_by: by.trim() })
      rememberName(by.trim())
      onBusy(false)
      onDone(res.conflict)
    } catch (err) {
      setBusy(false)
      onBusy(false)
      setProblem(<SettleError err={err} mode={mode} />)
    }
  }

  const verb = resolving ? 'resolution' : 'dismissal'
  return (
    <form className={styles.form} onSubmit={submit} noValidate aria-label={resolving ? 'Resolve conflict' : 'Dismiss conflict'}>
      {resolving ? (
        <fieldset className={styles.fieldset} disabled={busy}>
          <legend className="cap">Which claim is current</legend>
          <div className={styles.segmented}>
            {[a, b].map((claim) =>
              claim ? (
                <label key={claim.id} className={styles.segment}>
                  <input
                    ref={
                      claim.id === (winner || a?.id || b?.id)
                        ? (el) => {
                            firstRef.current = el
                          }
                        : undefined
                    }
                    type="radio"
                    name={`${id}-winner`}
                    value={claim.id}
                    checked={winner === claim.id}
                    onChange={() => changed(setWinner)(claim.id)}
                  />
                  <span>Claim {claim.side.toUpperCase()}</span>
                  <StateMark state={claim.state} />
                </label>
              ) : null,
            )}
          </div>
          {winner ? (
            <p className={styles.winnerText}>{conflict.claims.find((c) => c.id === winner)?.text}</p>
          ) : (
            <p className={styles.hint}>
              {live.length > 1 ? 'Both claims are marked live' : 'Neither claim is marked live'}, so pick the one
              that stands.
            </p>
          )}
        </fieldset>
      ) : (
        <p className={styles.hint}>
          Dismissing marks this pair as not a real conflict and takes it out of the open queue. The reason, your name
          and the date are recorded with it.
        </p>
      )}

      <div className={styles.fields}>
        <div className={styles.field}>
          <label className="cap" htmlFor={`${id}-rationale`}>
            {resolving ? 'Rationale' : 'Reason'}
          </label>
          <textarea
            ref={
              resolving
                ? undefined
                : (el) => {
                    firstRef.current = el
                  }
            }
            id={`${id}-rationale`}
            className={styles.input}
            rows={2}
            value={rationale}
            disabled={busy}
            required
            placeholder={resolving ? 'Why this claim stands, and where that was decided' : 'Why this is not a real conflict'}
            onChange={(e) => changed(setRationale)(e.target.value)}
          />
        </div>
        <div className={`${styles.field} ${styles.byField}`}>
          <label className="cap" htmlFor={`${id}-by`}>
            {resolving ? 'Resolved by' : 'Dismissed by'}
          </label>
          <input
            id={`${id}-by`}
            className={styles.input}
            value={by}
            disabled={busy}
            required
            autoComplete="name"
            onChange={(e) => changed(setBy)(e.target.value)}
          />
        </div>
      </div>

      <div className={styles.formFoot}>
        <button type="submit" className="btn" disabled={busy} aria-busy={busy}>
          {busy ? 'Recording…' : resolving ? 'Record resolution' : 'Dismiss conflict'}
        </button>
        <button type="button" className={styles.textButton} disabled={busy} onClick={onCancel}>
          Cancel
        </button>
        {busy ? (
          <span className={styles.hint} role="status">
            Sending the {verb} to the API.
          </span>
        ) : null}
      </div>
      {problem}
    </form>
  )
}

function SettleError({ err, mode }: { err: unknown; mode: 'resolve' | 'dismiss' }) {
  const status = err instanceof ApiError ? err.status : null
  const what = mode === 'resolve' ? 'The resolution was not recorded.' : 'The dismissal was not recorded.'
  let todo: ReactNode
  if (status === 409) {
    todo = (
      <>
        {' '}It is no longer open, so someone settled it already.{' '}
        <button type="button" className={styles.textButton} onClick={refreshWorkspaceData}>
          Reload the queue
        </button>
      </>
    )
  } else if (status === 422) {
    todo = ' Correct the field the API names and send it again.'
  } else if (status === 404) {
    todo = ` The conflict is not in workspace ${currentWorkspaceId()}. Reload the queue.`
  } else {
    todo = ' Check that the API is running, then send it again.'
  }
  return (
    <div className={`notice ${styles.notice}`} data-tone="error" role="alert">
      <strong>{what}</strong>
      <code>{errorText(err)}</code>
      <span className={styles.todo}>{todo}</span>
    </div>
  )
}

// ── Status and precedent ─────────────────────────────────────────────────────

function SettledStatus({ conflict }: { conflict: Conflict }) {
  const r = conflict.resolution ?? null
  if (conflict.status === 'resolved') {
    const winner = r ? sides(conflict).find((c) => c?.id === r.winner_claim_id) : undefined
    return (
      <p className={styles.status}>
        <span className="chip" data-status="resolved">
          <Icon name="resolved" size={14} />
          Settled
        </span>
        <span>
          {r ? (
            <>
              {winner ? `Claim ${winner.side.toUpperCase()} stands. ` : null}
              Resolved <span className={styles.mono}>{isoDate(r.resolved_at)}</span> by {r.resolved_by}.
            </>
          ) : (
            'Resolved. The response carries no resolution record.'
          )}
        </span>
      </p>
    )
  }
  return (
    <p className={styles.status}>
      <span className="chip" data-status="dismissed">
        Dismissed
      </span>
      {conflict.dismissal ? (
        <span>
          Dismissed <span className={styles.mono}>{isoDate(conflict.dismissal.dismissed_at)}</span> by{' '}
          {conflict.dismissal.dismissed_by}: {conflict.dismissal.rationale}
        </span>
      ) : (
        <span>Dismissed as not a real conflict. The response carries no dismissal record.</span>
      )}
    </p>
  )
}

const PRECEDENT_CHARS = 56

function PrecedentLine({ precedent, currentId }: { precedent: Precedent | undefined; currentId: string }) {
  if (!precedent) return null
  const newest = precedent.found
    ? precedent.settled.reduce<Precedent['settled'][number] | null>(
        (best, p) => (!best || p.settled_at > best.settled_at ? p : best),
        null,
      )
    : null
  if (!newest) {
    return (
      <p className={styles.precedent} title="Nothing about this conflict's entity has been settled before.">
        precedent: none
      </p>
    )
  }
  const text =
    newest.winner_text.length > PRECEDENT_CHARS
      ? `${newest.winner_text.slice(0, PRECEDENT_CHARS).trimEnd()}…`
      : newest.winner_text
  const label = (
    <>
      precedent: settled {isoDate(newest.settled_at)} · {text}
    </>
  )
  const more = precedent.settled.length > 1 ? ` (newest of ${precedent.settled.length})` : ''
  if (newest.conflict_id === currentId) {
    return (
      <p className={styles.precedent} title={`${newest.winner_text}${more}. Settled by this conflict.`}>
        {label}
      </p>
    )
  }
  const route = { name: 'conflicts', conflictId: newest.conflict_id } as const
  return (
    <a
      className={`${styles.precedent} ${styles.precedentLink}`}
      href={routePath(route)}
      title={`${newest.winner_text}${more}. Open ${newest.conflict_id}.`}
      onClick={(e) => {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return
        e.preventDefault()
        navigate(route)
      }}
    >
      {label}
    </a>
  )
}
