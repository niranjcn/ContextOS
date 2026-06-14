import React, { useState, useEffect, useRef } from 'react'
import { api } from '../api'

const ICON_MAP = {
  search: '🔍',
  edit: '✎',
  briefcase: '📋',
  clipboard: '📝',
  upload: '📤',
  mic: '🎤',
  network: '🕸',
  plug: '🔌',
}

function AgentChat({ agent, onBack }) {
  const [input, setInput] = useState('')
  const [conversation, setConversation] = useState([])
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversation])

  async function handleSubmit(e) {
    e.preventDefault()
    const q = input.trim()
    if (!q || loading) return

    setConversation((prev) => [...prev, { role: 'user', content: q }])
    setInput('')
    setLoading(true)

    try {
      if (agent.id === 'query') {
        const res = await api.queryStream(q)
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let text = ''
        setConversation((prev) => [...prev, { role: 'assistant', content: '', streaming: true }])
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          text += decoder.decode(value, { stream: true })
          setConversation((prev) => {
            const copy = [...prev]
            copy[copy.length - 1] = { role: 'assistant', content: text, streaming: true }
            return copy
          })
        }
        setConversation((prev) => {
          const copy = [...prev]
          copy[copy.length - 1] = { role: 'assistant', content: text, streaming: false }
          return copy
        })
      } else if (agent.id === 'draft') {
        const data = await api.queryDraft(q)
        setConversation((prev) => [...prev, { role: 'assistant', content: data.draft, sources: data.context_used }])
      } else if (agent.id === 'brief') {
        const attendees = q.split(',').map((s) => s.trim()).filter(Boolean)
        const data = await api.queryBrief('Meeting', attendees)
        setConversation((prev) => [...prev, { role: 'assistant', content: data.brief, people: data.people_found }])
      } else if (agent.id === 'ingest') {
        const docId = 'dashboard_' + Date.now()
        const data = await api.ingestText(q, docId, 'agents_tab')
        setConversation((prev) => [...prev, {
          role: 'assistant',
          content: `Ingested as document **${data.doc_id}** — ${data.chunks_created} chunks created. Status: ${data.status}`,
        }])
      } else {
        setConversation((prev) => [...prev, { role: 'assistant', content: `Agent "${agent.name}" is not yet connected to the chat interface. Please use its dedicated tab.` }])
      }
    } catch (err) {
      setConversation((prev) => [...prev, { role: 'assistant', content: `Error: ${err.message}`, streaming: false }])
    } finally {
      setLoading(false)
    }
  }

  const placeholderText =
    agent.id === 'query' ? 'Ask a question about your knowledge base...' :
    agent.id === 'draft' ? 'Describe what you want to draft...' :
    agent.id === 'brief' ? 'Enter attendee names (comma-separated)...' :
    agent.id === 'ingest' ? 'Paste text content to ingest...' :
    agent.id === 'graph' ? 'Type a person or topic to search the graph...' :
    'Type your message...'

  return (
    <div className="agent-chat">
      <div className="agent-chat-header">
        <button className="agent-chat-back" onClick={onBack} title="Back to agents list">
          ← Back
        </button>
        <span className="agent-chat-title">{ICON_MAP[agent.icon] || '🤖'} {agent.name}</span>
        <span className={`agent-status-dot ${agent.status}`} />
      </div>

      <div className="agent-chat-body">
        {conversation.length === 0 && (
          <div className="agent-chat-welcome">
            <p>{agent.description}</p>
            {agent.modes?.length > 0 && (
              <div className="agent-modes-hint">
                <strong>Available modes:</strong> {agent.modes.join(', ')}
              </div>
            )}
          </div>
        )}

        {conversation.map((msg, i) => (
          <div key={i} className={`chat-message chat-${msg.role}`}>
            <div className="chat-avatar">
              {msg.role === 'user' ? 'You' : 'AI'}
            </div>
            <div className="chat-bubble">
              <div className={`chat-content ${msg.streaming ? 'chat-streaming' : ''}`}>
                {msg.content}
                {msg.streaming && <span className="chat-cursor">▊</span>}
              </div>
              {msg.sources?.length > 0 && (
                <div className="chat-sources">Sources: {msg.sources.join(', ')}</div>
              )}
              {msg.people?.length > 0 && (
                <div className="chat-sources">People found: {msg.people.join(', ')}</div>
              )}
            </div>
          </div>
        ))}

        <div ref={bottomRef} />
      </div>

      <form className="agent-chat-input-row" onSubmit={handleSubmit}>
        <input
          className="agent-chat-input"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholderText}
          disabled={loading || agent.status !== 'ready'}
        />
        <button className="btn-primary btn-chat-send" type="submit" disabled={loading || !input.trim() || agent.status !== 'ready'}>
          {loading ? <span className="spinner">◌</span> : 'Send'}
        </button>
      </form>
    </div>
  )
}

function AgentCard({ agent, onSelect }) {
  const statusLabel =
    agent.status === 'ready' ? 'Available' :
    agent.status === 'offline' ? 'Offline' : 'Error'

  return (
    <div className={`agent-card agent-${agent.status}`}>
      <div className="agent-card-icon">{ICON_MAP[agent.icon] || '🤖'}</div>
      <div className="agent-card-body">
        <div className="agent-card-header">
          <h3 className="agent-card-name">{agent.name}</h3>
          <span className={`agent-badge badge-${agent.status}`}>{statusLabel}</span>
        </div>
        <p className="agent-card-desc">{agent.description}</p>
        <div className="agent-card-modes">
          {agent.modes.map((m) => (
            <span key={m} className="agent-mode-tag">{m}</span>
          ))}
        </div>
      </div>
      <div className="agent-card-action">
        <button
          className="btn-primary btn-agent-select"
          onClick={() => onSelect(agent)}
          disabled={agent.status !== 'ready'}
        >
          {agent.status === 'ready' ? 'Open Chat' : 'Unavailable'}
        </button>
      </div>
    </div>
  )
}

export default function Agents() {
  const [agents, setAgents] = useState([])
  const [backend, setBackend] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedAgent, setSelectedAgent] = useState(null)
  const [filter, setFilter] = useState('all')

  async function fetchAgents() {
    setLoading(true)
    try {
      const data = await api.getAgents()
      setAgents(data.agents || [])
      setBackend(data.backend || null)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchAgents() }, [])

  if (selectedAgent) {
    return <AgentChat agent={selectedAgent} onBack={() => setSelectedAgent(null)} />
  }

  const filtered = filter === 'all' ? agents : agents.filter((a) => a.status === filter)
  const readyCount = agents.filter((a) => a.status === 'ready').length
  const totalCount = agents.length

  return (
    <div className="panel">
      <div className="agents-header">
        <div>
          <h2 className="section-title">
            <span className="section-icon">🤖</span> AI Agents
          </h2>
          <p className="section-desc">
            Select an agent to interact with. Each agent provides a specific capability
            powered by your local knowledge base and LLM.
          </p>
        </div>
        {backend && (
          <div className="agents-backend-status">
            <div className={`backend-indicator ${backend.ready ? 'ready' : 'offline'}`}>
              <span className="backend-dot" />
              LLM: {backend.ready ? 'Online' : 'Offline'}
            </div>
            {backend.models?.length > 0 && (
              <div className="backend-models">
                {backend.models.slice(0, 2).join(', ')}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="agents-summary">
        <div className="agent-summary-card">
          <span className="agent-summary-value">{totalCount}</span>
          <span className="agent-summary-label">Total Agents</span>
        </div>
        <div className="agent-summary-card">
          <span className="agent-summary-value ready">{readyCount}</span>
          <span className="agent-summary-label">Available</span>
        </div>
        <div className="agent-summary-card">
          <span className="agent-summary-value">{totalCount - readyCount}</span>
          <span className="agent-summary-label">Offline</span>
        </div>
      </div>

      <div className="agents-filter-bar">
        {['all', 'ready', 'offline'].map((f) => (
          <button
            key={f}
            className={`filter-btn ${filter === f ? 'filter-active' : ''}`}
            onClick={() => setFilter(f)}
          >
            {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
            {f === 'all' ? ` (${totalCount})` : f === 'ready' ? ` (${readyCount})` : ` (${totalCount - readyCount})`}
          </button>
        ))}
      </div>

      {error && (
        <div className="error-box">
          <span className="error-icon">⚠</span> {error}
        </div>
      )}

      {loading ? (
        <div className="loading-text"><span className="spinner">◌</span> Loading agents…</div>
      ) : filtered.length === 0 ? (
        <p className="empty-state">No agents match the selected filter.</p>
      ) : (
        <div className="agents-list">
          {filtered.map((agent) => (
            <AgentCard key={agent.id} agent={agent} onSelect={setSelectedAgent} />
          ))}
        </div>
      )}
    </div>
  )
}
