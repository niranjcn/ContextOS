import React, { useState } from 'react'
import { api } from '../api'

export default function QueryBox() {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleQuery(e) {
    e.preventDefault()
    if (!question.trim()) return

    setLoading(true)
    setAnswer(null)
    setError(null)

    try {
      const data = await api.query(question.trim())
      setAnswer(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="panel">
      <h2 className="section-title">
        <span className="section-icon">🔍</span> Ask ContextOS
      </h2>
      <p className="section-desc">
        Ask questions about your documents, emails, meetings — everything in your knowledge base.
      </p>

      <form onSubmit={handleQuery}>
        <div className="query-input-wrapper">
          <input
            id="query-input"
            className="query-input"
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="What did John discuss in last week's meeting?"
            disabled={loading}
          />
          <button
            id="query-submit"
            className="btn-primary"
            type="submit"
            disabled={loading || !question.trim()}
          >
            {loading ? (
              <>
                <span className="spinner">◌</span> Thinking…
              </>
            ) : (
              'Ask'
            )}
          </button>
        </div>
      </form>

      {/* Error state */}
      {error && (
        <div className="error-box">
          <span className="error-icon">⚠</span> {error}
        </div>
      )}

      {/* Answer state */}
      {answer && (
        <div className="answer-container">
          <div className="answer-box">{answer.answer}</div>
          <div className="answer-meta">
            {answer.sources?.length > 0 && (
              <span className="meta-item">
                <strong>Sources:</strong> {answer.sources.join(', ')}
              </span>
            )}
            <span className="meta-item">
              Model: {answer.model_used}
            </span>
            <span className="meta-item">
              Retrieval: {answer.retrieval_time_ms}ms
            </span>
            <span className="meta-item">
              Inference: {answer.inference_time_ms}ms
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
