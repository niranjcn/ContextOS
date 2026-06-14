import React, { useState, useEffect } from 'react'
import { api } from './api'
import QueryBox from './components/QueryBox'
import GraphViewer from './components/GraphViewer'
import IngestStatus from './components/IngestStatus'
import StatusPanel from './components/StatusPanel'
import Connectors from './components/Connectors'
import Agents from './components/Agents'

const TABS = [
  { id: 'agents',    label: 'Agents',     icon: '🤖' },
  { id: 'ask',       label: 'Query',      icon: '💬' },
  { id: 'ingest',    label: 'Ingest',     icon: '📤' },
  { id: 'graph',     label: 'Graph',      icon: '🕸' },
  { id: 'connectors',label: 'Connectors', icon: '🔌' },
  { id: 'status',    label: 'Status',     icon: '📊' },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('agents')
  const [health, setHealth] = useState(null)
  const [agentsCount, setAgentsCount] = useState(null)

  useEffect(() => {
    fetchHealth()
    fetchAgents()
    const interval = setInterval(fetchHealth, 15000)
    return () => clearInterval(interval)
  }, [])

  async function fetchHealth() {
    try {
      const data = await api.getHealth()
      setHealth(data)
    } catch {
      setHealth({
        status: 'offline',
        ollama_running: false,
        models_available: [],
        vector_count: 0,
        graph_node_count: 0,
        uptime_seconds: 0,
      })
    }
  }

  async function fetchAgents() {
    try {
      const data = await api.getAgents()
      setAgentsCount(data.available ?? null)
    } catch {
      /* silent */
    }
  }

  const statusClass =
    health?.status === 'healthy'  ? 'healthy' :
    health?.status === 'degraded' ? 'degraded' : 'offline'

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <h1 className="logo">
            <span className="logo-icon">◆</span> ContextOS
          </h1>
          <p className="tagline">Private AI Memory Layer — Control Panel</p>
        </div>
        <div className="header-right">
          {agentsCount !== null && (
            <div className="header-meta">
              <span className="meta-agents">{agentsCount} agents ready</span>
              <span className="meta-sep">·</span>
            </div>
          )}
          <div className={`status-badge ${statusClass}`}>
            <span className="status-dot" />
            {health?.status || 'Connecting…'}
          </div>
        </div>
      </header>

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-label">LLM Backend</div>
          <div className={`stat-value ${health?.ollama_running ? 'text-success' : 'text-error'}`}>
            {health?.ollama_running ? 'Online' : 'Offline'}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Vector Chunks</div>
          <div className="stat-value">{health?.vector_count?.toLocaleString() ?? '—'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Graph Nodes</div>
          <div className="stat-value">{health?.graph_node_count?.toLocaleString() ?? '—'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">LLM Models</div>
          <div className="stat-value">{health?.models_available?.length ?? 0}</div>
        </div>
      </div>

      <nav className="tab-nav" role="tablist">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            className={`tab-btn ${activeTab === tab.id ? 'tab-active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className="tab-icon">{tab.icon}</span>
            <span className="tab-label">{tab.label}</span>
          </button>
        ))}
      </nav>

      <main className="tab-content">
        {activeTab === 'agents'     && <Agents />}
        {activeTab === 'ask'        && <QueryBox />}
        {activeTab === 'ingest'     && <IngestStatus />}
        {activeTab === 'graph'      && <GraphViewer />}
        {activeTab === 'connectors' && <Connectors />}
        {activeTab === 'status'     && <StatusPanel />}
      </main>
    </div>
  )
}
