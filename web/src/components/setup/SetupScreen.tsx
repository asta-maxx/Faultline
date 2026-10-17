import { useState, type FormEvent } from 'react'
import type { Source, SourceKind } from '../../types'
import {
  ApiError,
  addSource,
  createWorkspace,
  errorText,
  listSources,
  listWorkspaces,
  refreshWorkspaceData,
  removeSource,
  setWorkspace,
  startAudit,
  useWorkspace,
} from '../../lib/api'
import { navigate } from '../../lib/router'
import { useAsync } from '../../lib/useAsync'
import { plural } from '../../lib/format'
import { Icon } from '../Icon'
import { SourceStatusMark } from '../sources/SourceStatusMark'
import styles from './SetupScreen.module.css'

const TOKEN_USED = 'Cloned with a token. The token was not stored.'

/** A failed add: the server's own words, and which kind of source it was for. */
type SourceError = { kind: SourceKind; status: number | null; detail: string }

/**
 * Connect sources. With no workspace (reached from NEW WORKSPACE) the column
 * starts with a name field and the workspace is created when the first
 * source is added; the screen then moves to /setup?workspace=<id> and the
 * app switches to it.
 */
export function SetupScreen({ workspaceId }: { workspaceId: string | null }) {
  const ws = useWorkspace()
  const [name, setName] = useState('')
  const [kind, setKind] = useState<SourceKind>('git')
  const [location, setLocation] = useState('')
  const [token, setToken] = useState('')
  const [busy, setBusy] = useState(false)
  const [nameError, setNameError] = useState<string | null>(null)
  const [sourceError, setSourceError] = useState<SourceError | null>(null)
  const [auditError, setAuditError] = useState<string | null>(null)
  const [last, setLast] = useState<{ workspace: string; source: Source } | null>(null)
  const [removeErrors, setRemoveErrors] = useState<Record<string, string>>({})

  // NEW WORKSPACE while already on /setup?workspace=<id>: start the form over.
  const [prevWorkspace, setPrevWorkspace] = useState(workspaceId)
  if (prevWorkspace !== workspaceId) {
    setPrevWorkspace(workspaceId)
    if (workspaceId === null) {
      setName('')
      setLocation('')
      setToken('')
      setNameError(null)
      setSourceError(null)
      setAuditError(null)
      setLast(null)
    }
  }

  const sources = useAsync(
    () => (workspaceId ? listSources(workspaceId) : Promise.resolve<Source[]>([])),
    `sources:${workspaceId ?? ''}:${ws.key}`,
  )
  const workspaces = useAsync(listWorkspaces, `setup-workspaces:${workspaceId ?? ''}:${ws.key}`)
  const workspace =
    workspaceId && workspaces.status === 'ready' ? (workspaces.data.find((w) => w.id === workspaceId) ?? null) : null

  const list = sources.status === 'ready' ? sources.data : []
  const canAdd = !busy && location.trim() !== '' && (workspaceId !== null || name.trim() !== '')

  const onAdd = async (e: FormEvent) => {
    e.preventDefault()
    if (!canAdd) return
    setBusy(true)
    setSourceError(null)
    setNameError(null)
    let id = workspaceId
    if (!id) {
      try {
        const created = await createWorkspace(name.trim())
        id = created.id
        setWorkspace(created.id)
        navigate({ name: 'setup', workspace: created.id }, true)
      } catch (err) {
        setNameError(errorText(err))
        setBusy(false)
        return
      }
    }
    try {
      const body = kind === 'git' && token ? { kind, location: location.trim(), token } : { kind, location: location.trim() }
      const source = await addSource(id, body)
      setLast({ workspace: id, source })
      setLocation('')
      setToken('')
      refreshWorkspaceData()
    } catch (err) {
      setSourceError(
        err instanceof ApiError
          ? { kind, status: err.status, detail: err.detail }
          : { kind, status: null, detail: errorText(err) },
      )
    }
    setBusy(false)
  }

  const onRemove = async (sourceId: string) => {
    if (!workspaceId) return
    try {
      await removeSource(workspaceId, sourceId)
      setRemoveErrors((r) => {
        const rest = { ...r }
        delete rest[sourceId]
        return rest
      })
      if (last?.source.id === sourceId) setLast(null)
      refreshWorkspaceData()
    } catch (err) {
      setRemoveErrors((r) => ({ ...r, [sourceId]: errorText(err) }))
    }
  }

  const onAudit = async () => {
    if (!workspaceId) return
    setAuditError(null)
    setBusy(true)
    try {
      const { run_id } = await startAudit(workspaceId)
      navigate({ name: 'audit', runId: run_id })
    } catch (err) {
      setAuditError(errorText(err))
      setBusy(false)
    }
  }

  const lastHere = last && last.workspace === workspaceId ? last.source : null

  return (
    <div className={styles.screen}>
      <div className={styles.column}>
        {workspaceId ? (
          <p className={styles.workspace}>
            <span className="cap">Workspace</span>
            <span className={styles.workspaceName}>{workspace?.name ?? workspaceId}</span>
            <span className={styles.workspaceGraph}>{workspace?.graph ?? ''}</span>
          </p>
        ) : null}

        <header className={styles.intro}>
          <h1 className="display">What should Faultline read?</h1>
          <p className={styles.lede}>
            Point it at your documentation. It reads everything once and finds where it disagrees with itself.
          </p>
        </header>

        <form className={styles.form} onSubmit={onAdd}>
          {workspaceId === null ? (
            <div className={styles.field}>
              <label className="label" htmlFor="setup-name">
                Workspace name
              </label>
              <input
                id="setup-name"
                className={styles.input}
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="off"
                spellCheck={false}
                aria-describedby="setup-name-note"
              />
              {nameError ? (
                <p id="setup-name-note" className={styles.error} role="alert">
                  {nameError}
                </p>
              ) : (
                <p id="setup-name-note" className={styles.hint}>
                  The workspace is created when you add its first source.
                </p>
              )}
            </div>
          ) : null}

          <div className={styles.field}>
            <span className="label" id="setup-kind">
              Source
            </span>
            <div className={styles.segmented} role="radiogroup" aria-labelledby="setup-kind">
              {(['git', 'folder'] as const).map((k) => (
                <button
                  key={k}
                  type="button"
                  role="radio"
                  aria-checked={kind === k}
                  className={styles.segment}
                  onClick={() => {
                    setKind(k)
                    setSourceError(null)
                  }}
                >
                  {k === 'folder' ? 'Folder' : 'Git repository'}
                </button>
              ))}
            </div>
          </div>

          <div className={styles.field}>
            <label className="label" htmlFor="setup-location">
              {kind === 'folder' ? 'Folder path on the API machine' : 'Repository URL'}
            </label>
            <input
              id="setup-location"
              className={`${styles.input} ${styles.mono}`}
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              autoComplete="off"
              spellCheck={false}
              placeholder={kind === 'git' ? 'https://github.com/owner/repo' : undefined}
            />
          </div>

          {kind === 'git' ? (
            <>
              <div className={styles.field}>
                <label className="label" htmlFor="setup-token">
                  Access token <span className={styles.optional}>optional</span>
                </label>
                <input
                  id="setup-token"
                  type="password"
                  className={`${styles.input} ${styles.mono}`}
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  autoComplete="off"
                  spellCheck={false}
                />
              </div>
              <p className={styles.hint}>
                Faultline clones the repository (latest commit only) and reads its .md, .markdown and .txt files.
                Nothing in it is run. A token is used for this one clone and never stored, so a private repository
                needs it again to be read again.
              </p>
            </>
          ) : (
            <p className={styles.caveat}>
              Folder sources read a folder on the computer running Faultline's API. That works when you run
              Faultline yourself. On the hosted demo the server cannot see your computer, so use a Git repository.
            </p>
          )}

          <div className={styles.addRow}>
            <button type="submit" className="btn btn-primary" disabled={!canAdd}>
              {busy && kind === 'git' ? 'Cloning…' : 'Add source'}
            </button>
            <div className={styles.addResult} aria-live="polite">
              {busy && kind === 'git' ? (
                <p className={styles.hint}>Cloning the repository. Large repositories can take a minute.</p>
              ) : sourceError ? (
                <AddError error={sourceError} />
              ) : lastHere ? (
                <AddResult source={lastHere} />
              ) : null}
            </div>
          </div>
        </form>

        <section className={styles.sources} aria-label="Sources">
          <h2 className="cap">
            {workspaceId && sources.status === 'ready' ? plural(list.length, 'source') : 'Sources'}
          </h2>
          {sources.status === 'error' ? (
            <p className={styles.error}>The source list did not load. {sources.error}</p>
          ) : list.length === 0 ? (
            <p className={styles.empty}>No sources yet.</p>
          ) : (
            <ul className={styles.rows}>
              {list.map((s) => (
                <li key={s.id} className={styles.row}>
                  <span className="chip">{s.kind}</span>
                  <div className={styles.rowMain}>
                    <p className={styles.location} title={s.location}>
                      {s.location}
                    </p>
                    {s.message ? <p className={styles.message}>{s.message}</p> : null}
                    {s.has_token && !s.message && s.status === 'ready' ? <p className={styles.message}>{TOKEN_USED}</p> : null}
                    {removeErrors[s.id] ? <p className={styles.error}>{removeErrors[s.id]}</p> : null}
                  </div>
                  <span className={styles.docs}>{s.docs === null ? 'not scanned' : plural(s.docs, 'document')}</span>
                  <SourceStatusMark status={s.status} />
                  <button
                    type="button"
                    className={styles.remove}
                    onClick={() => void onRemove(s.id)}
                    aria-label={`Remove ${s.location}`}
                  >
                    <Icon name="close" size={14} />
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <footer className={styles.footer}>
          <button
            type="button"
            className="btn btn-primary"
            disabled={busy || !workspaceId || list.length === 0}
            onClick={() => void onAudit()}
          >
            {workspace?.last_audit ? 'Run audit' : 'Run first audit'}
          </button>
          {auditError ? (
            <p className={styles.error} role="alert">
              {auditError}
            </p>
          ) : list.length === 0 ? (
            <p className={styles.hint}>Add at least one source to run an audit.</p>
          ) : null}
        </footer>
      </div>
    </div>
  )
}

/** What the API said about the source just added. Success only when it was found and scanned. */
function AddResult({ source: s }: { source: Source }) {
  if (s.status === 'ready') {
    return (
      <div className={styles.added}>
        <p className={styles.addedRow}>
          <span className={styles.docs}>{s.docs === null ? 'not scanned' : plural(s.docs, 'document')}</span>
          <span className="dot" />
          <SourceStatusMark status={s.status} />
        </p>
        <p className={styles.addedLocation}>{s.location}</p>
        {s.message ? <p className={styles.message}>{s.message}</p> : null}
        {s.has_token && !s.message ? <p className={styles.message}>{TOKEN_USED}</p> : null}
      </div>
    )
  }
  return (
    <div className={styles.notRead}>
      <SourceStatusMark status={s.status} />
      {s.message ? <p>{s.message}</p> : null}
    </div>
  )
}

/** The server's message as it came, then what to do about it. No source was created. */
function AddError({ error: e }: { error: SourceError }) {
  return (
    <div role="alert" className={styles.failed}>
      <p className={styles.error}>
        {e.status !== null ? `${e.status} · ` : ''}
        {e.detail}
      </p>
      {e.kind === 'git' && e.status === 422 ? (
        <p className={styles.hint}>
          Nothing was added. Check the URL, add a token for a private repository, or use a smaller repository.
        </p>
      ) : null}
    </div>
  )
}
