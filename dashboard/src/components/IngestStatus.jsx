import React, { useState, useEffect } from 'react'

export default function IngestStatus({ apiBase }) {
  const [stats, setStats] = useState(null)
  const [text, setText] = useState('')
  const [docId, setDocId] = useState('')
  const [ingesting, setIngesting] = useState(false)
  const [result, setResult] = useState(null)

  useEffect(() => { fetchStats() }, [])

  async function fetchStats() {
    try {
      const res = await fetch(`${apiBase}/ingest/status`)
      if (res.ok) setStats(await res.json())
    } catch { /* API may not be running */ }
  }

  async function handleIngest(e) {
    e.preventDefault()
    if (!text.trim() || !docId.trim()) return

    setIngesting(true)
    setResult(null)
    try {
      const res = await fetch(`${apiBase}/ingest/text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, doc_id: docId, source: 'dashboard' }),
      })
      const data = await res.json()
      setResult(data)
      fetchStats()
      if (res.ok) { setText(''); setDocId('') }
    } catch (err) {
      setResult({ status: 'error', error: err.message })
    } finally {
      setIngesting(false)
    }
  }

  return (
    <div className="ingest-section">
      <h2 className="section-title">📥 Ingest Content</h2>

      {stats && (
        <div style={{ marginBottom: '1rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          Total documents: <strong style={{ color: 'var(--text-primary)' }}>{stats.total}</strong>
          {Object.entries(stats.by_source || {}).map(([src, count]) => (
            <span key={src}> · {src}: {count}</span>
          ))}
        </div>
      )}

      <form onSubmit={handleIngest}>
        <input
          className="query-input"
          style={{ marginBottom: '0.5rem', width: '100%' }}
          type="text"
          value={docId}
          onChange={(e) => setDocId(e.target.value)}
          placeholder="Document ID (e.g., meeting_notes_jan15)"
          disabled={ingesting}
        />
        <textarea
          className="query-input"
          style={{ width: '100%', minHeight: '100px', resize: 'vertical', marginBottom: '0.5rem' }}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste text content to ingest..."
          disabled={ingesting}
        />
        <button className="query-btn" type="submit" disabled={ingesting || !text.trim() || !docId.trim()}>
          {ingesting ? '⏳ Ingesting...' : '📥 Ingest'}
        </button>
      </form>

      {result && (
        <div className="answer-box" style={{ marginTop: '1rem' }}>
          Status: {result.status} | Chunks: {result.chunks_created ?? 0}
        </div>
      )}
    </div>
  )
}
