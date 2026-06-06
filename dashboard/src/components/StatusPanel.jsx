import React, { useState, useEffect } from 'react'
import { api } from '../api'

function formatUptime(seconds) {
  if (!seconds || seconds < 0) return '—'
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)
  if (hrs > 0) return `${hrs}h ${mins}m`
  if (mins > 0) return `${mins}m ${secs}s`
  return `${secs}s`
}

export default function StatusPanel() {
  const [health, setHealth] = useState(null)
  const [models, setModels] = useState([])
  const [error, setError] = useState(null)

  async function fetchAll() {
    try {
      const h = await api.getHealth()
      setHealth(h)
      setError(null)
    } catch (err) {
      setError(err.message)
      setHealth(null)
    }
    try {
      const m = await api.getModels()
      setModels(m.models || [])
    } catch { /* silent */ }
  }

  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="status-panel">
      <h2 className="section-title">
        <span className="section-icon">📊</span> System Status
      </h2>

      {error && (
        <div className="status-error">
          <span className="error-icon">⚠</span> {error}
        </div>
      )}

      <div className="status-grid">
        {/* Ollama */}
        <div className="status-card">
          <div className="status-card-header">
            <span className="status-card-label">Ollama</span>
            <span className={`status-indicator ${health?.ollama_running ? 'status-on' : 'status-off'}`}>
              <span className="status-dot-mini" />
              {health?.ollama_running ? 'Running' : 'Offline'}
            </span>
          </div>
          <div className="status-card-value">
            {health?.ollama_running ? '✓' : '✗'}
          </div>
        </div>

        {/* Model */}
        <div className="status-card">
          <div className="status-card-header">
            <span className="status-card-label">Primary Model</span>
          </div>
          <div className="status-card-value status-card-value-sm">
            {models.length > 0 ? models[0] : '—'}
          </div>
        </div>

        {/* Vectors */}
        <div className="status-card">
          <div className="status-card-header">
            <span className="status-card-label">Vector Chunks</span>
          </div>
          <div className="status-card-value">
            {health?.vector_count?.toLocaleString() ?? '—'}
          </div>
        </div>

        {/* Graph */}
        <div className="status-card">
          <div className="status-card-header">
            <span className="status-card-label">Graph Nodes</span>
          </div>
          <div className="status-card-value">
            {health?.graph_node_count?.toLocaleString() ?? '—'}
          </div>
        </div>

        {/* Uptime */}
        <div className="status-card">
          <div className="status-card-header">
            <span className="status-card-label">Uptime</span>
          </div>
          <div className="status-card-value status-card-value-sm">
            {formatUptime(health?.uptime_seconds)}
          </div>
        </div>

        {/* Overall Status */}
        <div className="status-card">
          <div className="status-card-header">
            <span className="status-card-label">System</span>
          </div>
          <div className={`status-card-value ${
            health?.status === 'healthy' ? 'text-success' :
            health?.status === 'degraded' ? 'text-warning' : 'text-error'
          }`}>
            {health?.status || 'unknown'}
          </div>
        </div>
      </div>

      {/* Models list */}
      {models.length > 0 && (
        <div className="models-section">
          <h3 className="models-title">Available Models</h3>
          <div className="models-list">
            {models.map((m) => (
              <span key={m} className="model-badge">{m}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
