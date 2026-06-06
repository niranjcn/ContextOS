import React, { useState, useEffect, useRef } from 'react'
import { api } from '../api'

export default function IngestStatus() {
  const [stats, setStats] = useState(null)
  const [text, setText] = useState('')
  const [docId, setDocId] = useState('')
  const [source, setSource] = useState('manual')
  const [ingesting, setIngesting] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const fileRef = useRef(null)

  useEffect(() => { fetchStats() }, [])

  async function fetchStats() {
    try {
      const data = await api.getIngestStatus()
      setStats(data)
    } catch { /* API may not be running */ }
  }

  async function handleTextIngest(e) {
    e.preventDefault()
    if (!text.trim() || !docId.trim()) return

    setIngesting(true)
    setResult(null)
    setError(null)

    try {
      const data = await api.ingestText(text, docId, source)
      setResult(data)
      setText('')
      setDocId('')
      fetchStats()
    } catch (err) {
      setError(err.message)
    } finally {
      setIngesting(false)
    }
  }

  async function handleFileUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    setUploadResult(null)
    setError(null)

    try {
      const data = await api.uploadFile(file)
      setUploadResult(data)
      fetchStats()
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  return (
    <div className="panel">
      <h2 className="section-title">
        <span className="section-icon">📥</span> Ingest Content
      </h2>

      {/* Stats bar */}
      {stats && (
        <div className="ingest-stats">
          <span className="ingest-stat-total">
            <strong>{stats.total}</strong> documents indexed
          </span>
          {Object.entries(stats.by_source || {}).map(([src, count]) => (
            <span key={src} className="ingest-stat-source">
              {src}: {count}
            </span>
          ))}
        </div>
      )}

      {/* File Upload */}
      <div className="ingest-section-block">
        <h3 className="subsection-title">Upload File</h3>
        <div className="file-upload-wrapper">
          <input
            id="file-upload"
            ref={fileRef}
            type="file"
            accept=".txt,.md,.pdf,.docx"
            onChange={handleFileUpload}
            disabled={uploading}
            className="file-input"
          />
          <label htmlFor="file-upload" className={`file-label ${uploading ? 'disabled' : ''}`}>
            {uploading ? (
              <><span className="spinner">◌</span> Uploading…</>
            ) : (
              <>📁 Choose file (.txt, .md, .pdf, .docx)</>
            )}
          </label>
        </div>
        {uploadResult && (
          <div className="result-box result-success">
            ✓ Ingested <strong>{uploadResult.chunks_created}</strong> chunks
            {' · '}Status: {uploadResult.status}
          </div>
        )}
      </div>

      {/* Text Ingest */}
      <div className="ingest-section-block">
        <h3 className="subsection-title">Paste Text</h3>
        <form onSubmit={handleTextIngest}>
          <div className="ingest-fields">
            <input
              id="ingest-doc-id"
              className="query-input"
              type="text"
              value={docId}
              onChange={(e) => setDocId(e.target.value)}
              placeholder="Document ID (e.g., meeting_notes_jan15)"
              disabled={ingesting}
            />
            <input
              id="ingest-source"
              className="query-input"
              type="text"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="Source name"
              disabled={ingesting}
            />
          </div>
          <textarea
            id="ingest-text"
            className="query-input ingest-textarea"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste text content to ingest…"
            disabled={ingesting}
          />
          <button
            id="ingest-submit"
            className="btn-primary"
            type="submit"
            disabled={ingesting || !text.trim() || !docId.trim()}
          >
            {ingesting ? (
              <><span className="spinner">◌</span> Ingesting…</>
            ) : (
              '📥 Ingest Text'
            )}
          </button>
        </form>

        {result && (
          <div className="result-box result-success">
            ✓ Ingested <strong>{result.chunks_created}</strong> chunks
            {result.entities?.people?.length > 0 && (
              <>, found {result.entities.people.length} people</>
            )}
            {result.entities?.organizations?.length > 0 && (
              <>, {result.entities.organizations.length} orgs</>
            )}
            {' · '}Status: {result.status}
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="error-box">
          <span className="error-icon">⚠</span> {error}
        </div>
      )}
    </div>
  )
}
