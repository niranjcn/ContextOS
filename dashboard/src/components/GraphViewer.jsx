import React, { useState, useEffect } from 'react'
import { api } from '../api'

export default function GraphViewer() {
  const [people, setPeople] = useState([])
  const [docs, setDocs] = useState([])
  const [stats, setStats] = useState(null)
  const [selectedPerson, setSelectedPerson] = useState(null)
  const [personDocs, setPersonDocs] = useState([])
  const [loadingDocs, setLoadingDocs] = useState(false)
  const [tab, setTab] = useState('people')

  useEffect(() => {
    fetchPeople()
    fetchDocs()
    fetchStats()
  }, [])

  async function fetchPeople() {
    try {
      const data = await api.getPeople()
      setPeople(data.people || [])
    } catch { /* API may not be running */ }
  }

  async function fetchDocs() {
    try {
      const data = await api.getDocuments(10)
      setDocs(data.documents || [])
    } catch { /* API may not be running */ }
  }

  async function fetchStats() {
    try {
      const data = await api.getStats()
      setStats(data.stats || {})
    } catch { /* silent */ }
  }

  async function handlePersonClick(name) {
    if (selectedPerson === name) {
      setSelectedPerson(null)
      setPersonDocs([])
      return
    }
    setSelectedPerson(name)
    setLoadingDocs(true)
    try {
      const data = await api.getPersonDocs(name)
      setPersonDocs(data.documents || [])
    } catch {
      setPersonDocs([])
    } finally {
      setLoadingDocs(false)
    }
  }

  const totalPeople = stats?.Person_count ?? people.length
  const totalDocs = stats?.Document_count ?? docs.length

  return (
    <div className="panel">
      <h2 className="section-title">
        <span className="section-icon">🕸️</span> Knowledge Graph
      </h2>

      {/* Stats badges */}
      <div className="graph-stats-bar">
        <span className="graph-badge">{totalPeople} people</span>
        <span className="graph-badge">{totalDocs} documents</span>
        {stats?.Organization_count != null && (
          <span className="graph-badge">{stats.Organization_count} orgs</span>
        )}
        {stats?.Topic_count != null && (
          <span className="graph-badge">{stats.Topic_count} topics</span>
        )}
      </div>

      {/* Sub-tabs */}
      <div className="sub-tabs">
        <button
          className={`sub-tab ${tab === 'people' ? 'sub-tab-active' : ''}`}
          onClick={() => setTab('people')}
        >
          People ({people.length})
        </button>
        <button
          className={`sub-tab ${tab === 'docs' ? 'sub-tab-active' : ''}`}
          onClick={() => setTab('docs')}
        >
          Documents ({docs.length})
        </button>
      </div>

      {/* People tab */}
      {tab === 'people' && (
        <div>
          {people.length === 0 ? (
            <p className="empty-state">No people in graph yet. Ingest documents to populate.</p>
          ) : (
            <div className="person-grid">
              {people.map((p) => (
                <button
                  key={p}
                  className={`person-card ${selectedPerson === p ? 'person-card-active' : ''}`}
                  onClick={() => handlePersonClick(p)}
                >
                  <span className="person-avatar">{p.charAt(0)}</span>
                  <span className="person-name">{p}</span>
                </button>
              ))}
            </div>
          )}

          {/* Selected person's documents */}
          {selectedPerson && (
            <div className="person-docs">
              <h3 className="person-docs-title">
                Documents mentioning <strong>{selectedPerson}</strong>
              </h3>
              {loadingDocs ? (
                <p className="loading-text"><span className="spinner">◌</span> Loading…</p>
              ) : personDocs.length === 0 ? (
                <p className="empty-state">No documents found.</p>
              ) : (
                personDocs.map((d) => (
                  <div key={d.doc_id} className="doc-row">
                    <span className="doc-title">{d.title || d.doc_id}</span>
                    <span className="doc-meta">{d.source} · {d.date}</span>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}

      {/* Documents tab */}
      {tab === 'docs' && (
        <div>
          {docs.length === 0 ? (
            <p className="empty-state">No documents indexed yet.</p>
          ) : (
            docs.map((d) => (
              <div key={d.doc_id} className="doc-row">
                <span className="doc-title">{d.title || d.doc_id}</span>
                <span className="doc-meta">{d.source} · {d.date}</span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
