import React, { useState, useEffect } from 'react'
import { api } from '../api'

function SetupGuide({ connector, onClose }) {
  const [guide, setGuide] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getConnectorGuide(connector)
      .then(setGuide)
      .catch(() => setGuide(null))
      .finally(() => setLoading(false))
  }, [connector])

  if (loading) return <div className="loading-text"><span className="spinner">◌</span> Loading guide…</div>
  if (!guide) return <div className="error-box">⚠ Guide not available</div>

  return (
    <div className="setup-guide-overlay" onClick={onClose}>
      <div className="setup-guide-panel" onClick={(e) => e.stopPropagation()}>
        <div className="setup-guide-header">
          <h2>Setup Guide: {connector}</h2>
          <button className="setup-guide-close" onClick={onClose}>&times;</button>
        </div>
        <div className="setup-guide-body">
          {guide.steps.map((s) => (
            <div key={s.step} className="guide-step">
              <div className="guide-step-number">{s.step}</div>
              <div className="guide-step-content">
                <h4>{s.title}</h4>
                <p>{s.description}</p>
                {s.link && (
                  <a href={s.link} target="_blank" rel="noopener noreferrer" className="guide-link">
                    Open in browser &rarr;
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function ConnectorCard({ connector, onRefresh }) {
  const [expanded, setExpanded] = useState(false)
  const [showGuide, setShowGuide] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState(null)
  const [credFile, setCredFile] = useState(null)
  const [configuring, setConfiguring] = useState(false)
  const [historyPath, setHistoryPath] = useState('')
  const [watchDirs, setWatchDirs] = useState('')

  async function handleToggle() {
    await api.configureConnector(connector.id, { enabled: !connector.enabled })
    onRefresh()
  }

  async function handleSync() {
    setSyncing(true)
    setSyncResult(null)
    try {
      const result = await api.syncConnector(connector.id)
      setSyncResult(result)
    } catch (err) {
      setSyncResult({ status: 'error', message: err.message })
    } finally {
      setSyncing(false)
    }
  }

  async function handleCredUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setConfiguring(true)
    try {
      const text = await file.text()
      await api.configureConnector(connector.id, { credentials_json: text })
      onRefresh()
      setCredFile(file.name)
    } catch (err) {
      alert('Failed to save credentials: ' + err.message)
    } finally {
      setConfiguring(false)
    }
  }

  async function handleSaveSettings() {
    setConfiguring(true)
    try {
      const settings = {}
      if (connector.id === 'browser_history' && historyPath) {
        settings.history_path = historyPath
      }
      if (connector.id === 'local_files' && watchDirs) {
        settings.watch_dirs = watchDirs.split(',').map((s) => s.trim()).filter(Boolean)
      }
      await api.configureConnector(connector.id, { settings, configured: true, enabled: true })
      onRefresh()
    } catch (err) {
      alert('Failed to save settings: ' + err.message)
    } finally {
      setConfiguring(false)
    }
  }

  const needsGuide = connector.needs_credentials || connector.id === 'browser_history' || connector.id === 'local_files'

  return (
    <div className={`connector-card ${connector.enabled ? 'connector-enabled' : ''}`}>
      <div className="connector-card-header" onClick={() => setExpanded(!expanded)}>
        <div className="connector-card-main">
          <span className="connector-icon">{connector.icon}</span>
          <div>
            <div className="connector-name">{connector.name}</div>
            <div className="connector-desc">{connector.description}</div>
          </div>
        </div>
        <div className="connector-card-status">
          {connector.configured ? (
            <span className="connector-badge badge-configured">Configured</span>
          ) : (
            <span className="connector-badge badge-not-configured">Not setup</span>
          )}
          <label className="toggle-switch" onClick={(e) => e.stopPropagation()}>
            <input type="checkbox" checked={connector.enabled} onChange={handleToggle} />
            <span className="toggle-slider"></span>
          </label>
        </div>
      </div>

      {expanded && (
        <div className="connector-card-body">
          {needsGuide && (
            <button className="btn-guide" onClick={() => setShowGuide(true)}>
              📖 Show setup guide
            </button>
          )}

          {connector.needs_credentials && (
            <div className="connector-section">
              <label className="connector-section-label">OAuth Credentials File</label>
              {connector.configured ? (
                <div className="connector-configured-info">
                  ✓ Credentials saved ({credFile || 'uploaded'})
                </div>
              ) : (
                <div className="connector-cred-upload">
                  <input
                    type="file"
                    id={`cred-${connector.id}`}
                    accept=".json"
                    onChange={handleCredUpload}
                    className="file-input"
                  />
                  <label htmlFor={`cred-${connector.id}`} className="file-label-sm">
                    {configuring ? 'Saving…' : '📎 Upload credentials.json'}
                  </label>
                </div>
              )}
            </div>
          )}

          {connector.id === 'browser_history' && (
            <div className="connector-section">
              <label className="connector-section-label">History File Path</label>
              <input
                className="query-input"
                type="text"
                value={historyPath}
                onChange={(e) => setHistoryPath(e.target.value)}
                placeholder="e.g. C:\Users\You\AppData\Local\Google\Chrome\User Data\Default\History"
              />
              <button className="btn-primary btn-sm" onClick={handleSaveSettings} disabled={configuring || !historyPath}>
                Save Path & Enable
              </button>
            </div>
          )}

          {connector.id === 'local_files' && (
            <div className="connector-section">
              <label className="connector-section-label">Watch Directories (comma-separated)</label>
              <input
                className="query-input"
                type="text"
                value={watchDirs}
                onChange={(e) => setWatchDirs(e.target.value)}
                placeholder="e.g. C:\Users\You\Documents, D:\Reports"
              />
              <button className="btn-primary btn-sm" onClick={handleSaveSettings} disabled={configuring || !watchDirs}>
                Save & Enable
              </button>
            </div>
          )}

          <div className="connector-actions">
            <button
              className="btn-primary btn-sm"
              onClick={handleSync}
              disabled={syncing || !connector.enabled}
            >
              {syncing ? <><span className="spinner">◌</span> Syncing…</> : '🔄 Sync Now'}
            </button>
          </div>

          {syncResult && (
            <div className={`sync-result ${syncResult.status === 'completed' ? 'sync-ok' : 'sync-err'}`}>
              {syncResult.status === 'completed' ? '✓' : '✗'} {syncResult.message}
            </div>
          )}
        </div>
      )}

      {showGuide && <SetupGuide connector={connector.id} onClose={() => setShowGuide(false)} />}
    </div>
  )
}

export default function Connectors() {
  const [connectors, setConnectors] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  async function fetchConnectors() {
    setLoading(true)
    try {
      const data = await api.getConnectors()
      setConnectors(data.connectors || [])
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchConnectors() }, [])

  return (
    <div className="panel">
      <div className="connectors-header">
        <h2 className="section-title">
          <span className="section-icon">🔌</span> Connectors
        </h2>
        <p className="section-desc">
          Connect your data sources. Each connector needs to be configured and enabled before it can sync.
        </p>
      </div>

      {error && (
        <div className="error-box">
          <span className="error-icon">⚠</span> {error}
        </div>
      )}

      {loading ? (
        <div className="loading-text"><span className="spinner">◌</span> Loading connectors…</div>
      ) : (
        <div className="connectors-list">
          {connectors.map((c) => (
            <ConnectorCard key={c.id} connector={c} onRefresh={fetchConnectors} />
          ))}
        </div>
      )}
    </div>
  )
}
