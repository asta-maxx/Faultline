import type { GraphModel } from '../../lib/graphModel'
import { capitalize, count } from '../../lib/format'
import { STATE_ICON } from '../../lib/icons'
import { Icon } from '../Icon'
import styles from './GraphLegend.module.css'

const STATE_WORD = { live: 'Live', contradicted: 'Contradicted', superseded: 'Superseded' } as const

/** Counts come from the path in the response; nothing is listed that is not in it. */
export function GraphLegend({ model, caption }: { model: GraphModel; caption: string }) {
  return (
    <div className={styles.legend}>
      <ul className={styles.items} aria-label="Node types in this path">
        {model.typeCounts.map((t) => (
          <li key={t.type}>
            <Icon name={t.type} size={14} />
            <span>{capitalize(t.type)}</span>
            <span className="num">{count(t.count)}</span>
          </li>
        ))}
        {model.stateCounts.length ? <li className={styles.divider} aria-hidden="true" /> : null}
        {model.stateCounts.map((s) => (
          <li key={s.state} data-state={s.state}>
            <Icon name={STATE_ICON[s.state]} size={14} />
            <span>{STATE_WORD[s.state]}</span>
            <span className="num">{count(s.count)}</span>
          </li>
        ))}
      </ul>
      <p className={styles.caption}>{caption}</p>
    </div>
  )
}
