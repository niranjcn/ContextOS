# ContextOS

> Your private AI memory layer — everything you know, instantly searchable.

ContextOS is a **100% on-device, privacy-first AI context engine** for knowledge
workers. It captures your emails, documents, calendar events, browser activity,
and meeting recordings, builds a local knowledge graph and vector store, and lets
you query your entire professional life in natural language — using a locally
running LLM with **zero cloud dependency and zero data leaving your machine**.

---

## Why ContextOS exists

Every AI tool today treats you like a stranger at the start of every session. You
explain the same project to ChatGPT, then to Copilot, then to Gemini. None of them
know your working style, your past decisions, the names of the people you work with,
or what you agreed to in last Thursday's meeting.

ContextOS fixes this. It builds a persistent "professional brain" on your machine
that all your tools — and you — can tap into at any time.

The **on-device-first architecture** is what makes this viable for enterprises in
regulated industries (healthcare, finance, legal, government) where cloud AI tools
are blocked by GDPR, HIPAA, and SOC 2 requirements. Your data never leaves your
machine. Full stop.

---

## Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | In progress | Foundation — local LLM + basic RAG |
| Phase 2 | Planned | Ingestion engine — email, docs, files |
| Phase 3 | Planned | Context engine — hybrid retrieval |
| Phase 4 | Planned | API + React dashboard |
| Phase 5 | Planned | Smart drafting, meeting briefs, decision log |
| Phase 6 | Planned | Open source launch + enterprise edition |

---

## Core Features

### What it does today (Phase 1)
- Run a local LLM (Llama 3.2 or Mistral) via Ollama — no API key needed
- Ingest any text file and ask questions about it in natural language
- Local vector search over ingested documents using ChromaDB
- REST API on `localhost:8000` for programmatic access
- CLI: `contextos query "what did I decide about vendor X?"`

### What it will do (Phases 2–5)
- **Gmail / Google Drive connector** — auto-ingests your emails and documents
- **Local file watcher** — monitors a folder, ingests new files automatically
- **Meeting transcription** — drop an audio file, Whisper transcribes + ingests it
- **Knowledge graph** — entities (people, orgs, topics) linked to documents in Kuzu
- **Smart email drafting** — writes emails in your tone based on your history
- **Meeting brief generator** — 1-page brief 30 min before any calendar event
- **Decision log** — searchable history of past choices with source citations
- **Browser extension** — captures your reading context in real time

---

## How it works

```
Your data (emails, docs, meetings)
         │
         ▼
  [Connectors Layer]
  Gmail · Drive · Files · Browser · Whisper
         │
         ▼
  [Ingestion Pipeline]
  Parse → Chunk → Extract entities (spaCy) → Embed (sentence-transformers)
         │
         ┌──────────────────────────┐
         ▼                          ▼
  [ChromaDB]                  [Kuzu Graph DB]
  Semantic chunks             Entity relationships
  (what was said)             (who, what, when, where)
         │                          │
         └──────────┬───────────────┘
                    ▼
         [Hybrid Retriever]
         Vector search + Graph traversal
                    │
                    ▼
         [Prompt Builder]
         Injects retrieved context into LLM prompt
                    │
                    ▼
         [Ollama — Local LLM]
         Llama 3.2 / Mistral 7B
         Runs entirely on your machine
                    │
                    ▼
         [Answer + Sources]
         Cited, grounded, private
```

Everything is encrypted at rest using AES-256-GCM. All processing happens locally.
No telemetry. No analytics. No network calls after initial model download.

---

## Tech Stack

### Core Technologies

| Component | Technology | Version | Why this choice |
|-----------|-----------|---------|-----------------|
| Language | Python | 3.11+ | Ecosystem, readability, AI library support |
| LLM runtime | Ollama | latest | One-command local LLM serving, model management |
| Primary model | Llama 3.2 | 3B/8B | Best quality-to-size ratio for on-device use |
| Fallback model | Mistral | 7B | Strong alternative, excellent instruction following |
| Embeddings | sentence-transformers | 3.1.1 | all-MiniLM-L6-v2 runs fast on CPU, good quality |
| Vector DB | ChromaDB | 0.5.18 | Embedded, no server, persistent, Python-native |
| Graph DB | Kuzu | 0.6.0 | Embedded graph DB, Cypher queries, fast, no server |
| Metadata DB | SQLite | built-in | Lightweight, reliable, zero config |
| NLP | spaCy | 3.7.6 | Fast NER, runs locally, battle-tested |
| Doc parsing | LangChain + Tika | 0.3.7 | 40+ file formats, well-maintained |
| API | FastAPI | 0.115.4 | Fast, typed, auto-docs, async support |
| CLI | Typer + Rich | 0.12.5 | Beautiful terminal UI, type-safe commands |
| Encryption | cryptography | 43.0.3 | AES-256-GCM, PBKDF2 key derivation |
| Transcription | Whisper | 20240930 | OpenAI's open source model, runs fully locally |
| Frontend | React 18 + Vite | - | Fast dev experience, small bundle |
| Testing | pytest | 8.3.3 | Standard Python testing, great plugin ecosystem |

### Why NOT cloud services

| Cloud alternative | Why we don't use it |
|------------------|---------------------|
| OpenAI API | Data leaves your machine; costs money; requires internet |
| Pinecone | Data leaves your machine; costs money |
| MongoDB Atlas | Data leaves your machine |
| AWS S3 | Data leaves your machine |
| Google Cloud NLP | Data leaves your machine |

Every component in ContextOS runs on your hardware, in your filesystem, under your
control. This is not a privacy feature — it is the core architecture.

---

## Directory Structure

```
contextos/
├── README.md                    ← you are here
├── LICENSE                      ← Apache 2.0
├── CONTRIBUTING.md              ← contribution guidelines
├── CHANGELOG.md                 ← version history
├── .env.example                 ← copy to .env and fill in values
├── .gitignore
├── pyproject.toml               ← project metadata + tool config
├── requirements.txt             ← production dependencies (pinned)
├── requirements-dev.txt         ← dev + test dependencies
├── Makefile                     ← common dev commands
│
├── core/                        ← THE BRAIN (all business logic)
│   ├── config.py                ← settings singleton (loads .env)
│   ├── encryption.py            ← AES-256-GCM encrypt/decrypt
│   │
│   ├── ingestion/               ← data capture + processing
│   │   ├── base.py              ← BaseConnector abstract class
│   │   ├── extractor.py         ← spaCy entity extraction
│   │   ├── chunker.py           ← text splitting into chunks
│   │   └── pipeline.py          ← orchestrates the full ingest flow
│   │
│   ├── storage/                 ← all persistence layers
│   │   ├── graph.py             ← Kuzu knowledge graph wrapper
│   │   ├── vectors.py           ← ChromaDB vector store wrapper
│   │   └── metadata.py          ← SQLite sync-state tracker
│   │
│   ├── inference/               ← query processing + answer generation
│   │   ├── retriever.py         ← hybrid graph + vector retrieval
│   │   ├── prompt_builder.py    ← context-aware prompt construction
│   │   └── engine.py            ← main RAG query engine
│   │
│   └── api/                     ← REST API
│       ├── main.py              ← FastAPI app factory + middleware
│       ├── models.py            ← Pydantic request/response schemas
│       └── routers/
│           ├── query.py         ← POST /query (ask a question)
│           ├── graph.py         ← GET /graph/* (browse knowledge)
│           ├── ingest.py        ← POST /ingest/* (add documents)
│           └── health.py        ← GET /health (system status)
│
├── connectors/                  ← external data source integrations
│   ├── local_files.py           ← watch a folder, auto-ingest files
│   ├── gmail.py                 ← Gmail API (OAuth2)
│   ├── gdrive.py                ← Google Drive API
│   └── browser_history.py       ← Chrome/Firefox local history
│
├── features/                    ← high-level AI-powered features
│   ├── smart_draft.py           ← write emails in your voice
│   ├── meeting_brief.py         ← pre-meeting 1-page brief
│   ├── decision_log.py          ← search past decisions with sources
│   └── transcriber.py           ← Whisper audio → text → ingest
│
├── cli/
│   └── main.py                  ← Typer CLI (contextos query, ingest, etc.)
│
├── dashboard/                   ← React control panel
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       └── components/
│           ├── QueryBox.jsx     ← ask questions in the UI
│           ├── GraphViewer.jsx  ← browse your knowledge graph
│           └── IngestStatus.jsx ← see what's been indexed
│
└── tests/                       ← test suite
    ├── conftest.py              ← shared fixtures
    ├── test_encryption.py
    ├── test_extractor.py
    ├── test_chunker.py
    ├── test_graph.py
    ├── test_vectors.py
    ├── test_retriever.py
    ├── test_engine.py
    └── test_api.py
```

---

## System Requirements

### Minimum (runs everything on CPU)
- OS: Linux (Ubuntu 22.04+), macOS 12+, Windows 11 with WSL2
- Python: 3.11 or higher
- RAM: 16 GB (8 GB usable for the app, 8 GB for the LLM)
- Storage: 10 GB free (models ~5 GB, data ~5 GB depending on your corpus)
- CPU: Any modern x86-64 or Apple Silicon

### Recommended (faster inference)
- RAM: 32 GB
- GPU: NVIDIA with 8+ GB VRAM (CUDA 12+) OR Apple Silicon M1/M2/M3
- Storage: 50 GB SSD

### Model size guide

| Model | RAM needed | Speed (CPU) | Quality |
|-------|-----------|-------------|---------|
| llama3.2:3b | 4 GB | Fast (~20 tok/s) | Good for simple queries |
| llama3.2:8b | 8 GB | Medium (~8 tok/s) | Recommended default |
| mistral:7b | 8 GB | Medium (~8 tok/s) | Strong alternative |
| llama3.1:70b | 48 GB | Slow (GPU needed) | Best quality |

Start with `llama3.2` (3B). You can switch models any time in your `.env`.

---

## Installation

### Step 1 — Clone the repository

```bash
git clone https://github.com/your-username/contextos.git
cd contextos
```

### Step 2 — Install Ollama

Ollama is the local LLM runtime. Install it first.

```bash
# Linux / macOS
curl -fsSL https://ollama.ai/install.sh | sh

# Windows: download installer from https://ollama.ai/download
```

Verify it's running:
```bash
ollama --version
# Should print: ollama version 0.x.x
```

### Step 3 — Pull a language model

```bash
# Download Llama 3.2 (3B, ~2 GB — good for most laptops)
ollama pull llama3.2

# Or the 8B version for better quality (requires 8+ GB RAM)
ollama pull llama3.2:8b

# Verify it works
ollama run llama3.2 "Hello, are you running locally?"
```

### Step 4 — Set up Python environment

```bash
# Create and activate a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Download spaCy language model (for entity recognition)
python -m spacy download en_core_web_sm
```

### Step 5 — Configure your environment

```bash
# Copy the example config
cp .env.example .env

# Generate an encryption key
python -c "
from cryptography.fernet import Fernet
print('CONTEXTOS_ENCRYPTION_KEY=' + Fernet.generate_key().decode())
"
# Paste the output into your .env file
```

Open `.env` and set at minimum:
```env
CONTEXTOS_DATA_DIR=~/.contextos/data
CONTEXTOS_DB_DIR=~/.contextos/db
CONTEXTOS_ENCRYPTION_KEY=<your-generated-key>
OLLAMA_MODEL=llama3.2
```

### Step 6 — Verify the setup

```bash
# Run the test suite
make test

# Check Ollama connection
make check-ollama

# Start the API server
make run-api
# Open http://localhost:8000/docs in your browser
```

### Step 7 — Your first query

```bash
# Ingest a text file
contextos ingest file path/to/any-document.txt

# Ask a question about it
contextos query "summarize the main points of this document"

# Or via the API
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "what is this document about?"}'
```

---

## Configuration Reference

Every setting lives in `.env`. Here is the complete reference:

### Paths

| Variable | Default | Description |
|----------|---------|-------------|
| `CONTEXTOS_DATA_DIR` | `~/.contextos/data` | Raw ingested content storage |
| `CONTEXTOS_DB_DIR` | `~/.contextos/db` | Database files (graph, vectors, metadata) |
| `CONTEXTOS_LOG_DIR` | `~/.contextos/logs` | Log files |

### LLM Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Primary model name |
| `OLLAMA_FALLBACK_MODEL` | `mistral` | Used if primary fails |
| `OLLAMA_TIMEOUT` | `120` | Seconds before inference timeout |

### Embedding Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | HuggingFace sentence-transformer model |

The embedding model downloads automatically on first run (~90 MB).

### API Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `127.0.0.1` | Bind address (localhost only for security) |
| `API_PORT` | `8000` | Port number |
| `API_RELOAD` | `true` | Hot reload in development |

### Encryption

| Variable | Default | Description |
|----------|---------|-------------|
| `CONTEXTOS_ENCRYPTION_KEY` | required | Base64 AES key — generate with the command above |
| `ENABLE_ENCRYPTION` | `true` | Set to `false` for development only |

### Feature Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_GMAIL` | `false` | Gmail connector (requires OAuth setup) |
| `ENABLE_GDRIVE` | `false` | Google Drive connector |
| `ENABLE_BROWSER_HISTORY` | `false` | Browser history connector |
| `ENABLE_WHISPER` | `false` | Meeting transcription |

---

## API Reference

The API runs at `http://localhost:8000`. Interactive docs at `/docs`.

### Query

**`POST /query`** — Ask a question about your context

```json
Request:
{
  "question": "What did I discuss with Priya last week?"
}

Response:
{
  "answer": "Based on your emails from Nov 12, you discussed...",
  "sources": ["email:thread_abc123", "doc:meeting_notes_nov12.txt"],
  "model_used": "llama3.2",
  "retrieval_time_ms": 45,
  "inference_time_ms": 3200
}
```

**`POST /query/stream`** — Streaming version (Server-Sent Events)

### Ingest

**`POST /ingest/text`** — Ingest raw text

```json
Request:
{
  "content": "Meeting notes from Nov 14...",
  "source": "manual",
  "metadata": { "title": "Q4 Planning Meeting", "date": "2024-11-14" }
}

Response:
{
  "doc_id": "abc123",
  "chunks_created": 8,
  "entities_extracted": { "people": ["Alice", "Bob"], "orgs": ["Acme Corp"] },
  "status": "success"
}
```

**`POST /ingest/file`** — Upload a file (multipart form)

```bash
curl -X POST http://localhost:8000/ingest/file \
  -F "file=@/path/to/report.pdf" \
  -F "source=local"
```

**`GET /ingest/status`** — Ingestion statistics

```json
{
  "total_documents": 342,
  "by_source": { "gmail": 280, "local_files": 52, "manual": 10 },
  "last_sync": "2024-11-14T09:32:11Z"
}
```

### Graph

**`GET /graph/people`** — All people in your knowledge graph

```json
{ "people": ["Alice Johnson", "Bob Chen", "Priya Nair"], "count": 47 }
```

**`GET /graph/people/{name}/documents`** — Documents mentioning a person

```json
{
  "person": "Priya Nair",
  "documents": [
    { "title": "Q3 Review", "date": "2024-09-15", "source": "gdrive" },
    { "title": "Re: Budget approval", "date": "2024-10-02", "source": "gmail" }
  ]
}
```

**`GET /graph/stats`** — Knowledge graph statistics

```json
{
  "nodes": { "Person": 47, "Organization": 23, "Document": 342, "Topic": 158 },
  "relationships": 1205
}
```

### Health

**`GET /health`** — System status

```json
{
  "status": "healthy",
  "ollama_running": true,
  "models_available": ["llama3.2", "mistral"],
  "vector_count": 8432,
  "graph_node_count": 570,
  "uptime_seconds": 3602
}
```

---

## CLI Reference

```bash
# Ask a question
contextos query "what decisions did I make about the API design?"

# Ingest files
contextos ingest path/to/folder         # all supported files in folder
contextos ingest file report.pdf        # single file
contextos ingest file notes.txt --source work-notes

# Transcribe a meeting
contextos transcribe meeting-2024-11-14.mp3
contextos transcribe recording.mp4 --title "Q4 planning call"

# Browse the knowledge graph
contextos graph people                  # list all people
contextos graph people "Alice"          # docs mentioning Alice
contextos graph docs                    # recent documents
contextos graph stats                   # graph statistics

# System commands
contextos status                        # health check
contextos serve                         # start the API server
contextos serve --port 8080             # custom port

# Help
contextos --help
contextos query --help
```

---

## Data Flow — Detailed

Understanding data flow helps you debug and extend ContextOS.

### Ingestion flow

```
Source document (email, PDF, meeting audio)
        │
        ▼
[Connector] — fetches raw content, assigns stable doc_id
        │
        ▼
[MetadataStore.is_processed()] — skip if already ingested
        │ (if new)
        ▼
[Apache Tika / LangChain loader] — extract plain text from any format
        │
        ├──────────────────────────────────────┐
        ▼                                      ▼
[TextChunker]                          [EntityExtractor]
splits text into                       spaCy NER extracts:
600-char chunks                        people, orgs, dates,
with 80-char overlap                   locations, topics
        │                                      │
        ▼                                      ▼
[VectorStore.add_chunks()]             [GraphStore.add_entity()]
ChromaDB embeds each chunk             Kuzu upserts entities
using all-MiniLM-L6-v2                 and links them to document
        │                                      │
        └──────────────────────────────────────┘
        ▼
[MetadataStore.mark_processed()] — record completion
```

### Query flow

```
User question: "what did I decide about the authentication approach?"
        │
        ▼
[EntityExtractor] — extracts "authentication" as topic
        │
        ├──────────────────────────────────────┐
        ▼                                      ▼
[VectorStore.search()]                 [GraphStore traversal]
Top 5 semantically similar             Documents tagged with
chunks (cosine similarity)             "authentication" topic
        │                                      │
        └──────────────────┬───────────────────┘
                           ▼
               [PromptBuilder.build()]
               Structures context into:
               - Graph facts section
               - Relevant documents section
               - Instructions section
               - User question
                           │
                           ▼
                  [Ollama — local LLM]
                  llama3.2 generates answer
                  grounded in retrieved context
                           │
                           ▼
                  [EngineResponse]
                  answer + sources + timing metadata
```

---

## Storage Architecture

### ChromaDB (vector store)

- Location: `~/.contextos/db/chroma/`
- Collection: `contextos_chunks`
- Each document is split into ~600-character chunks
- Each chunk is embedded as a 384-dimensional vector
- Search: cosine similarity, returns top-k chunks

### Kuzu (knowledge graph)

- Location: `~/.contextos/db/kuzu/`
- Node types: `Person`, `Organization`, `Document`, `Topic`
- Relationship types: `MENTIONED_IN`, `WORKS_AT`, `RELATES_TO`
- Query language: Cypher (same as Neo4j)
- Example: `MATCH (p:Person)-[:MENTIONED_IN]->(d:Document) RETURN p.name, d.title`

### SQLite (metadata)

- Location: `~/.contextos/db/metadata.db`
- Tracks: doc_id, source, ingestion timestamp, file hash
- Purpose: prevents re-processing the same document twice

### File encryption

- Algorithm: AES-256-GCM
- Key derivation: PBKDF2-HMAC-SHA256 (100,000 iterations)
- All stored content is encrypted before write, decrypted on read
- The encryption key never leaves your machine — it lives only in your `.env`

---

## Development Guide

### Running tests

```bash
# Run all tests
make test

# Run with coverage report
pytest tests/ -v --cov=core --cov-report=html
open htmlcov/index.html  # view coverage in browser

# Run a specific test file
pytest tests/test_graph.py -v

# Run tests matching a pattern
pytest tests/ -k "test_encryption" -v
```

### Code quality

```bash
# Format code
make format

# Check style without changing files
make lint

# Type check
mypy core/ --ignore-missing-imports
```

### Adding a new connector

1. Create `connectors/your_source.py`
2. Extend `BaseConnector` from `core/ingestion/base.py`
3. Implement `fetch() -> list[dict]` and `validate_config() -> bool`
4. Add a feature flag to `.env.example`: `ENABLE_YOUR_SOURCE=false`
5. Add config loading to `core/config.py`
6. Register the connector in `core/ingestion/pipeline.py`
7. Write tests in `tests/test_connector_your_source.py`

### Adding a new feature

1. Create `features/your_feature.py`
2. Import `ContextEngine` and `HybridRetriever` as dependencies
3. Add a CLI command in `cli/main.py`
4. Add an API endpoint in `core/api/routers/`
5. Write tests

### Environment for development

```bash
# Install dev dependencies
make install-dev

# Set up pre-commit hooks (auto-formats on commit)
pre-commit install

# Run the API in dev mode (auto-reloads on file change)
make run-api
```

---

## Connecting Google Services (Optional)

Gmail and Google Drive connectors require OAuth2 setup. This is optional — the
local file connector works without any Google account.

### Step 1 — Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project named "ContextOS"
3. Enable these APIs:
   - Gmail API
   - Google Drive API
4. Go to "Credentials" → "Create OAuth 2.0 Client ID"
5. Application type: Desktop app
6. Download the JSON file
7. Save it to `~/.contextos/google_credentials.json`

### Step 2 — Set your .env

```env
GOOGLE_CLIENT_SECRETS_FILE=~/.contextos/google_credentials.json
GOOGLE_TOKEN_FILE=~/.contextos/google_token.json
ENABLE_GMAIL=true
ENABLE_GDRIVE=true
```

### Step 3 — Authorize

```bash
# This opens a browser window for OAuth consent
contextos connect gmail
# Follow the prompts, then close the browser tab
# A token is saved to ~/.contextos/google_token.json

# Verify it works
contextos status
# Should show: gmail: connected
```

---

## Privacy & Security Model

### What ContextOS stores

| Data type | Where | Encrypted | Deletable |
|-----------|-------|-----------|-----------|
| Document content | ChromaDB chunks | Yes | Yes — `contextos ingest delete <source>` |
| Entity graph | Kuzu database | Yes | Yes — `contextos graph delete <entity>` |
| Processing history | SQLite | No (metadata only) | Yes |
| LLM model weights | Ollama cache (~/.ollama) | No | Yes — `ollama rm model-name` |
| Embedding model | HuggingFace cache | No | Yes |

### What ContextOS never does

- Makes outbound network requests during normal operation
- Sends telemetry or usage data anywhere
- Stores API keys or cloud credentials (Google OAuth tokens stored locally only)
- Logs your query content (only query count is logged for diagnostics)

### Threat model

ContextOS is designed for the following threat:
> "I don't trust cloud AI providers with my professional data."

It is **not** designed for:
- Full disk encryption (use your OS BitLocker/FileVault for that)
- Protection against a malicious admin on your own machine
- Network-level attacks (the API binds to 127.0.0.1 — not accessible from other machines)

For enterprise deployments where the machine is shared, set `API_HOST=127.0.0.1`
(already the default) and consider running under a dedicated OS user account.

---

## Troubleshooting

### "Ollama is not running"

```bash
# Start Ollama manually
ollama serve

# Check if it's running
curl http://localhost:11434/api/tags

# On Linux, check if it's a service
sudo systemctl status ollama
sudo systemctl start ollama
```

### "Model not found"

```bash
# List available models
ollama list

# Pull the required model
ollama pull llama3.2

# Check your .env OLLAMA_MODEL matches an installed model
```

### "Out of memory during inference"

Switch to a smaller model in `.env`:
```env
OLLAMA_MODEL=llama3.2  # 3B, uses ~4 GB RAM
```

Or add swap space (Linux):
```bash
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### "spaCy model not found"

```bash
python -m spacy download en_core_web_sm
python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('OK')"
```

### "ChromaDB error on startup"

If the vector store is corrupt:
```bash
# Backup and reset (you'll need to re-ingest)
mv ~/.contextos/db/chroma ~/.contextos/db/chroma.bak
# Restart the app — it will recreate the collection
```

### "Slow inference"

Normal on CPU — expected speeds:
- 3B model on CPU: 15–25 tokens/second (~30–60 seconds per answer)
- 7B model on CPU: 5–10 tokens/second (~1–2 minutes per answer)
- 7B model on GPU: 30–60 tokens/second (~5–10 seconds per answer)

To check if your GPU is being used:
```bash
# NVIDIA
nvidia-smi

# Apple Silicon — check in Activity Monitor → GPU History
```

### Tests failing

```bash
# Run with verbose output
pytest tests/ -v -s

# Run only fast tests (skip integration tests)
pytest tests/ -v -m "not integration"

# Check if Ollama is needed for a test
# Tests that need Ollama are marked @pytest.mark.integration
```

---

## Roadmap

### v0.1 — Foundation (current)
- [ ] Core storage layer (graph, vectors, metadata)
- [ ] Ingestion pipeline with spaCy NER
- [ ] Basic RAG query engine via Ollama
- [ ] FastAPI REST API
- [ ] Typer CLI
- [ ] Full test suite

### v0.2 — Connectors
- [ ] Local file watcher (PDF, DOCX, TXT, MD)
- [ ] Gmail connector (OAuth2)
- [ ] Google Drive connector
- [ ] Browser history connector (Chrome/Firefox)
- [ ] Whisper meeting transcription

### v0.3 — Features
- [ ] Smart email drafting
- [ ] Meeting brief generator
- [ ] Decision log search
- [ ] React dashboard UI
- [ ] Browser extension (Chrome)

### v0.4 — Polish
- [ ] Performance benchmarks
- [ ] Docker container
- [ ] macOS app bundle
- [ ] Windows installer

### v1.0 — Enterprise
- [ ] Team mode (shared graph, per-user encryption)
- [ ] Admin panel
- [ ] Plugin SDK (WASM)
- [ ] Audit log
- [ ] SSO integration

---

## Contributing

We welcome contributions. Please read `CONTRIBUTING.md` before opening a PR.

Good first issues are tagged with `good-first-issue` in the issue tracker.
Help-wanted issues (no prior context needed) are tagged `help-wanted`.

### Quick contribution checklist

- [ ] Fork the repo and create a feature branch
- [ ] Write code with type hints and docstrings
- [ ] Write or update tests for your change
- [ ] Run `make lint` and `make test` — both must pass
- [ ] Open a PR with a clear description linking the issue

---

## License

Apache 2.0 — see `LICENSE` for the full text.

You can use ContextOS in commercial products, modify it, and distribute it.
You must include the license and copyright notice.
You cannot use the ContextOS name or logo to imply endorsement.

---

## Acknowledgements

ContextOS is built on the shoulders of these open source projects:

- [Ollama](https://ollama.ai) — local LLM serving
- [LangChain](https://langchain.com) — document loading and text splitting
- [ChromaDB](https://trychroma.com) — embedded vector database
- [Kuzu](https://kuzudb.com) — embedded graph database
- [spaCy](https://spacy.io) — industrial-strength NLP
- [Whisper](https://github.com/openai/whisper) — open source speech recognition
- [sentence-transformers](https://sbert.net) — semantic embeddings
- [FastAPI](https://fastapi.tiangolo.com) — modern Python API framework

---

*Built with the belief that your professional knowledge belongs to you.*
