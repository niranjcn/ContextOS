import React, { useState, useEffect } from 'react'
import QueryBox from './components/QueryBox'
import GraphViewer from './components/GraphViewer'
import IngestStatus from './components/IngestStatus'

const API_BASE = 'http://127.0.0.1:8000'

export default function App() {
  const [health, setHealth] = useState(null)

  useEffect(() => {
    fetchHealth()
    const interval = setInterval(fetchHealth, 15000)
    return () => clearInterval(interval)
  }, [])

  async function fetchHealth() {
    try {
      const res = await fetch(`${API_BASE}/health`)
      const data = await res.json()
      setHealth(data)
    } catch {
      setHealth({ status: 'offline', ollama_running: false, models_available: [], vector_count: 0, graph_node_count: 0, uptime_seconds: 0 })
    }
  }

  const statusClass = health?.status === 'healthy' ? 'healthy' : health?.status === 'degraded' ? 'degraded' : 'offline'

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>⚡ ContextOS</h1>
          <p className="tagline">Your private AI memory layer</p>
        </div>
        <div className={`status-badge ${statusClass}`}>
          <span className="status-dot" />
          {health?.status || 'Connecting...'}
        </div>
      </header>

      <div className="grid">
        <div className="card">
          <h3>Ollama</h3>
          <div className="value">{health?.ollama_running ? '✓ Running' : '✗ Offline'}</div>
        </div>
        <div className="card">
          <h3>Vectors</h3>
          <div className="value">{health?.vector_count?.toLocaleString() ?? '—'}</div>
        </div>
        <div className="card">
          <h3>Graph Nodes</h3>
          <div className="value">{health?.graph_node_count?.toLocaleString() ?? '—'}</div>
        </div>
        <div className="card">
          <h3>Models</h3>
          <div className="value">{health?.models_available?.length ?? 0}</div>
        </div>
      </div>

      <QueryBox apiBase={API_BASE} />
      <GraphViewer apiBase={API_BASE} />
      <IngestStatus apiBase={API_BASE} />
    </div>
  )
}
