# ContextOS — Remaining Work

Everything that's not yet implemented or needs polish.

---

## Not Started (0%)

### Desktop Builds
- **macOS app bundle** — Swift wrapper with embedded Ollama, one-click install
- **Windows installer** — NSIS or MSI package
- No packaging scripts exist yet

### Enterprise Features (v1.0)
- **Team mode** — shared knowledge graph with per-user encryption
- **Admin panel** — user management, usage stats, system config
- **Plugin SDK** — WASM-based plugin system for custom connectors/features
- **Audit log** — immutable record of all queries and data access
- **SSO integration** — OIDC/SAML for enterprise auth

---

## In Progress

### Browser Extension
- **Status**: Scaffolded (Manifest V3, content/background/popup, icons)
- **What it does**: Captures page content (title, URL, body text) and sends to ContextOS API
- **What's done**: `manifest.json`, `content.js`, `background.js`, `popup.html`, `popup.js`, placeholder icons
- **What's missing**:
  - Error retry/queue mechanism for failed sends
  - Smart content extraction (readability fork for article-only capture, not full body text)
  - Configurable capture shortcuts
  - Icon badge showing number of pending (unsent) captures
  - Site blacklist (e.g. exclude mail.google.com)
  - Tab-specific capture toggle
  - Firefox port (Manifest V3 compatible)

---

## Needs Polish

### Connectors

| Connector | Current State | What's Missing |
|-----------|--------------|----------------|
| **Gmail** | OAuth works, one-shot fetch works | No auto-scheduled background sync; no error recovery for API quotas; no incremental sync (always fetches all) |
| **Google Drive** | Lists files, downloads content | No pagination beyond first page; no folder traversal; no MIME-type filtering; no incremental sync (~60% complete) |
| **Browser History** | Chrome & Firefox parsing works | No Safari support; no polling/daemon mode; no recency filtering beyond SQL LIMIT |
| **Local Files** | Polling works, multi-format support | Not auto-registered in the sync system; must be explicitly called |

#### Fix needed in `connectors/gdrive.py`:
- Implement pagination (currently fetches first page only)
- Add recursive folder traversal
- Add incremental sync (track last sync time, only fetch newer files)
- Broaden MIME-type export handling

### Features

| Feature | Current State | What's Missing |
|---------|--------------|----------------|
| **Smart Draft** | Uses `ContextEngine.generate()`, style examples retrieved | Hardcoded "professional, clear tone" fallback when no style examples found; no real style learning from user's writing via embedding comparison |
| **Meeting Brief** | Uses `ContextEngine.generate()`, per-participant retrieval | No calendar API integration (date/agenda must be manually provided) |
| **Decision Log** | Keyword-based search works | No persistent storage — purely query-time keyword matching against ingested docs; no NLP-based classification |
| **Transcriber** | Whisper integration, `openai-whisper` uncommented in `requirements.txt` | User must manually install ffmpeg on host; not available inside Docker container |

#### Fixes needed:
- `features/smart_draft.py` — Replace hardcoded tone fallback with actual writing pattern analysis (compare embeddings of user's past writing)
- `features/meeting_brief.py` — Add calendar API integration (Google Calendar, Outlook)
- `features/decision_log.py` — Add persistent `Decision` node type to the Kuzu graph schema; classify sentences as decisions via NLP
- `requirements.txt` — `openai-whisper` is now uncommented; ffmpeg dependency still needs documenting

### Dashboard (React)

| Component | Current State | What's Missing |
|-----------|--------------|----------------|
| **QueryBox** | Single query works | No streaming response (uses `POST /query`, not `POST /query/stream`); no conversation history |
| **GraphViewer** | People list with click-to-docs works | No organization browsing tab; no network visualization (currently just lists); no search/filter |
| **IngestStatus** | File upload, text paste, stats display works | No delete/re-ingest controls; no progress indicator for long ingests |
| **StatusPanel** | Health cards, auto-refresh works | No model management (pull new models from UI) |

### Tests

| Area | Coverage | What's Missing |
|------|----------|---------------|
| Core engine | 95% | Minor improvements possible in edge case coverage |
| Connectors | 0% | No tests for any connector (requires actual accounts / browser files) |
| Features | 0% | No tests for smart_draft, meeting_brief, decision_log, transcriber |
| Performance | 0% | No benchmark or stress tests |
| Integration | Partial | Tests use mocks for Ollama (appropriate for CI), but no end-to-end tests with a real LLM |

---

## Infrastructure Gaps

| Area | Issue |
|------|-------|
*(none — K8s, Terraform, Jenkins removed; CI/CD via GitHub Actions only)*
