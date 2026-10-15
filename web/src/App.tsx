import { useState } from 'react'
import { AppHeader } from './components/layout/AppHeader'
import { ConflictQueue } from './components/queue/ConflictQueue'
import { InvestigationWorkspace } from './components/investigation/InvestigationWorkspace'
import type { Conflict } from './types'
import styles from './App.module.css'

export default function App() {
  const [selectedConflict, setSelectedConflict] = useState<Conflict | null>(null)

  return (
    <div className={styles.app}>
      <AppHeader conflictCount={null} />
      <main className={styles.main}>
        {selectedConflict ? (
          <InvestigationWorkspace
            conflict={selectedConflict}
            onBack={() => setSelectedConflict(null)}
          />
        ) : (
          <ConflictQueue onSelect={setSelectedConflict} />
        )}
      </main>
    </div>
  )
}
