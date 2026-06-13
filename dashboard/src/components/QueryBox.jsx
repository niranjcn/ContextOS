import React, { useState, useRef, useEffect } from 'react'
import { api } from '../api'

export default function QueryBox() {
  const [history, setHistory] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState('ask')
  const [draftResult, setDraftResult] = useState(null)
  const [briefResult, setBriefResult] = useState(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history, draftResult, briefResult])

  async function handleSubmit(e) {
    e.preventDefault()
    const q = input.trim()
    if (!q || loading) return

    if (mode === 'ask') {
      setHistory((prev) => [...prev, { role: 'user', content: q }])
      setInput('')
      setLoading(true)

      try {
        const res = await api.queryStream(q)
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let text = ''

        setHistory((prev) => [...prev, { role: 'assistant', content: '', streaming: true }])

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          text += decoder.decode(value, { stream: true })
          setHistory((prev) => {
            const copy = [...prev]
            copy[copy.length - 1] = { role: 'assistant', content: text, streaming: true }
            return copy
          })
        }

        setHistory((prev) => {
          const copy = [...prev]
          copy[copy.length - 1] = { role: 'assistant', content: text, streaming: false }
          return copy
        })
      } catch (err) {
        setHistory((prev) => [
          ...prev,
          { role: 'assistant', content: `Error: ${err.message}`, streaming: false },
        ])
      } finally {
        setLoading(false)
      }
    } else if (mode === 'draft') {
      setLoading(true)
      setDraftResult(null)
      try {
        const data = await api.queryDraft(q)
        setDraftResult(data)
      } catch (err) {
        setDraftResult({ draft: `Error: ${err.message}`, context_used: [] })
      } finally {
        setLoading(false)
      }
    } else if (mode === 'brief') {
      setLoading(true)
      setBriefResult(null)
      try {
        const attendees = q.split(',').map((s) => s.trim()).filter(Boolean)
        const data = await api.queryBrief('Meeting', attendees)
        setBriefResult(data)
      } catch (err) {
        setBriefResult({ brief: `Error: ${err.message}`, people_found: [] })
      } finally {
        setLoading(false)
      }
    }
  }

  function clearHistory() {
    setHistory([])
    setDraftResult(null)
    setBriefResult(null)
  }

  const placeholder =
    mode === 'ask' ? 'Ask anything about your documents...' :
    mode === 'draft' ? 'Describe what you want to draft...' :
    'Enter attendee names (comma-separated)...'

  return (
    <div className="panel terminal-panel">
      <div className="terminal-header">
        <div className="terminal-tabs">
          <button className={`terminal-tab ${mode === 'ask' ? 'terminal-tab-active' : ''}`} onClick={() => setMode('ask')}>
            ❯ Query
          </button>
          <button className={`terminal-tab ${mode === 'draft' ? 'terminal-tab-active' : ''}`} onClick={() => setMode('draft')}>
            ✎ Draft
          </button>
          <button className={`terminal-tab ${mode === 'brief' ? 'terminal-tab-active' : ''}`} onClick={() => setMode('brief')}>
            📋 Brief
          </button>
        </div>
        <button className="terminal-clear" onClick={clearHistory} title="Clear history">Clear</button>
      </div>

      <div className="terminal-body">
        {mode === 'ask' && history.length === 0 && (
          <div className="terminal-welcome">
            <div className="terminal-prompt-line">
              <span className="terminal-prompt">contextos ❯</span> Ask anything about your knowledge base
            </div>
            <div className="terminal-hints">
              <span>"What did Alice decide about the API?"</span>
              <span>"Summarize Q3 planning document"</span>
              <span>"Who is working on project X?"</span>
            </div>
          </div>
        )}

        {mode === 'ask' && history.map((msg, i) => (
          <div key={i} className={`terminal-message terminal-${msg.role}`}>
            <span className="terminal-prompt">
              {msg.role === 'user' ? '❯' : '↳'}
            </span>
            <span className={`terminal-content ${msg.streaming ? 'terminal-streaming' : ''}`}>
              {msg.content}
              {msg.streaming && <span className="terminal-cursor">▊</span>}
            </span>
          </div>
        ))}

        {mode === 'draft' && (
          <div className="terminal-mode-content">
            {!draftResult && (
              <div className="terminal-hints">
                <p>Describe what you want to write. ContextOS will use your past writing style.</p>
                <span>"Write an email to the team about the project delay"</span>
                <span>"Draft a status update for the Q4 review"</span>
              </div>
            )}
            {draftResult && (
              <div className="terminal-answer">
                <div className="terminal-answer-text">{draftResult.draft}</div>
                {draftResult.context_used?.length > 0 && (
                  <div className="terminal-answer-meta">
                    Context used: {draftResult.context_used.join(', ')}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {mode === 'brief' && (
          <div className="terminal-mode-content">
            {!briefResult && (
              <div className="terminal-hints">
                <p>Enter the names of meeting attendees separated by commas.</p>
                <span>"Alice, Bob, Priya"</span>
                <span>"John, Sarah, Mike, Lisa"</span>
              </div>
            )}
            {briefResult && (
              <div className="terminal-answer">
                <div className="terminal-answer-text">{briefResult.brief}</div>
                {briefResult.people_found?.length > 0 && (
                  <div className="terminal-answer-meta">
                    People in knowledge graph: {briefResult.people_found.join(', ')}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <form className="terminal-input-row" onSubmit={handleSubmit}>
        <span className="terminal-input-prompt">
          {mode === 'ask' ? '❯' : mode === 'draft' ? '✎' : '▸'}
        </span>
        <input
          className="terminal-input"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholder}
          disabled={loading}
          autoFocus
        />
        <button className="terminal-send-btn" type="submit" disabled={loading || !input.trim()}>
          {loading ? <span className="spinner">◌</span> : '⏎'}
        </button>
      </form>
    </div>
  )
}
