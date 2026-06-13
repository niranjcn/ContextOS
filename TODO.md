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

## Recently Completed

### Dashboard: Connector Setup + Terminal Query
- **Connector configuration UI** — New "Connectors" tab in the dashboard with:
  - Card-based layout showing each connector (Gmail, Drive, Browser History, Local Files)
  - Guided step-by-step setup modal with external links to Google Cloud Console
  - Inline credential file upload (drag/click to upload `credentials.json`)
  - Toggle switch to enable/disable connectors
  - Expand/collapse sections for credentials, path config, and sync controls
  - Sync Now button with progress indicator
- **Terminal-style Query interface** — Upgraded "Query" tab to a terminal emulator with:
  - Monospace prompt with `❯` prefix
  - Streaming responses (uses `POST /query/stream` with SSE)
  - Sub-tabs for Query, Draft, and Meeting Brief modes
  - Conversation history with blinking cursor during streaming
  - Example hints in the welcome screen
  - Session clear button
  - Supports all three query modes from a single terminal interface
- **Backend: Connectors API** — New `GET/POST /connectors/*` endpoints with:
  - JSON config store (`connectors_config.json` in data directory)
  - Credential file management (save OAuth JSON to `secrets/`)
  - Sync triggers that call the actual connector code
  - Per-connector setup guides with numbered steps and external links

### Browser Extension
- **Status**: Scaffolded (Manifest V3, content/background/popup, icons)
- **What it does**: Captures page content (title, URL, body text) and sends to ContextOS API
- **What's done**: `manifest.json`, `content.js`, `background.js`, `popup.html`, `popup.js`, placeholder icons
- **What's missing**:
  - Error retry/queue mechanism for failed sends
  - Smart content extraction (readability fork for article-only capture)
  - Configurable capture shortcuts
  - Site blacklist
  - Firefox port

---

## Needs Polish

### Connectors (backend)

| Connector | Current State | What's Missing |
|-----------|--------------|----------------|
| **Gmail** | OAuth works, one-shot fetch works, dashboard config UI ready | No auto-scheduled background sync; no error recovery for API quotas; no incremental sync (always fetches all) |
| **Google Drive** | Lists files, downloads content | No pagination beyond first page; no folder traversal; no MIME-type filtering; no incremental sync (~60% complete) |
| **Browser History** | Chrome & Firefox parsing works, dashboard config UI ready | No Safari support; no polling/daemon mode; no recency filtering beyond SQL LIMIT |
| **Local Files** | Polling works, multi-format support, dashboard config UI ready | Not auto-registered in the sync system; must be explicitly called |

#### Fix needed in `connectors/gdrive.py`:
- Implement pagination (currently fetches first page only)
- Add recursive folder traversal
- Add incremental sync (track last sync time, only fetch newer files)
- Broaden MIME-type export handling

#### Connector config now managed via Dashboard UI:
- `core/api/routers/connectors.py` — REST API for config CRUD
- `core/config_store.py` — JSON file store in data directory
- `dashboard/src/components/Connectors.jsx` — Full UI with guides, credential upload, toggles, sync
- Future: migrate connector backend code to read from `config_store` instead of only `.env`

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
| **QueryBox** | Terminal-style interface with streaming, history, draft/brief modes | No conversation persistence across page reload; no export/copy buttons |
| **GraphViewer** | People list with click-to-docs works | No organization browsing tab; no network visualization (currently just lists); no search/filter |
| **IngestStatus** | File upload, text paste, stats display works | No delete/re-ingest controls; no progress indicator for long ingests |
| **Connectors** | Full setup UI with guides, credential upload, toggles, sync | No real-time sync progress polling; no credential validation test |
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
