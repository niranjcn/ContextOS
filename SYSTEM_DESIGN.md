# ContextOS — System Design Interview Prep

> A privacy-first, 100% on-device AI context engine for knowledge workers.

---

## Table of Contents

1. [Problem Statement & Requirements](#1-problem-statement--requirements)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Component Deep Dive](#3-component-deep-dive)
4. [Data Flow](#4-data-flow)
5. [Storage Architecture](#5-storage-architecture)
6. [API Design](#6-api-design)
7. [Privacy & Security Model](#7-privacy--security-model)
8. [Key Design Decisions & Trade-offs](#8-key-design-decisions--trade-offs)
9. [Scaling & Productionization](#9-scaling--productionization)
10. [Failure Modes & Mitigations](#10-failure-modes--mitigations)
11. [Interview Q&A](#11-interview-qa)

---

## 1. Problem Statement & Requirements

### The Problem

Every AI tool today (ChatGPT, Copilot, Gemini) treats you as a stranger at the start of every session. You repeatedly explain the same project context, your working style, past decisions, and relationships. These tools have no persistent memory of who you are or what you know.

In regulated industries (healthcare, finance, legal, government), cloud AI is often blocked by GDPR, HIPAA, or SOC 2 — you cannot send sensitive documents to OpenAI's servers.

### Core Requirements

| Requirement | Type | Rationale |
|-------------|------|-----------|
| 100% on-device processing | Functional | Data never leaves the user's machine |
| Ingest documents (PDF, DOCX, TXT, MD) | Functional | Common knowledge worker file formats |
| Ingest emails, browser history, meetings | Functional | Capture full professional context |
| Natural language query over all ingested data | Functional | RAG: retrieve relevant context, then answer |
| Hybrid search (semantic + graph-based) | Functional | Better answers than vector-only search |
| Entity extraction (people, orgs, topics) | Functional | Automatically link documents by entities |
| Encryption at rest | Non-functional | AES-256-GCM for all stored content |
| Zero telemetry, zero network calls | Non-functional | No analytics, no cloud dependencies |
| REST API + CLI + Web UI | Functional | Multiple interaction modes |
| Runs on consumer hardware (16 GB RAM, CPU) | Non-functional | No GPU required |

### Non-Goals

- Real-time multi-user collaboration (v1.0 aspirational)
- Cloud sync or backup (intentionally excluded)
- Mobile apps
- Real-time document co-editing

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        User Interfaces                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────────┐ │
│  │  CLI     │   │  REST    │   │  React   │   │  Browser Ext.    │ │
│  │ (Typer)  │   │  (FastAPI)│  │(Dashboard)│   │  (Not Started)   │ │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────────┬─────────┘ │
│       │              │              │                   │           │
└───────┼──────────────┼──────────────┼───────────────────┼───────────┘
        │              │              │                   │
        ▼              ▼              ▼                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Features Layer                                │
│  ┌────────────┐  ┌──────────────┐  ┌────────────┐  ┌─────────────┐  │
│  │Smart Draft │  │Meeting Brief │  │Decision Log│  │Transcriber  │  │
│  │(~85%)      │  │(~85%)        │  │(~80%)      │  │(~90%)       │  │
│  └──────┬─────┘  └──────┬───────┘  └─────┬──────┘  └──────┬──────┘  │
│         │               │                │                │         │
└─────────┼───────────────┼────────────────┼────────────────┼─────────┘
          │               │                │                │
          ▼               ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Inference Engine (RAG)                         │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────────┐   │
│  │ HybridRetriever │  │ PromptBuilder  │  │     Ollama (LLM)     │   │
│  │ Graph + Vector  │──│ Context-aware  │──│ Llama 3.2 / Mistral  │   │
│  └────────┬───────┘  │ Prompt constr. │  │ localhost:11434      │   │
│           │          └────────────────┘  └──────────────────────┘   │
│           │                                                         │
└───────────┼─────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Ingestion Pipeline                            │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────────┐ │
│  │ Chunker  │   │Extractor │   │ Pipeline │   │  BaseConnector   │ │
│  │ LangChain│   │ spaCy    │   │Orchestr. │   │  (abstract)      │ │
│  │ 600-char │   │ NER      │   │          │   │  ┌───────────┐   │ │
│  │ + 80 ovlp│   │ entities │   │          │   │  │local_files│   │ │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   │  │gmail      │   │ │
│       │              │              │         │  │gdrive     │   │ │
│       └──────────────┴──────────────┘         │  │browser_hist│  │ │
│                                               │  └───────────┘   │ │
└───────────────────────────────────────────────┴───────────────────┘ │
            │              │              │                            │
            ▼              ▼              ▼                            │
┌───────────────────────────────────────────────────────────────────────┐
│                         Storage Layer                                  │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐   │
│  │ ChromaDB        │  │ Kuzu Graph DB    │  │ SQLite (Metadata)  │   │
│  │ Vector Store    │  │ Knowledge Graph  │  │ Sync state tracker │   │
│  │ 384-dim vectors │  │ Person/Org/Doc   │  │ Dedup, timestamps  │   │
│  │ Cosine similar. │  │ Topic nodes      │  │                    │   │
│  └─────────────────┘  └──────────────────┘  └────────────────────┘   │
│                              │                                        │
│                              ▼                                        │
│                    ┌──────────────────┐                                │
│                    │  Encryption      │                                │
│                    │  AES-256-GCM     │                                │
│                    │  PBKDF2 key der. │                                │
│                    └──────────────────┘                                │
└───────────────────────────────────────────────────────────────────────┘
```

### Why This Architecture

The system follows a **layered pipeline pattern**:

1. **Connectors** → pull data from diverse sources, normalize to a common document schema
2. **Ingestion** → parse, chunk, extract entities, embed, store
3. **Storage** → three specialized DBs (vectors, graph, metadata) each optimized for its query pattern
4. **Inference** → retrieve from all stores, fuse results, construct prompt, generate answer
5. **Features** → higher-level AI tasks that compose the core engine
6. **Interfaces** → CLI, API, Web UI — all thin wrappers over the same core

This separation allows each layer to be tested, swapped, or scaled independently.

---

## 3. Component Deep Dive

### 3.1 Ingestion Pipeline

#### Chunker (`core/ingestion/chunker.py`)

**What it does:** Splits documents into fixed-size chunks for vector embedding.

**Why 600 characters with 80 overlap:**
- Too small (<200 chars): chunks lack semantic context, retrieval quality drops
- Too large (>1000 chars): exceeds most embedding model's max sequence length (all-MiniLM-L6-v2 = 256 tokens ≈ 500-700 chars); also reduces granularity
- 80-char overlap (≈13%): ensures no context is lost at chunk boundaries; topic sentences spanning two chunks are fully captured

**Design choice — LangChain's `RecursiveCharacterTextSplitter`:**
- Splits on paragraph boundaries first, then sentences, then characters — preserves natural text structure
- Better than naive character splitting because it keeps sentences intact

#### Entity Extractor (`core/ingestion/extractor.py`)

**What it does:** Extracts named entities (people, organizations, dates, locations) and noun-phrase topics from document text.

**Why spaCy:**
- Runs entirely on CPU, fast (processes ~10K chars/sec on a laptop)
- Pre-trained `en_core_web_sm` model — no training data or API calls needed
- Industry-standard NER with good precision on person/org/location detection
- Alternative: Stanford NER (heavier), OpenAI NER (cloud-dependent), regex (brittle)

**Why extract entities at ingest time (vs. query time):**
- Graph construction is done once at ingest, then queried at O(1) traversal time
- Query-time entity extraction would add latency to every user query
- Enables relationship linking: "Alice" mentioned in document A and document B → traverse the graph to connect them

#### Pipeline Orchestrator (`core/ingestion/pipeline.py`)

**What it does:** Coordinates the full in-gest flow: validate → check dedup → parse → extract → chunk → embed → store → track.

**Deduplication:**
- SQLite metadata store tracks doc_id + content hash per source
- Before processing, the pipeline checks `is_processed()` — if the same content hash exists for the same source, it's skipped
- Prevents duplicate embeddings and graph nodes when a document hasn't changed

---

### 3.2 Storage Layer

#### ChromaDB — Vector Store (`core/storage/vectors.py`)

**Why ChromaDB (not Pinecone, Weaviate, Qdrant, FAISS):**
- **Embedded, no server** — runs in-process, no Docker container or cloud service needed
- **Persistent** — saves to disk, survives restarts
- **Python-native** — import chromadb, no HTTP client
- **FAISS comparison:** FAISS is faster for pure search but has no built-in persistence, metadata filtering, or document management. ChromaDB wraps FAISS internally with all of that.
- **Pinecone/Qdrant comparison:** cloud services, data leaves machine, costs money

**Collection:** single `contextos_chunks` collection
- Each chunk stored with metadata: `doc_id`, `source`, `title`, `date`, `chunk_index`
- Metadata filtering enables: "find documents from Gmail only" or "documents from last week"

**Embedding model:** `all-MiniLM-L6-v2` (sentence-transformers)
- 384-dimensional vectors — good balance of speed and quality
- Runs on CPU inference in ~100ms per document
- Alternatives: `text-embedding-ada-002` (OpenAI, cloud), `BAAI/bge-large-en` (higher quality but 4x slower)

#### Kuzu — Knowledge Graph (`core/storage/graph.py`)

**Why Kuzu (not Neo4j, ArangoDB, NetworkX):**
- **Embedded** — Kuzu is a columnar, in-process graph DB. No server. No Docker.
- **Cypher queries** — same query language as Neo4j. SQL-like, easy to learn.
- **Fast** — columnar storage optimized for OLAP graph traversal. Sub-millisecond node lookups.
- **Neo4j comparison:** requires a server process, heavier. Overkill for a single-user desktop app.
- **NetworkX comparison:** in-memory only, no persistence. Kuzu persists to disk.
- **ArangoDB comparison:** multi-model (document + graph), but server-based.

**Schema — 4 node types, 4 relationship types:**
```
(Person) -[:MENTIONED_IN]-> (Document)
(Organization) -[:MENTIONED_IN]-> (Document)
(Document) -[:RELATES_TO]-> (Topic)
(Person) -[:WORKS_AT]-> (Organization)
```

**Why this schema:**
- `MENTIONED_IN` — the core relationship. Answers "what documents mention Alice?" and "who is mentioned in this document?"
- `RELATES_TO` — connects documents to topics. Enables "find documents about 'budget'"
- `WORKS_AT` — organizational context. Knows that Alice and Bob are both at Acme Corp, so documents about Acme may involve both

**Why not just use vector search alone?**
- Vector search finds semantically similar chunks, but doesn't understand entity relationships
- Example: "What did Alice say about the budget?" — vector search finds chunks about "budget" and chunks about "Alice", but graph traversal directly links Alice to budget-related documents via entity co-occurrence
- Graph enables multi-hop queries: "Find documents about topics that Alice writes about" → `MATCH (alice:Person {name:"Alice"})-[r:MENTIONED_IN]->(d:Document)-[:RELATES_TO]->(t:Topic) RETURN t.name`

#### SQLite — Metadata Store (`core/storage/metadata.py`)

**What it tracks:**
- `doc_id` (stable hash-based identifier)
- `source` (gmail, local_files, manual, etc.)
- `timestamp` (when it was ingested)
- `content_hash` (SHA256 of the content — for dedup)

**Why SQLite (not a document store, not another graph DB):**
- It's a single-file embedded relational DB — zero setup, zero config
- Perfect for simple key-value lookups: "was this document already processed?"
- Already included in Python's standard library — no extra dependency
- WAL mode for concurrent reads during ingestion

---

### 3.3 Inference Engine

#### Hybrid Retriever (`core/inference/retriever.py`)

**How it works:**

```
User query: "What did Alice decide about the API authentication?"
         │
         ▼
  Step 1: Entity Extraction
  → Extracts "Alice" (person), "API authentication" (topic)
         │
         ▼
  Step 2: Parallel Retrieval
  ┌──────────────────────┐    ┌────────────────────────┐
  │ Graph Traversal       │    │ Vector Search           │
  │ Find docs mentioning  │    │ Embed query → cosine    │
  │ "Alice" AND related   │    │ sim against all chunks  │
  │ to "authentication"   │    │ → top 5 chunks          │
  │ → matching docs       │    └────────────────────────┘
  └──────────────────────┘              │
         │                              │
         └──────────┬───────────────────┘
                    ▼
  Step 3: Merge & Deduplicate
  → Union of results, dedup by doc_id
  → Priority: graph results ranked higher
    (entity-relevant docs > purely semantic)
         │
         ▼
  Step 4: Return top-k context chunks
```

**Why hybrid retrieval matters:**
- Vector search alone: finds semantically similar text, but can miss explicit entity relationships
- Graph alone: only finds structurally connected documents, misses paraphrases and synonyms
- Together: vector search catches "auth approach" when query says "authentication method"; graph catches "Alice was mentioned in the Q3 planning doc" even if the semantic similarity is low

#### Prompt Builder (`core/inference/prompt_builder.py`)

**Three prompt templates:**

| Template | Use Case | Structure |
|----------|----------|-----------|
| General | Most queries | System instructions + graph facts + relevant chunks + question |
| Draft | Smart drafting | Style examples from retrieved docs + instructions + request |
| Brief | Meeting prep | Per-participant context + recent topics + current agenda |

**Why structured prompts matter:**
- LLMs (especially 3B-7B models) need explicit instruction about their role and output format
- Separating "graph facts" from "document chunks" helps the LLM distinguish between factual entity relationships and semantic content
- Without this structure, smaller models hallucinate more and produce rambling answers

#### Engine (`core/inference/engine.py`)

**Ollama integration:**
- REST client to Ollama's API at `localhost:11434/api/generate`
- Streaming via Server-Sent Events for real-time token-by-token output
- Automatic model fallback: if primary model (llama3.2) fails, tries mistral
- Model health check: `GET /api/tags` to list available models

**Why Ollama (not llama.cpp, LM Studio, GPT4All):**
| Factor | Ollama | llama.cpp | LM Studio |
|--------|--------|-----------|-----------|
| Model management | `ollama pull` — automatic | Manual download | Built-in download |
| API | Built-in REST API | Need server wrapper | Built-in |
| GPU acceleration | Automatic (CUDA/Metal) | Manual build flags | Automatic |
| Multi-model | Switch by name | Need separate binaries | Built-in |
| Portability | Same binary, all OS | Compile per platform | Windows/Mac only |

Ollama wins on developer experience — one binary, one command, everything works.

---

### 3.4 Connectors

#### Base Connector Pattern (`core/ingestion/base.py`)

All connectors extend the abstract `BaseConnector`:

```python
class BaseConnector(ABC):
    @abstractmethod
    def fetch(self) -> list[dict]:     # returns list of document dicts
    @abstractmethod
    def validate_config(self) -> bool: # checks if config is valid

    def sync(self):                    # fetch → pipeline.process_batch()
        docs = self.fetch()
        for doc in docs:
            if not metadata.is_processed(doc["id"]):
                pipeline.process_document(doc)
```

Why this pattern:
- Uniform interface across all data sources (email, files, browser, audio)
- `sync()` method handles common dedup + pipeline routing — connectors only implement data fetching
- New connectors can be added by writing one class

#### Local Files (`connectors/local_files.py`)

**How it works:**
1. Recursively scan a directory for supported extensions (.txt, .md, .pdf, .docx)
2. Use PyPDFLoader for PDFs, Docx2txtLoader for DOCX, raw text for TXT/MD
3. `run_forever()` polls every N seconds — watches for new files
4. Content hash computed from file content (not path) — renaming a file won't re-ingest it

**Graceful fallbacks:**
- PDF without text layer → try OCR (not fully implemented)
- Unsupported extension → skip with warning
- Binary file → detect and skip

#### Gmail (`connectors/gmail.py`)

**OAuth2 flow:**
1. User sets `GOOGLE_CLIENT_SECRETS_FILE` in `.env`
2. First time: opens browser for Google consent screen
3. Token saved to `~/.contextos/google_token.json`
4. Token auto-refreshes on expiry
5. Messages parsed: headers (From, To, Subject, Date), body extracted via MIME recursion (prefers plain text over HTML)

**Design challenge:** Gmail API pagination. Each `messages.list` returns up to 100 messages. Must paginate through all to get a complete snapshot.

#### Browser History (`connectors/browser_history.py`)

**How it works:**
- Chrome: reads `%LOCALAPPDATA%\Google\Chrome\User Data\Default\History` (SQLite)
- Firefox: reads `%APPDATA%\Mozilla\Firefox\Profiles\*.default\places.sqlite`
- Copies the file first (to avoid SQLite locking by the browser)
- Extracts: URL, title, visit timestamp, visit count
- Formats as markdown-like entries for the ingestion pipeline

**Why copy before reading:** Both Chrome and Firefox hold write locks on their history databases. Attempting to open the locked file raises `sqlite3.OperationalError: database is locked`.

---

### 3.5 API Layer (`core/api/`)

**FastAPI app factory (`main.py`):**
- CORS middleware (allow dashboard origin)
- Lifespan events: initialize stores (ChromaDB, Kuzu, SQLite) on startup, close on shutdown
- Four routers: health, query, ingest, graph

**Router breakdown:**

| Router | Endpoints | Purpose |
|--------|-----------|---------|
| health | `GET /health`, `GET /health/models` | System status, Ollama availability, vector/graph stats |
| query | `POST /query`, `POST /query/stream`, `POST /query/draft`, `POST /query/brief` | Core Q&A, streaming, feature endpoints |
| ingest | `POST /ingest/text`, `POST /ingest/file`, `GET /ingest/status`, `DELETE /ingest/source/{source}` | Add data, check status, remove source |
| graph | `GET /graph/people`, `GET /graph/organizations`, `GET /graph/people/{name}/documents`, `GET /graph/documents`, `GET /graph/stats` | Knowledge graph exploration |

**Why FastAPI (not Flask, Django, Starlette):**
- Auto-generated OpenAPI docs at `/docs` — zero effort API documentation
- Pydantic models for request/response validation — catches type errors at the boundary
- Async support — important for streaming LLM responses
- Starlette underneath — fast, ASGI-based
- Flask comparison: no native async, no auto-docs, older
- Django comparison: too heavy for a single-user API, opinionated ORM not needed

---

### 3.6 CLI Layer (`cli/main.py`)

**Built with Typer + Rich:**

| Command | Group | Description |
|---------|-------|-------------|
| `query` | — | Ask a question, get answer with sources |
| `ingest` | `file`, `text` | Ingest a file or paste text |
| `transcribe` | — | Transcribe audio with Whisper + auto-ingest |
| `draft` | — | Draft an email in your style |
| `brief` | — | Generate a meeting brief |
| `decisions` | — | Search past decisions |
| `connect` | `gmail`, `gdrive` | OAuth authentication flow |
| `sync` | `gmail`, `gdrive`, `files`, `browser`, `all` | Run a connector's fetch + pipeline |
| `status` | — | Full system health check |
| `serve` | — | Start the API server |
| `graph` | `people`, `docs`, `stats` | Browse the knowledge graph |

**Why Typer + Rich (not Click, argparse):**
- Typer uses type hints to auto-generate CLI arguments — no boilerplate
- Rich provides tables, panels, progress spinners, colored output
- Click comparison: more verbose, requires explicit parameter decorators
- argparse: too low-level, no auto-help generation

---

## 4. Data Flow

### 4.1 Ingestion Flow (Detailed)

```
User action: contextos ingest file report.pdf
                    │
                    ▼
CLI calls: pipeline.ingest_file("report.pdf")
                    │
                    ▼
Pipeline.ingest_file():
  ┌─────────────────────────────────────────────┐
  │ 1. Read file bytes                          │
  │ 2. Compute content_hash = sha256(bytes)     │
  │ 3. Detect file type by extension             │
  │ 4. Extract text:                             │
  │    - .txt / .md → decode as UTF-8           │
  │    - .pdf → PyPDFLoader                     │
  │    - .docx → Docx2txtLoader                 │
  │ 5. Generate doc_id = hash(source + filename) │
  └─────────────────────────────────────────────┘
                    │
                    ▼
  metadata.is_processed(doc_id, content_hash)?
                    │
          ┌─────────┴─────────┐
          │ YES               │ NO
          ▼                   ▼
       Skip              pipeline.process_document(text, metadata)
          │                   │
          │      ┌────────────┼────────────┐
          │      ▼            ▼            ▼
          │  extractor    chunker      encrypt
          │  .extract()   .chunk()     .encrypt_file()
          │      │            │            │
          │      ▼            ▼            │
          │  Entities     Chunks          │
          │  (spaCy NER)  (600-char)      │
          │      │            │            │
          │      ▼            ▼            │
          │  graph        vectors          │
          │  .add_entity  .add_chunks ─────┘
          │  .link_entity (encrypted)
          │      │            │
          └──────┴────────────┘
                    │
                    ▼
          metadata.mark_processed(doc_id)
                    │
                    ▼
              Return: doc_id, chunk_count, entities
```

### 4.2 Query Flow (Detailed)

```
User: "What did Alice decide about the API auth?"
                    │
                    ▼
Engine.query("What did Alice decide...")
                    │
                    ▼
Step 1 — Extract entities from query:
  extractor.extract("What did Alice decide about the API auth?")
  → people: ["Alice"]
  → topics: ["API auth", "authentication"]
                    │
                    ▼
Step 2a — Graph traversal (parallel):
  MATCH (p:Person {name:"Alice"})-[:MENTIONED_IN]->(d:Document)
  WHERE d.date > last_30_days
  RETURN d.doc_id, d.title, d.date
  → returns set of doc_ids mentioning Alice

  OR: MATCH (d:Document)-[:RELATES_TO]->(t:Topic)
  WHERE t.name CONTAINS "authentication"
  RETURN d.doc_id, d.title, d.date
  → returns set of doc_ids related to auth
                    │
                    ▼
Step 2b — Vector search (parallel):
  Embed query → 384-dim vector
  ChromaDB: cosine_similarity(query_vector, all_chunk_vectors)
  → top 5 most semantically similar chunks
                    │
                    ▼
Step 3 — Merge results:
  graph_docs = {doc_a, doc_b, doc_c}   (from graph traversal)
  vector_chunks = [chunk_x, chunk_y, ...]  (from vector search)
  
  priority_result = []
  # Graph docs first (entity relevance)
  for chunk in vector_chunks:
    if chunk.doc_id in graph_docs:
      priority_result.append(chunk)
  # Then the rest
  for chunk in vector_chunks:
    if chunk.doc_id not in graph_docs:
      priority_result.append(chunk)
                    │
                    ▼
Step 4 — Build prompt:
  prompt = prompt_builder.build(
    question="What did Alice decide about the API auth?",
    context_chunks=priority_result[:MAX_TOKENS],
    graph_facts="Alice is mentioned in 3 documents: ..."
  )
                    │
                    ▼
Step 5 — Call Ollama:
  POST http://localhost:11434/api/generate
  {
    "model": "llama3.2",
    "prompt": prompt,
    "stream": false,
    "options": {"temperature": 0.3}
  }
                    │
                    ▼
Step 6 — Parse response:
  Extract answer text from Ollama response
  Map source citations back to original doc_ids
  Return: EngineResponse(
    answer="Based on the Q3 planning doc...",
    sources=["Q3_planning.pdf", "email_thread_45"],
    model="llama3.2",
    retrieval_time_ms=45,
    inference_time_ms=3200
  )
```

---

## 5. Storage Architecture

### Three Databases, Three Purposes

```
                    ┌─────────────────────────────┐
                    │     Why Three Databases?     │
                    ├─────────────────────────────┤
                    │ No single DB excels at all   │
                    │ three query patterns:        │
                    │                             │
                    │ ChromaDB: semantic similarity│
                    │ Kuzu: graph traversal (hops) │
                    │ SQLite: simple key-value     │
                    └─────────────────────────────┘
```

| Feature | ChromaDB | Kuzu | SQLite |
|---------|----------|------|--------|
| **Type** | Vector DB | Graph DB | Relational DB |
| **Query pattern** | "Find similar" | "Traverse relationships" | "Find by key" |
| **Access pattern** | k-NN search | Cypher MATCH | SELECT WHERE |
| **Data** | 384-dim embedding vectors | Nodes + edges | Rows in a table |
| **Size** | ~KBs per chunk | ~100s bytes per node/edge | ~50 bytes per row |
| **Persistence** | Directory on disk | Directory on disk | Single .db file |
| **Startup** | Load from disk | Load from disk | Open file |
| **Backup** | Copy directory | Copy directory | Copy file |

### Why Not a Single Database?

- **Vector databases** (ChromaDB, Pinecone) don't do graph traversal natively
- **Graph databases** (Neo4j, Kuzu) don't do vector similarity search
- **Relational databases** (PostgreSQL with pgvector) can do both, but:
  - pgvector uses IVFFlat indexing — less accurate than ChromaDB's HNSW
  - Requires running a PostgreSQL server — adds complexity for a desktop app
  - pgvector doesn't handle document chunk management (deletion, metadata filtering) as cleanly

The trade-off: three DBs means more code and more start-up time. The benefit: each DB is best-in-class for its specific query pattern, and all three are embedded (no servers).

### Encryption Layer

All stored content passes through AES-256-GCM encryption before hitting disk:

```
┌──────────┐     ┌──────────────┐     ┌──────────┐
│ Raw data │────→│ Encrypt()    │────→│ Storage  │
│ (chunks, │     │ AES-256-GCM  │     │ (disk)   │
│ entities)│     │ PBKDF2 key   │     │          │
└──────────┘     │ 100K iters   │     └──────────┘
                 └──────────────┘
```

Why AES-256-GCM:
- AES is hardware-accelerated on modern CPUs (AES-NI instructions) — fast
- GCM mode provides authenticated encryption (detects tampering)
- PBKDF2 with 100K iterations makes brute-force key derivation expensive
- The encryption key lives only in `.env` — never sent over a network

---

## 6. API Design

### Design Principles

1. **Uniform response format** — all endpoints return JSON with consistent error structure
2. **Idempotent where possible** — same ingest request produces same result (via content hashing)
3. **Streaming for long operations** — query streaming via SSE so the user sees tokens as they're generated
4. **Self-documenting** — FastAPI generates OpenAPI spec, interactive Swagger UI at `/docs`

### Key API Decisions

**`POST /query` vs `POST /query/stream`:**
- The non-streaming endpoint is simpler for programmatic clients (curl, scripting)
- The streaming endpoint uses Server-Sent Events for the dashboard — tokens appear as they're generated, perceived latency is much lower

**`DELETE /ingest/source/{source}`:**
- Allows removing all data from a specific source (e.g., revoke Gmail access without losing local files)
- Cascades: deletes from ChromaDB, Kuzu, and SQLite metadata

**Rate limiting in `POST /query`:**
- In-memory token bucket: 10 queries per minute per client IP
- Prevents runaway loops if a client accidentally spams the API
- Soft limit — returns `429 Too Many Requests` with a `Retry-After` header

---

## 7. Privacy & Security Model

### Threat Model

**Designed for:**
> "I don't trust cloud AI providers with my professional data."

**Not designed for:**
- Full disk encryption (use BitLocker/FileVault)
- Protection against malicious admin on the same machine
- Network-level attacks (API binds to 127.0.0.1)

### Data Flow Guarantees

```
[Your Machine] ←──────────────────────────────────→ [Internet]
     │                                                     
     │  Outbound:                                          
     │    • Ollama model download (one-time)               
     │    • spaCy model download (one-time)                
     │    • sentence-transformers model download (one-time)
     │                                                     
     │  Never outbound:                                    
     │    • Your documents                                 
     │    • Your queries                                   
     │    • Your embeddings                                
     │    • Your knowledge graph                           
     │    • Telemetry / analytics                          
     │                                                     
     │  Optional outbound:                                 
     │    • Gmail/Drive API (if enabled)                   
     │    → But data is fetched to your machine,           
     │      processed locally, never re-sent               
```

### Encryption at Rest

| Data | Encrypted? | Algorithm | Key Location |
|------|-----------|-----------|-------------|
| Document chunks (ChromaDB) | Yes | AES-256-GCM | `.env` file |
| Knowledge graph (Kuzu) | Yes | AES-256-GCM | `.env` file |
| Metadata (SQLite) | No — doc_ids only | — | — |
| LLM model weights | No — binary blobs | — | `~/.ollama/` |
| Google OAuth tokens | No — stored as JSON | — | `~/.contextos/` |

Why is metadata not encrypted? It stores only doc_ids, content hashes, and timestamps — no actual document content. Encrypting it would prevent efficient `SELECT` queries.

### Audit & Transparency

- No telemetry, no analytics, no crash reporting
- Query content is never logged — only query count (for diagnostics)
- All processing happens in-memory, results discarded after delivery

---

## 8. Key Design Decisions & Trade-offs

### Decision 1: On-Device vs. Cloud

| Factor | On-Device (ContextOS) | Cloud (ChatGPT + RAG) |
|--------|----------------------|----------------------|
| Privacy | Data never leaves your machine | Data processed on third-party servers |
| Cost | Free (your electricity) | Pay per token / API call |
| Model quality | 3B-8B models (good but not SOTA) | GPT-4 / Claude (best-in-class) |
| Speed | CPU: 5-20 tok/s; GPU: 30-60 tok/s | Instant (datacenter GPUs) |
| Offline capability | Fully offline after model download | Requires internet |
| Maintenance | User manages Ollama, models, storage | Zero maintenance |

**Trade-off accepted:** Lower model quality for complete privacy. The hypothesis is that for knowledge-retrieval tasks (finding specific information in your documents), a 7B model with perfect context retrieval beats GPT-4 without context.

### Decision 2: Embedded DBs vs. Server DBs

| DB Type | Embedded (ContextOS) | Server (Enterprise) |
|---------|---------------------|-------------------|
| Setup | pip install, done | Docker, config, networking |
| Resource usage | Shares process memory | Separate process, overhead |
| Performance | No network hop (in-memory) | Network latency per query |
| Scalability | Single process, single machine | Clusters, replication |
| Backup | Copy a directory | Snapshot, replication, WAL archiving |

**Trade-off accepted:** No horizontal scalability. ContextOS is designed for a single user on a single machine. Embedded DBs are the right choice: zero ops overhead, best performance for a desktop app.

### Decision 3: Hybrid (Graph + Vector) vs. Vector-Only Retrieval

| Aspect | Hybrid | Vector-Only |
|--------|--------|-------------|
| Entity-aware | Yes — "Alice mentioned in X doc" | No — only semantic similarity |
| Multi-hop queries | Yes — "docs about topics Alice writes" | No — single similarity pass |
| Cold-start quality | Good — entities extracted at ingest | Poor — need many chunks for similarity |
| Complexity | Two DBs, two queries, merge logic | One DB, one query |
| Latency | ~100ms (parallel graph + vector) | ~50ms |

**Trade-off accepted:** Double the retrieval complexity for significantly better answers on entity-specific queries. The parallel query pattern means latency only increases by ~50ms.

### Decision 4: spaCy NER at Ingest vs. LLM at Query Time

| Factor | spaCy at Ingest | LLM at Query Time |
|--------|----------------|-------------------|
| Speed | 10ms per document | 2-5 seconds per query |
| Cost | One-time CPU cost | Added to every query latency |
| Accuracy | Good for standard entities (person, org) | Better for complex/ambiguous entities |
| Offline | Fully offline | Requires LLM to be running |

**Trade-off accepted:** spaCy may miss some nuanced entities, but entity extraction at ingest time adds zero query latency. The LLM can still re-extract at query time if needed — the system uses both (graph entities from spaCy + any entities the LLM extracts from the query).

### Decision 5: Ollama vs. Other LLM Runtimes

| Factor | Ollama | llama.cpp | GPT4All | LM Studio |
|--------|--------|-----------|---------|-----------|
| REST API | Built-in | Manual wrapper | Built-in | Built-in |
| Model mgmt | `ollama pull` | Download manually | Built-in download | Built-in |
| GPU | Auto (CUDA/Metal) | Manual build flags | Auto | Auto |
| Embeddings | No native endpoint | Need separate setup | Limited | No |
| Cross-platform | ✓ | ✓ (compile per OS) | ✓ | Win/Mac only |

**Why Ollama won:** One binary, one command, everything works. It handles model downloading, GPU acceleration, and API serving — eliminating three potential failure points. The trade-off: less control over inference parameters than raw llama.cpp.

### Decision 6: Chunk Size (600 chars)

```
Impact of chunk size on retrieval quality:
     │
     │
 0.8 │                          ● (600 chars — sweet spot)
     │                        ↗
 0.7 │                      ↗
  F  │                    ↗
  1  │                  ↗
  S  │                ↗
  c  │              ↗
  o  │            ↗
  r  │          ↗                      ● (1200 chars — too much noise)
  e  │        ● ← 200 chars
     │      ↗    (too little context)
     │    ↗
     │  ↗
     │ ●
     └──────────────────────────────────────
       0    400   800   1200   1600   2000
                    Chunk size (chars)
```

- <300 chars: chunks lack enough context for meaningful answers
- 300-800 chars: sweet spot (all-MiniLM-L6-v2 max = 256 tokens ≈ 500-700 chars)
- >1000 chars: dilutes relevance; multiple topics in one chunk

### Decision 7: Temperature = 0.3

- Lower temperature (0.1-0.3): more deterministic, less creative — preferred for factual QA
- Higher temperature (0.7-1.0): more creative — better for drafting but risks hallucination
- For a RAG system, low temperature is critical: you want the LLM to stick to retrieved facts, not invent

---

## 9. Scaling & Productionization

### Current Architecture Limits

| Constraint | Why | Impact |
|-----------|-----|--------|
| Single-process Python | GIL, single thread for CPU work | Can't parallelize multiple queries |
| Embedded DBs (ChromaDB, Kuzu) | Single-process file access | Can't run multiple API replicas sharing the same DB files |
| Single-user design | No auth, no sessions | Any process on the machine can query |
| Ollama single instance | Ollama serves one model at a time | No model parallelism |

### Scaling Path for Enterprise

```
            ┌───────────────────┐
            │   Load Balancer   │
            │   (ALB / nginx)   │
            └────────┬──────────┘
                     │
         ┌───────────┼───────────┐
         ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │ API     │ │ API     │ │ API     │ ← Stateless, scale horizontally
    │ Pod 1   │ │ Pod 2   │ │ Pod 3   │
    └────┬────┘ └────┬────┘ └────┬────┘
         │           │           │
         └───────────┼───────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
    ┌───────────────┐    ┌───────────────┐
    │  Ollama       │    │  Ollama       │ ← Stateful, behind service
    │  (GPU node)   │    │  (GPU node)   │
    └───────────────┘    └───────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
    ┌───────────────┐    ┌───────────────┐
    │  ChromaDB     │    │  Kuzu (repl.) │ ← Stateful, persistent volumes
    │  (replicated) │    │               │
    └───────────────┘    └───────────────┘
```

**What changes for multi-user:**
- SQLite → PostgreSQL (for concurrent writes in metadata store)
- ChromaDB → Qdrant / Weaviate (server-based vector DB with replication)
- Kuzu → Neo4j (server-based graph DB with clustering)
- Per-user encryption key management (AWS KMS / HashiCorp Vault)
- Authentication middleware (OIDC, JWT)
- Rate limiting per user, not per IP

---

## 10. Failure Modes & Mitigations

| Failure | Impact | Mitigation |
|---------|--------|------------|
| Ollama not running | All queries fail | `health` endpoint checks Ollama; CLI shows clear error; `make run-ollama` |
| Model not pulled | Inference fails | Engine falls back to `OLLAMA_FALLBACK_MODEL`; health endpoint shows available models |
| ChromaDB corruption | Vector search fails | Metadata store still has doc_ids; user can delete and re-ingest |
| Kuzu DB corruption | Graph traversal fails | Retriever degrades to vector-only search; user can delete and re-ingest |
| Out of memory during inference | Process crash | Smaller model fallback; swap file recommendation in docs |
| Google API quota exceeded | Gmail/Drive sync fails | Connector returns error, pipeline skips failed batch; retry on next sync |
| OAuth token expired | Gmail/Drive auth fails | Auto-refresh built into Google auth library; if refresh fails, user re-authenticates |
| File locked by another process | Local file read fails | Try-except with clear error message; skip and continue |
| Disk full | Ingestion fails | Check disk space before ingest; clear error message; guide to free space |

---

## 11. Interview Q&A

### Q: Why not use a single vector database like Pinecone or Weaviate?

**A:** Those are cloud services — they violate the core requirement of data never leaving the machine. ChromaDB is embedded, Python-native, and persists to local disk. For a desktop app, an embedded database is the right choice: zero ops, no network calls, instant startup.

### Q: Why both a vector DB and a graph DB? Isn't one enough?

**A:** They solve different problems. Vector search finds semantically similar text — great for "find me more like this." Graph traversal follows entity relationships — great for "find me everything about Alice." Together, they give better answers than either alone. For example: "What did Alice decide about the budget?" — vector search finds chunks about "budget" and "Alice" semantically; the graph directly links Alice to budget-related documents via entity co-occurrence.

### Q: How does deduplication work?

**A:** Each document gets a stable `doc_id` (hash of source + identifier) and a `content_hash` (SHA256 of content). Before processing, we check SQLite: "have we seen this content_hash for this source before?" If yes, skip. This means re-running a connector only ingests new/changed documents.

### Q: How would you scale this for 1000 users in an enterprise?

**A:** Three things change:
1. **DBs:** Embedded ChromaDB/Kuzu/SQLite → server-based Qdrant/Neo4j/PostgreSQL for concurrent access
2. **Auth:** Add OIDC/JWT middleware — currently the API has no auth
3. **Deployment:** Single process → Docker Compose with multiple replicas behind a reverse proxy
The core architecture (hybrid retrieval, ingestion pipeline, prompt building) stays the same.

### Q: What's the trickiest bug you encountered?

**A:** In `graph.py:241`, the LIMIT clause f-string is broken due to string literal concatenation — `"ORDER BY d.date DESC LIMIT {limit}"` lacks the `f` prefix on the second literal. At runtime, Cypher receives literal `{limit}` instead of the value. It's a subtle Python pitfall: adjacent string literals concatenate, but only the first one had `f`. Easy to miss in review.

### Q: Why did you choose Kuzu over Neo4j?

**A:** Kuzu is embedded (in-process, no server), Neo4j requires running a server process. For a desktop app targeting a single user, Kuzu's columnar storage gives sub-millisecond graph traversal without the operational overhead of managing a Neo4j instance. Kuzu also speaks Cypher, so migrating to Neo4j later requires minimal query changes.

### Q: How do you ensure the LLM doesn't hallucinate?

**A:** Three defenses:
1. **Low temperature (0.3)** — makes the model less creative, more likely to stick to retrieved facts
2. **Prompt structure** — explicitly separates "graph facts" from "document chunks" so the model knows what's factual vs. what's retrieved
3. **Source citations** — every answer includes document references. If the model hallucinates, the user can check the source.

These don't eliminate hallucination (no system can), but they make it detectable and reduce frequency.

### Q: Why Python and not Rust/Go for performance?

**A:** The bottleneck is LLM inference (seconds per query), not Python code (milliseconds). Python's ecosystem for AI/ML (spaCy, sentence-transformers, ChromaDB, Kuzu bindings) is unmatched. Rewriting in Rust would save ~50ms per request — imperceptible next to 3-10 second inference times.

### Q: What would you do differently if starting over?

**A:** Three things:
1. **Unified storage abstraction** — instead of three separate stores (ChromaDB, Kuzu, SQLite), wrap them behind a single `StorageBackend` interface with common operations (add, search, delete). Currently each store has its own API.
2. **Connector auto-registration** — connectors should auto-register themselves via a plugin pattern rather than being manually wired in the pipeline
3. **Event-driven architecture** — instead of polling file watchers, use filesystem events (watchdog/inotify) for real-time ingestion
