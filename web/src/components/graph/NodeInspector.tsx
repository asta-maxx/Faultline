import { involvedSystems, relationships, type GraphModel, type ModelNode } from '../../lib/graphModel'
import { confidence, count, isoDate } from '../../lib/format'
import { Icon, StateMark } from '../Icon'
import styles from './NodeInspector.module.css'

interface Props {
  model: GraphModel
  node: ModelNode
  onSelect: (id: string) => void
  onClose: () => void
}

/** The §5 date property each dated label carries, named for what it means. */
const DATE_WORD: Partial<Record<ModelNode['type'], string>> = {
  document: 'Updated',
  decision: 'Decided',
  message: 'Sent',
  ticket: 'Closed',
}

/** Everything shown here is read from the path and the conflict; absent data is not shown. */
export function NodeInspector({ model, node, onSelect, onClose }: Props) {
  const groups = relationships(model, node.id)
  const systems = node.type === 'system' ? [] : involvedSystems(model, node.id)
  const claim = node.claim

  return (
    <aside className={styles.panel} aria-label={`${node.heading} details`}>
      <header className={styles.head} data-state={node.state ?? 'none'}>
        <div className={styles.headLine}>
          <span className="cap">{node.heading}</span>
          <span className={styles.id} title={node.id}>
            #{node.id}
          </span>
          <button type="button" className={styles.close} onClick={onClose} aria-label="Close inspector">
            <Icon name="close" size={16} />
          </button>
        </div>
        {node.state ? <StateMark state={node.state} /> : null}
        <h2 className={styles.title}>{claim ? claim.text : node.label}</h2>
      </header>

      {claim ? (
        <section className={styles.section}>
          <h3 className="cap">Source</h3>
          <button type="button" className={styles.item} onClick={() => onSelect(claim.source.doc_id)}>
            <Icon name="document" size={20} />
            <span className={styles.itemMain}>
              <span className={styles.itemTitle}>{claim.source.title}</span>
              <span className={styles.itemSub}>{claim.source.path}</span>
            </span>
            <span className={styles.itemDate}>{isoDate(claim.source.updated_at)}</span>
          </button>
          <dl className={styles.facts}>
            <div>
              <dt className="cap">Confidence</dt>
              <dd className="num">{confidence(claim.confidence)}</dd>
            </div>
            <div>
              <dt className="cap">Evidence span</dt>
              <dd>{claim.evidence_span}</dd>
            </div>
          </dl>
        </section>
      ) : node.date !== null ? (
        <section className={styles.section}>
          <h3 className="cap">{DATE_WORD[node.type] ?? 'Dated'}</h3>
          <p className="num">{isoDate(node.date)}</p>
        </section>
      ) : null}

      {groups.map((g) => (
        <section key={`${g.edge}:${g.direction}`} className={styles.section}>
          <h3 className="cap">
            {g.direction === 'in' ? `← ${g.edge}` : `${g.edge} →`}
            <span className={styles.groupCount}>{count(g.nodes.length)}</span>
          </h3>
          <ul>
            {g.nodes.map((n) => (
              <li key={n.id}>
                <button type="button" className={styles.item} data-state={n.state ?? 'none'} onClick={() => onSelect(n.id)}>
                  <Icon name={n.type} size={20} />
                  <span className={styles.itemMain}>
                    <span className={styles.itemTitle}>{n.claim ? n.claim.text : n.label}</span>
                    <span className={styles.itemSub}>
                      {n.heading} #{n.id}
                    </span>
                  </span>
                  {n.date !== null ? <span className={styles.itemDate}>{isoDate(n.date)}</span> : null}
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}

      {node.type !== 'system' ? (
        <section className={styles.section}>
          <h3 className="cap">
            Involved systems
            <span className={styles.groupCount}>{count(systems.length)}</span>
          </h3>
          {systems.length ? (
            <ul>
              {systems.map((s) => (
                <li key={s.id}>
                  <button type="button" className={styles.item} onClick={() => onSelect(s.id)}>
                    <Icon name="system" size={20} />
                    <span className={styles.itemMain}>
                      <span className={styles.itemTitle}>{s.label}</span>
                      <span className={styles.itemSub}>#{s.id}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className={styles.none}>No GOVERNS edge in this path reaches a system from here.</p>
          )}
        </section>
      ) : null}
    </aside>
  )
}
