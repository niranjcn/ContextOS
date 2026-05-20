import React, { useState } from 'react'

export default function QueryBox({ apiBase }) {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleQuery(e) {
    e.preventDefault()
    if (!question.trim()) return

    setLoading(true)
    setAnswer(null)

    try {
      const res = await fetch(`${apiBase}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question.trim() }),
      })
      const data = await res.json()
      if (res.ok) {
        setAnswer(data)
      } else {
        setAnswer({ answer: `Error: ${data.detail || 'Query failed'}`, sources: [] })
      }
    } catch (err) {
      setAnswer({ answer: `Connection error: ${err.message}`, sources: [] })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="query-section">
      <h2 className="section-title">🔍 Ask ContextOS</h2>
      <form onSubmit={handleQuery}>
        <div className="query-input-wrapper">
          <input
            className="query-input"
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="What did John discuss in last week's meeting?"
            disabled={loading}
          />
          <button className="query-btn" type="submit" disabled={loading || !question.trim()}>
            {loading ? '⏳ Thinking...' : 'Ask'}
          </button>
        </div>
      </form>

      {answer && (
        <div>
          <div className="answer-box">{answer.answer}</div>
          {answer.sources?.length > 0 && (
            <div className="answer-meta">
              Sources: {answer.sources.join(', ')} | Model: {answer.model_used} |
              Retrieval: {answer.retrieval_time_ms}ms | Inference: {answer.inference_time_ms}ms
            </div>
          )}
        </div>
      )}
    </div>
  )
}
