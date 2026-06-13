# ContextOS — Remaining Work

Everything that's not yet implemented or needs polish.

---

## Not Started (0%)

### Browser Extension
- Chrome extension to capture reading context in real time
- Would inject into the browser's reading flow and push to the ingestion pipeline
- No code exists yet

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
| **Smart Draft** | Basic retrieval + prompt works | Hardcoded "professional, clear tone"; no real style learning from user's writing; creates its own Ollama client instead of using the engine's singleton |
| **Meeting Brief** | Per-participant retrieval works | Same redundant Ollama client creation; no calendar integration (date/agenda must be manually provided) |
| **Decision Log** | Keyword-based search works | No persistent storage — purely query-time keyword matching against ingested docs; no NLP-based classification |
| **Transcriber** | Whisper integration works | `openai-whisper` commented out in `requirements.txt` on line 3; user must manually install it |

#### Fixes needed:
- `features/smart_draft.py` — Replace hardcoded tone with actual writing pattern analysis; use `ContextEngine` from `core/inference/engine.py` instead of creating a new Ollama client
- `features/meeting_brief.py` — Same Ollama client issue; add calendar API integration
- `features/decision_log.py` — Add persistent `Decision` node type to the Kuzu graph schema
- `requirements.txt` — Uncomment `openai-whisper` once the build issue is resolved

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
| Core engine | 95% | One minor bug in `graph.py:241` (broken f-string for LIMIT clause) |
| Connectors | 0% | No tests for any connector (requires actual accounts / browser files) |
| Features | 0% | No tests for smart_draft, meeting_brief, decision_log, transcriber |
| Performance | 0% | No benchmark or stress tests |
| Integration | Partial | Tests use mocks for Ollama (appropriate for CI), but no end-to-end tests with a real LLM |

---

## Known Bugs

1. **`core/storage/graph.py:241`** — Broken f-string for the LIMIT clause. The string `"ORDER BY d.date DESC LIMIT {limit}"` is not actually an f-string (the second string literal lacks the `f` prefix due to concatenation). Will cause a Cypher syntax error at runtime.

---

## Infrastructure Gaps

| Area | Issue |
|------|-------|
| **K8s secrets** | `k8s/secret.yaml` contains placeholder base64 values — must generate real encryption keys |
| **K8s registry** | All deployment YAMLs contain `YOUR_REGISTRY/contextos-api:IMAGE_TAG` — must replace with real ECR URLs |
| **K8s domain** | Ingress host is `contextos.yourdomain.com` — must replace with real domain |
| **Terraform backend** | S3 backend config is commented out in `terraform/main.tf:37-43` — must uncomment and configure before production use |
| **Terraform apply order** | `main.tf:299` references `aws_eks_cluster.main.identity[0].oidc[0].issuer` which may fail on first apply (chicken-and-egg with the EKS cluster resource on line 306) |
