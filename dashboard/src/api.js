/**
 * ContextOS API Client.
 *
 * Centralised fetch-based client for all backend endpoints.
 * Every function returns parsed JSON and throws with a readable message on error.
 */

const BASE = '/api'

async function request(path, options = {}) {
  const url = `${BASE}${path}`
  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    })
    const data = await res.json().catch(() => null)
    if (!res.ok) {
      throw new Error(data?.detail || `Request failed: ${res.status}`)
    }
    return data
  } catch (err) {
    if (err.message.includes('fetch')) {
      throw new Error('Cannot reach the ContextOS API. Is the server running?')
    }
    throw err
  }
}

export const api = {
  // ---- Query ----
  query: (question) =>
    request('/query', {
      method: 'POST',
      body: JSON.stringify({ question }),
    }),

  queryDraft: (instruction, recipient = '') =>
    request('/query/draft', {
      method: 'POST',
      body: JSON.stringify({ instruction, recipient }),
    }),

  queryBrief: (meetingTitle, attendees, meetingTime = '') =>
    request('/query/brief', {
      method: 'POST',
      body: JSON.stringify({
        meeting_title: meetingTitle,
        attendees,
        meeting_time: meetingTime,
      }),
    }),

  // ---- Ingest ----
  ingestText: (text, docId, source = 'dashboard', metadata = {}) =>
    request('/ingest/text', {
      method: 'POST',
      body: JSON.stringify({ text, doc_id: docId, source, metadata }),
    }),

  uploadFile: async (file, source = 'file_upload') => {
    const formData = new FormData()
    formData.append('file', file)
    const url = `${BASE}/ingest/file`
    const res = await fetch(url, { method: 'POST', body: formData })
    const data = await res.json().catch(() => null)
    if (!res.ok) throw new Error(data?.detail || 'File upload failed')
    return data
  },

  getIngestStatus: () => request('/ingest/status'),

  deleteSource: (sourceName) =>
    request(`/ingest/source/${encodeURIComponent(sourceName)}`, {
      method: 'DELETE',
    }),

  // ---- Graph ----
  getPeople: () => request('/graph/people'),

  getPersonDocs: (name) =>
    request(`/graph/people/${encodeURIComponent(name)}/documents`),

  getOrganizations: () => request('/graph/organizations'),

  getDocuments: (limit = 20) => request(`/graph/documents?limit=${limit}`),

  getStats: () => request('/graph/stats'),

  // ---- Health ----
  getHealth: () => request('/health'),

  getModels: () => request('/health/models'),
}
