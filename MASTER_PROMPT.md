# ContextOS — Master Build Prompt
# Paste this entire prompt into any AI coding assistant (Claude, Cursor, Copilot, etc.)
# to scaffold the complete base structure of ContextOS.

---

## SYSTEM CONTEXT

You are an expert Python engineer helping me build **ContextOS** — a privacy-first,
on-device AI context engine for knowledge workers. The system captures data from
emails, documents, calendar, browser, and meetings, builds a local knowledge graph
and vector store from that data, and uses a locally running LLM (via Ollama) to
answer questions about the user's professional life — entirely on-device, with zero
cloud dependency.

This is an open source project. Code must be clean, well-commented, modular, and
testable. Every file should have docstrings. Every function should have type hints.

---

## PROJECT IDENTITY

- **Name:** ContextOS
- **Tagline:** Your private AI memory layer — everything you know, instantly searchable
- **License:** Apache 2.0
- **Language:** Python 3.11+
- **Architecture:** Local-first, privacy-first, plugin-extensible
- **Primary users:** Knowledge workers, developers, enterprise teams in regulated industries

---

## TECH STACK (NON-NEGOTIABLE)

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Runtime | Python 3.11+ | Core language |
| LLM runtime | Ollama | Run LLMs locally (no API key needed) |
| LLM model | llama3.2 (default), mistral (fallback) | Local inference |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | Text → vectors |
| Vector DB | ChromaDB | Semantic search over embedded chunks |
| Graph DB | Kuzu | Entity relationship graph (on-device) |
| Metadata DB | SQLite (via sqlitedict) | File tracking, sync state |
| NLP | spaCy (en_core_web_sm) | Named entity recognition |
| Document parsing | LangChain loaders + Apache Tika | Multi-format ingestion |
| API layer | FastAPI + Uvicorn | Local REST API on localhost:8000 |
| CLI | Typer + Rich | Terminal interface |
| Encryption | cryptography (AES-256-GCM) | Data at rest encryption |
| Transcription | Whisper (openai-whisper, base model) | Meeting audio → text |
| Frontend | React 18 + Vite (in /dashboard) | Control panel UI |
| Testing | pytest + pytest-asyncio + httpx | Unit + integration tests |
| Dev tools | black, ruff, mypy, pre-commit | Code quality |

---

## DIRECTORY STRUCTURE TO CREATE

Create the following complete directory and file structure. Every file listed must
be created with real, working, commented code — not placeholders or stubs.

```
contextos/
├── README.md
├── LICENSE                          ← Apache 2.0 text
├── CONTRIBUTING.md
├── .env.example
├── .gitignore
├── pyproject.toml                   ← project metadata + dependencies
├── requirements.txt                 ← pinned dependencies
├── requirements-dev.txt             ← dev/test dependencies
├── Makefile                         ← common dev commands
│
├── core/
│   ├── __init__.py
│   ├── config.py                    ← settings loaded from .env
│   ├── encryption.py                ← AES-256-GCM encrypt/decrypt utilities
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── base.py                  ← BaseConnector abstract class
│   │   ├── extractor.py             ← spaCy entity extraction
│   │   ├── chunker.py               ← text splitting into chunks
│   │   └── pipeline.py              ← orchestrates ingest → extract → store
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── graph.py                 ← Kuzu graph DB wrapper
│   │   ├── vectors.py               ← ChromaDB vector store wrapper
│   │   └── metadata.py              ← SQLite metadata store wrapper
│   │
│   ├── inference/
│   │   ├── __init__.py
│   │   ├── retriever.py             ← hybrid graph + vector retrieval
│   │   ├── prompt_builder.py        ← builds context-aware prompts
│   │   └── engine.py                ← main query engine (RAG loop)
│   │
│   └── api/
│       ├── __init__.py
│       ├── main.py                  ← FastAPI app factory
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── query.py             ← POST /query endpoint
│       │   ├── graph.py             ← GET /graph/* endpoints
│       │   ├── ingest.py            ← POST /ingest endpoints
│       │   └── health.py            ← GET /health endpoint
│       └── models.py                ← Pydantic request/response models
│
├── connectors/
│   ├── __init__.py
│   ├── local_files.py               ← watch local folder, ingest on change
│   ├── gmail.py                     ← Gmail API OAuth2 connector
│   ├── gdrive.py                    ← Google Drive API connector
│   └── browser_history.py           ← parse Chrome/Firefox history SQLite
│
├── features/
│   ├── __init__.py
│   ├── smart_draft.py               ← email drafting in user's voice
│   ├── meeting_brief.py             ← pre-meeting briefing generator
│   ├── decision_log.py              ← searchable decision history
│   └── transcriber.py               ← Whisper audio → text → ingest
│
├── cli/
│   ├── __init__.py
│   └── main.py                      ← Typer CLI app (contextos query, ingest, etc.)
│
├── dashboard/                       ← React frontend (scaffold with Vite)
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       └── components/
│           ├── QueryBox.jsx
│           ├── GraphViewer.jsx
│           └── IngestStatus.jsx
│
└── tests/
    ├── __init__.py
    ├── conftest.py                   ← shared fixtures (temp DB paths, mock data)
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

## DETAILED FILE SPECIFICATIONS

Build each file exactly as specified below.

---

### `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "contextos"
version = "0.1.0"
description = "Privacy-first on-device AI context engine for knowledge workers"
readme = "README.md"
license = { file = "LICENSE" }
requires-python = ">=3.11"
authors = [{ name = "Your Name", email = "you@example.com" }]
keywords = ["ai", "llm", "privacy", "knowledge-graph", "rag", "local-first"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3.11",
]

[project.scripts]
contextos = "cli.main:app"

[tool.black]
line-length = 88
target-version = ["py311"]

[tool.ruff]
line-length = 88
select = ["E", "F", "I", "N", "W"]

[tool.mypy]
python_version = "3.11"
strict = false
ignore_missing_imports = true
```

---

### `requirements.txt`

```
# LLM & Embeddings
ollama==0.3.3
sentence-transformers==3.1.1
openai-whisper==20240930

# Vector & Graph Storage
chromadb==0.5.18
kuzu==0.6.0

# NLP & Document Processing
spacy==3.7.6
langchain==0.3.7
langchain-community==0.3.7
langchain-text-splitters==0.3.2
tika==2.6.0

# API
fastapi==0.115.4
uvicorn[standard]==0.32.0
pydantic==2.9.2
httpx==0.27.2

# CLI
typer==0.12.5
rich==13.9.4

# Storage & Config
sqlitedict==2.1.0
python-dotenv==1.0.1
cryptography==43.0.3

# Google APIs (connectors)
google-auth==2.35.0
google-auth-oauthlib==1.2.1
google-api-python-client==2.149.0
```

---

### `requirements-dev.txt`

```
-r requirements.txt
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-cov==6.0.0
httpx==0.27.2
black==24.10.0
ruff==0.7.4
mypy==1.13.0
pre-commit==4.0.1
```

---

### `.env.example`

```env
# ContextOS Environment Configuration
# Copy this file to .env and fill in your values

# ---- Paths ----
CONTEXTOS_DATA_DIR=~/.contextos/data
CONTEXTOS_DB_DIR=~/.contextos/db
CONTEXTOS_LOG_DIR=~/.contextos/logs

# ---- Encryption ----
# Run: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
CONTEXTOS_ENCRYPTION_KEY=your-generated-key-here

# ---- LLM Settings ----
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_FALLBACK_MODEL=mistral
OLLAMA_TIMEOUT=120

# ---- Embedding Settings ----
EMBEDDING_MODEL=all-MiniLM-L6-v2

# ---- API Settings ----
API_HOST=127.0.0.1
API_PORT=8000
API_RELOAD=true

# ---- Google OAuth (for Gmail / Drive connectors) ----
GOOGLE_CLIENT_SECRETS_FILE=~/.contextos/google_credentials.json
GOOGLE_TOKEN_FILE=~/.contextos/google_token.json

# ---- Feature Flags ----
ENABLE_GMAIL=false
ENABLE_GDRIVE=false
ENABLE_BROWSER_HISTORY=false
ENABLE_WHISPER=false
ENABLE_ENCRYPTION=true
```

---

### `core/config.py`

Build a `Settings` class using `pydantic-settings` or `python-dotenv` that:
- Loads all values from `.env`
- Provides typed attributes for every config key
- Has a `get_db_path(name: str) -> Path` helper that creates the directory if missing
- Has a singleton `settings` instance exported at module level
- Raises a clear error if `CONTEXTOS_ENCRYPTION_KEY` is missing when encryption is enabled

---

### `core/encryption.py`

Build an `Encryptor` class that:
- Uses AES-256-GCM via the `cryptography` library
- Has `encrypt(data: str) -> bytes` and `decrypt(data: bytes) -> str` methods
- Has `encrypt_file(src: Path, dst: Path)` and `decrypt_file(src: Path, dst: Path)` helpers
- Key is derived from `settings.CONTEXTOS_ENCRYPTION_KEY` using PBKDF2
- All operations must handle errors gracefully and raise `EncryptionError` (custom exception)
- Include a `verify_key()` method that round-trips a test string

---

### `core/ingestion/base.py`

Build a `BaseConnector` abstract class with:
- Abstract method `fetch() -> list[dict]` — returns list of raw document dicts
- Each dict must have keys: `id`, `source`, `content`, `metadata` (dict), `created_at`
- Abstract method `validate_config() -> bool` — checks required settings are present
- A `sync()` method that calls fetch, checks against metadata store for already-processed IDs, and passes new items to the pipeline
- Logging built in using Python's `logging` module

---

### `core/ingestion/extractor.py`

Build an `EntityExtractor` class that:
- Loads spaCy `en_core_web_sm` on init
- Has `extract(text: str) -> ExtractedEntities` returning a dataclass with:
  - `people: list[str]`
  - `organizations: list[str]`
  - `dates: list[str]`
  - `locations: list[str]`
  - `topics: list[str]` (noun chunks, max 10)
- Deduplicates and normalizes entity names (strip whitespace, title case people)
- Has `batch_extract(texts: list[str]) -> list[ExtractedEntities]` for efficiency

---

### `core/ingestion/chunker.py`

Build a `TextChunker` class that:
- Uses LangChain's `RecursiveCharacterTextSplitter`
- Default chunk_size=600, chunk_overlap=80
- Has `chunk(text: str, metadata: dict) -> list[Chunk]` where `Chunk` is a dataclass
  with `content`, `metadata`, `chunk_index`, `total_chunks`
- Filters out chunks with fewer than 30 characters
- Adds `chunk_index` and `total_chunks` to each chunk's metadata

---

### `core/storage/graph.py`

Build a `GraphStore` class wrapping Kuzu that:
- Initializes schema on first run (CREATE NODE TABLE for Person, Organization,
  Document, Topic; CREATE REL TABLE for MENTIONED_IN, WORKS_AT, RELATES_TO)
- Has `add_document(doc_id, title, source, date)` method
- Has `add_entity(entity_type, name)` method (upsert — don't duplicate)
- Has `link_entity_to_document(entity_type, name, doc_id)` method
- Has `get_documents_for_person(name: str) -> list[dict]` method
- Has `get_all_people() -> list[str]` method
- Has `get_recent_documents(limit=20) -> list[dict]` method
- Has `search_entities(query: str) -> list[dict]` (fuzzy name match)
- All methods must be wrapped in try/except and log errors

---

### `core/storage/vectors.py`

Build a `VectorStore` class wrapping ChromaDB that:
- Creates a persistent `Chroma` collection named `"contextos_chunks"`
- Uses `HuggingFaceEmbeddings` with model from `settings.EMBEDDING_MODEL`
- Has `add_chunks(chunks: list[Chunk])` method — batches in groups of 100
- Has `search(query: str, k=5) -> list[SearchResult]` where `SearchResult` has
  `content`, `metadata`, `score`
- Has `delete_by_source(source: str)` for re-ingestion
- Has `count() -> int` for diagnostics
- Lazy-initializes the embedding model (don't load on import)

---

### `core/storage/metadata.py`

Build a `MetadataStore` class wrapping SQLite that:
- Tracks processed document IDs to prevent re-ingestion
- Has `mark_processed(doc_id: str, source: str, metadata: dict)`
- Has `is_processed(doc_id: str) -> bool`
- Has `get_all_processed() -> list[dict]`
- Has `get_stats() -> dict` — returns count by source
- Stores everything in `settings.get_db_path("metadata") / "metadata.db"`

---

### `core/inference/retriever.py`

Build a `HybridRetriever` class that:
- Takes `GraphStore` and `VectorStore` as constructor arguments
- Has `retrieve(query: str, k=5) -> RetrievalResult` where `RetrievalResult` has:
  - `semantic_chunks: list[SearchResult]`
  - `graph_facts: list[str]` — human-readable sentences from the graph
  - `mentioned_people: list[str]`
  - `mentioned_docs: list[str]`
- First does entity extraction on the query, then graph lookup for those entities,
  then vector search, then merges and deduplicates
- Has `retrieve_for_person(name: str) -> RetrievalResult` for person-specific queries

---

### `core/inference/prompt_builder.py`

Build a `PromptBuilder` class that:
- Takes a `RetrievalResult` and a raw question string
- Has `build(question: str, retrieval: RetrievalResult) -> str` that constructs
  a structured prompt with clearly labeled sections:
  - `## Your professional context` (graph facts)
  - `## Relevant documents` (semantic chunks with source citations)
  - `## Instructions` (answer only from context, cite sources, be specific)
  - `## Question`
- Has `build_draft_prompt(instruction: str, context: str, style_examples: str) -> str`
  for the smart drafting feature
- Has `build_brief_prompt(meeting_info: dict, history: str) -> str` for meeting briefs
- All prompts are stored as class-level string templates (not hardcoded inline)

---

### `core/inference/engine.py`

Build a `ContextEngine` class that:
- Constructor takes `retriever: HybridRetriever`, `prompt_builder: PromptBuilder`
- Has `query(question: str) -> EngineResponse` where `EngineResponse` has:
  - `answer: str`
  - `sources: list[str]`
  - `model_used: str`
  - `retrieval_time_ms: int`
  - `inference_time_ms: int`
- Calls Ollama via `ollama.chat()` with the built prompt
- Falls back to `settings.OLLAMA_FALLBACK_MODEL` if primary model fails
- Times retrieval and inference separately
- Has `is_ready() -> bool` that checks Ollama is running and model is available
- Logs all queries (without content) for diagnostics

---

### `core/api/main.py`

Build a FastAPI app factory `create_app() -> FastAPI` that:
- Includes all routers from `core/api/routers/`
- Has CORS middleware configured for localhost only
- Has a startup event that initializes the engine and verifies Ollama is running
- Has a shutdown event that cleanly closes DB connections
- Returns 503 with `{"status": "starting"}` if engine is not ready
- Has OpenAPI docs at `/docs` (development only)

---

### `core/api/routers/query.py`

Build a router with:
- `POST /query` — accepts `QueryRequest(question: str)`, returns `QueryResponse`
- `POST /query/stream` — streaming version using `StreamingResponse`
- Both endpoints validate the question is non-empty and under 2000 chars
- Rate limiting: max 10 requests per minute (use a simple in-memory counter)

---

### `core/api/routers/graph.py`

Build a router with:
- `GET /graph/people` — returns list of all people in graph
- `GET /graph/people/{name}/documents` — documents mentioning a person
- `GET /graph/documents` — recent documents (paginated, default limit=20)
- `GET /graph/stats` — counts of nodes and relationships

---

### `core/api/routers/ingest.py`

Build a router with:
- `POST /ingest/text` — accepts raw text + metadata, ingests immediately
- `POST /ingest/file` — accepts file upload (PDF, TXT, DOCX), ingests async
- `GET /ingest/status` — returns metadata store stats

---

### `core/api/routers/health.py`

Build a router with:
- `GET /health` — returns `{status, ollama_running, models_available, vector_count, graph_node_count, uptime_seconds}`
- `GET /health/models` — lists available Ollama models

---

### `connectors/local_files.py`

Build a `LocalFileConnector(BaseConnector)` that:
- Watches a directory (from config) using polling (check every 60 seconds)
- Supports .txt, .md, .pdf, .docx file types
- Uses LangChain loaders for each type
- Generates a stable `doc_id` from file path + modification time
- Skips already-processed files (checks MetadataStore)
- Has a `run_forever()` method for daemon mode

---

### `features/transcriber.py`

Build a `MeetingTranscriber` class that:
- Loads Whisper "base" model on init
- Has `transcribe(audio_path: Path) -> TranscriptionResult` with fields:
  `text`, `segments` (list of timed segments), `language`, `duration_seconds`
- Has `transcribe_and_ingest(audio_path: Path, pipeline: IngestionPipeline)` that
  transcribes then immediately ingests the transcript
- Supports .mp3, .mp4, .wav, .m4a, .webm formats
- Shows a progress indicator using Rich

---

### `cli/main.py`

Build a Typer CLI app with these commands:
- `contextos query "your question"` — queries the engine, prints formatted response
- `contextos ingest path/to/folder` — ingests all supported files in a folder
- `contextos ingest file path/to/file.pdf` — ingests a single file
- `contextos transcribe path/to/meeting.mp3` — transcribes and ingests audio
- `contextos graph people` — lists all people in the graph
- `contextos graph docs` — lists recent documents
- `contextos status` — shows health check output
- `contextos serve` — starts the API server
- Use Rich for all output (tables, progress bars, panels)

---

### `tests/conftest.py`

Build pytest fixtures:
- `tmp_db_dir(tmp_path)` — returns a temp directory for test databases
- `mock_settings(tmp_db_dir)` — returns a Settings object pointing to tmp dirs
- `graph_store(tmp_db_dir)` — initialized GraphStore with test schema
- `vector_store(tmp_db_dir)` — initialized VectorStore
- `metadata_store(tmp_db_dir)` — initialized MetadataStore
- `sample_document()` — returns a dict with id, content, source, metadata
- `sample_entities()` — returns an ExtractedEntities dataclass with test data

---

### `tests/test_encryption.py`

Write tests that verify:
- `encrypt(data)` returns bytes different from the input
- `decrypt(encrypt(data)) == data` for various string inputs
- `decrypt()` raises `EncryptionError` on tampered ciphertext
- `verify_key()` returns True for valid key, raises for invalid

---

### `tests/test_extractor.py`

Write tests that verify:
- "Barack Obama met with Google in New York" extracts "Barack Obama" as a person
- "The meeting is on Monday, January 15th" extracts a date
- Empty string returns empty entity lists
- `batch_extract` returns same results as individual `extract` calls

---

### `tests/test_graph.py`

Write tests that verify:
- `add_document` then `get_recent_documents` returns it
- `add_entity` is idempotent (call twice, get one result)
- `link_entity_to_document` creates a traversable relationship
- `get_documents_for_person` returns correct documents

---

### `tests/test_api.py`

Write async tests (using httpx + pytest-asyncio) that verify:
- `GET /health` returns 200
- `POST /query` with empty question returns 422
- `POST /ingest/text` with valid payload returns 200
- `GET /graph/people` returns a list

---

## CODE QUALITY REQUIREMENTS

Every file must follow these rules:

1. **Type hints on every function signature** — no bare `def foo(x):`
2. **Docstrings on every class and public method** — Google style
3. **Logging** — use `logging.getLogger(__name__)` in every module
4. **Error handling** — never bare `except:`, always catch specific exceptions
5. **No hardcoded strings** — all config comes from `settings`
6. **No print statements** — use `logger.info()` or Rich console
7. **Dataclasses or Pydantic models** for all structured data
8. **Constants at top of file** in SCREAMING_SNAKE_CASE
9. **No circular imports** — the dependency direction is:
   `config → storage → ingestion → inference → api`
10. **Every module must be importable** without side effects

---

## SETUP INSTRUCTIONS TO INCLUDE IN CODE

After generating all files, include a `Makefile` with:

```makefile
install:
    pip install -r requirements.txt
    python -m spacy download en_core_web_sm

install-dev:
    pip install -r requirements-dev.txt
    python -m spacy download en_core_web_sm
    pre-commit install

run-api:
    uvicorn core.api.main:app --host 127.0.0.1 --port 8000 --reload

test:
    pytest tests/ -v --cov=core --cov-report=term-missing

lint:
    ruff check . && black --check .

format:
    black . && ruff check --fix .

check-ollama:
    curl -s http://localhost:11434/api/tags | python3 -m json.tool

pull-model:
    ollama pull llama3.2
    ollama pull all-minilm
```

---

## WHAT TO BUILD FIRST (ORDERED)

Generate files in this exact order so each file can import from the previous:

1. `pyproject.toml`, `requirements.txt`, `.env.example`, `.gitignore`, `Makefile`
2. `core/config.py`
3. `core/encryption.py`
4. `core/storage/metadata.py`
5. `core/storage/graph.py`
6. `core/storage/vectors.py`
7. `core/ingestion/base.py`
8. `core/ingestion/extractor.py`
9. `core/ingestion/chunker.py`
10. `core/ingestion/pipeline.py`
11. `core/inference/retriever.py`
12. `core/inference/prompt_builder.py`
13. `core/inference/engine.py`
14. `core/api/models.py`
15. `core/api/routers/health.py`
16. `core/api/routers/query.py`
17. `core/api/routers/graph.py`
18. `core/api/routers/ingest.py`
19. `core/api/main.py`
20. `connectors/local_files.py`
21. `features/transcriber.py`
22. `cli/main.py`
23. `tests/conftest.py`
24. All test files

---

## FINAL INSTRUCTION

After generating all files:
1. Print a summary table showing every file created and its line count
2. Print the exact commands to run to verify the setup works:
   - Install dependencies
   - Run tests
   - Start the API
   - Make a test query via CLI
3. Point out any OS-specific gotchas (especially for Linux/Mac differences)
4. List any optional enhancements that could be added in Phase 2

Generate all files now. Do not skip any file. Do not use placeholder comments
like "# TODO: implement this". Every function must have a real implementation.
