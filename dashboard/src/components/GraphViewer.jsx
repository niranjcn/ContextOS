import React, { useState, useEffect } from 'react'

export default function GraphViewer({ apiBase }) {
  const [people, setPeople] = useState([])
  const [docs, setDocs] = useState([])
  const [tab, setTab] = useState('people')

  useEffect(() => {
    fetchPeople()
    fetchDocs()
  }, [])

  async function fetchPeople() {
    try {
      const res = await fetch(`${apiBase}/graph/people`)
      if (res.ok) {
        const data = await res.json()
        setPeople(data.people || [])
      }
    } catch { /* API may not be running */ }
  }

  async function fetchDocs() {
    try {
      const res = await fetch(`${apiBase}/graph/documents?limit=10`)
      if (res.ok) {
        const data = await res.json()
        setDocs(data.documents || [])
      }
    } catch { /* API may not be running */ }
  }

  return (
    <div className="query-section" style={{ marginBottom: '2rem' }}>
      <h2 className="section-title">🕸️ Knowledge Graph</h2>
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        <button
          className="query-btn"
          style={{ padding: '0.5rem 1rem', fontSize: '0.8125rem', opacity: tab === 'people' ? 1 : 0.5 }}
          onClick={() => setTab('people')}
        >
          People ({people.length})
        </button>
        <button
          className="query-btn"
          style={{ padding: '0.5rem 1rem', fontSize: '0.8125rem', opacity: tab === 'docs' ? 1 : 0.5 }}
          onClick={() => setTab('docs')}
        >
          Documents ({docs.length})
        </button>
      </div>

      {tab === 'people' && (
        <div>
          {people.length === 0 ? (
            <p style={{ color: 'var(--text-secondary)' }}>No people in graph yet. Ingest documents to populate.</p>
          ) : (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {people.map((p) => (
                <span key={p} style={{
                  background: 'var(--bg-primary)',
                  padding: '0.375rem 0.75rem',
                  borderRadius: '999px',
                  fontSize: '0.8125rem',
                  border: '1px solid var(--border)',
                }}>{p}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'docs' && (
        <div>
          {docs.length === 0 ? (
            <p style={{ color: 'var(--text-secondary)' }}>No documents indexed yet.</p>
          ) : (
            docs.map((d) => (
              <div key={d.doc_id} className="card" style={{ marginBottom: '0.5rem', padding: '1rem' }}>
                <strong>{d.title}</strong>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  {d.source} · {d.date}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
