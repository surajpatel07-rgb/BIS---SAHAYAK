# BIS Buddy

**Your AI Assistant for Indian Standards & BIS Services**

BIS Buddy is a full-stack, retrieval-augmented-generation (RAG) web application that
helps **industries, manufacturers and consumers** understand Indian Standards (IS),
BIS certification requirements, compliance procedures and BIS services through a
conversational AI assistant.

> ⚠️ **Sample data notice**: the bundled development dataset (`data/sample_documents/`)
> consists of **synthetic, SAMPLE-labelled documents** created for the hackathon demo.
> They are **not official BIS documents**. The system is designed so admins can upload
> real, official BIS PDFs (with source URLs) for production use.

---

## 1. Project overview

| Capability | How it works |
|---|---|
| Grounded Q&A | RAG over ingested BIS documents; answers cite the exact document + page |
| Citations | Clickable chips and source cards; open the PDF at the cited page |
| Document ingestion | Admin uploads PDF → extract → clean → chunk → embed → index |
| Semantic search | Vector search over chunks + reranking, at `/documents` |
| User modes | Consumer vs Industry — the LLM system prompt adapts tone and focus |
| Conversations | Persistent history, follow-up questions with context |
| Streaming | Server-sent events: "BIS Buddy is thinking…" then token-by-token answer |
| Voice input | Browser Web Speech API (gracefully disabled where unsupported) |
| Admin | Upload, delete, re-index, stats cards, failure visibility |
| Auth | JWT login/register, bcrypt hashing, admin-only management routes |
| Feedback | 👍/👎 + comment per assistant message |

**Grounding guarantee** — the assistant is contractually forbidden (system prompt +
code) from inventing standard numbers, fees, or requirements. If retrieval finds no
supporting content, it replies:
*"I could not find sufficient information in the indexed BIS documents to answer this
reliably."* — and the offline fallback provider enforces the same rule deterministically.

---

## 2. Architecture

### Query flow (chat)

```
User
 ↓
React Frontend (Vite + TypeScript + Tailwind)
 ↓  (JWT via Authorization header, SSE for streaming)
FastAPI Backend
 ↓
Query Processing (mode detection, history assembly)
 ↓
Embedding Model  ──►  Gemini gemini-embedding-001  (or local hash fallback)
 ↓
Vector Database  ──►  pgvector on PostgreSQL (or SQLite + JSON vectors in dev)
 ↓
Retriever (top-K cosine + hybrid keyword blend)
 ↓
Reranker (term coverage + phrase/standard-number boosts)
 ↓
Relevant BIS Document Chunks (top 5, with page + section metadata)
 ↓
Gemini LLM (gemini-3.1-flash-lite, grounded system prompt)   [local extractive fallback if no key]
 ↓
Answer + Citations ([1] [2] markers resolved to real sources)
 ↓
Frontend (streamed answer + clickable source cards)
```

### Ingestion flow (documents)

```
BIS PDF
 ↓
Upload (admin only, validated: extension, %PDF magic bytes, size ≤ 25 MB)
 ↓
Stored to disk (safe randomised filename, path-traversal guarded)
 ↓
PDF Extraction (PyMuPDF, per-page text with char-offset → page mapping)
 ↓
Cleaning (de-hyphenation, whitespace normalisation)
 ↓
Chunking (section-aware headings, configurable size/overlap)
 ↓
Metadata extraction (standard number, year, page numbers, section titles)
 ↓
Embeddings (provider abstraction: Gemini | local hash)
 ↓
PostgreSQL + pgvector (or SQLite JSON vectors in dev)
 ↓
Status: uploaded → processing → extracting → chunking → embedding → indexed | failed
```

Every stage updates `Document.status`; failures are stored on the row and surfaced in
the admin UI — ingestion never pretends to succeed.

---

## 3. Features

- 🔐 **Auth** — register/login/logout, bcrypt + JWT, `user` and `admin` roles
- 💬 **Grounded chat** — RAG answers with inline `[n]` citation chips
- 📄 **Citations** — document name, standard number, page, section, relevance score; click to open the PDF at the page
- 📡 **Streaming** — SSE `/api/chat/stream` with thinking indicator
- 👥 **Modes** — Consumer / Industry switch changes retrieval prompt + UI copy
- 🔎 **Search** — metadata search (number/title/keyword) *and* semantic chunk-level search
- 🗂 **Conversations** — persistent, searchable history; open any past chat
- 🎙 **Voice** — Web Speech API input (Chrome/Edge); button auto-disables elsewhere
- 🛠 **Admin dashboard** — stats cards, upload with metadata, re-index, delete, failure details
- 👍 **Feedback** — thumbs up/down + comments, stored per message
- 🧪 **Tests** — 19 backend tests incl. full offline RAG integration test
- 🐳 **Docker** — `docker compose up` for Postgres+pgvector, backend, frontend

---

## 4. Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query, lucide-react |
| Backend | Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2, Uvicorn |
| Database | PostgreSQL 16 + **pgvector** (prod) / SQLite (zero-setup dev) |
| LLM | **Google Gemini** (`gemini-3.1-flash-lite`) via `google-genai` |
| Embeddings | Gemini `gemini-embedding-001` (or deterministic local hash provider) |
| PDF | PyMuPDF |
| Auth | python-jose (JWT), bcrypt |
| Tests | pytest + FastAPI TestClient |

---

## 5. Folder structure

```
bis-buddy/
├── backend/
│   ├── app/
│   │   ├── api/                 # FastAPI routers
│   │   │   ├── auth.py          # register / login / me
│   │   │   ├── chat.py          # /api/chat, /api/chat/stream, conversations
│   │   │   ├── documents.py     # upload, list, detail, file, delete, reindex
│   │   │   ├── search.py        # semantic + metadata search
│   │   │   └── misc.py          # feedback, admin stats, health, config
│   │   ├── database/
│   │   │   ├── base.py          # engine/session, SQLite URL resolution
│   │   │   └── migrations.py    # idempotent migration runner
│   │   ├── ingestion/
│   │   │   ├── pdf.py           # PyMuPDF extraction with page tracking
│   │   │   └── service.py       # validate → extract → clean → chunk → embed → index
│   │   ├── models/models.py     # User, Conversation, Message, Document, DocumentChunk, Feedback
│   │   ├── rag/
│   │   │   ├── embeddings.py    # provider abstraction (Gemini | hash)
│   │   │   ├── chunking.py      # configurable section-aware chunker
│   │   │   ├── vector_store.py  # store abstraction (SQL | pgvector-ready)
│   │   │   ├── reranker.py      # term-coverage + boosts reranking
│   │   │   ├── retrieval.py     # embed → search → rerank → prompt builder
│   │   │   └── llm.py           # Gemini provider + grounded offline fallback
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── config.py            # pydantic-settings (env-driven)
│   │   ├── dependencies.py      # JWT current-user, admin guard
│   │   ├── security.py          # bcrypt + JWT helpers
│   │   ├── logging_config.py    # structured logging
│   │   └── main.py              # FastAPI app factory, CORS, lifespan
│   ├── tests/                   # pytest suite (health, auth, chunking, RAG e2e)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── components/Layout.tsx    # sidebar: modes, chats, nav
│   │   ├── context/AuthContext.tsx  # auth + mode state
│   │   ├── pages/                   # Landing, Login, Register, Chat, Documents,
│   │   │                            # DocumentDetail, Admin, Settings
│   │   ├── services/api.ts          # typed API client + SSE streaming
│   │   ├── App.tsx                  # routes with auth/admin guards
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts               # dev proxy → :8000
│   ├── Dockerfile + nginx.conf
│   └── tailwind.config.js
├── data/
│   ├── sample_documents/            # SAMPLE (synthetic) BIS-style PDFs
│   └── uploads/                     # ingested file storage
├── scripts/
│   ├── build_sample_pdfs.py         # generates the sample PDFs
│   └── seed_data.py                 # seeds users + ingests sample docs
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## 6. Environment variables

Copy `.env.example` → `.env` (project root; also read from `backend/.env`):

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | dev value | JWT signing — **change in production** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` | Token lifetime (7 days) |
| `DATABASE_URL` | `sqlite:///./data/bisbuddy.db` | Any SQLAlchemy URL; Postgres example in file |
| `GEMINI_API_KEY` | *(empty)* | **Required for generative answers.** Empty ⇒ offline fallback mode |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` | Chat model |
| `GEMINI_MAX_OUTPUT_TOKENS` | `8192` | Generation budget — thinking models (gemini-3.x) reason within it |
| `EMBEDDING_PROVIDER` | `hash` | `gemini` or `hash` (offline deterministic) |
| `GEMINI_EMBEDDING_MODEL` | `models/gemini-embedding-001` | Embedding model |
| `EMBEDDING_DIM` | `768` | Vector dimension |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `900` / `150` | Chunking configuration |
| `RETRIEVAL_TOP_K` / `RERANK_TOP_N` | `12` / `5` | Retrieval configuration |
| `MIN_RELEVANCE_SCORE` | `0.08` | Retrieval floor |
| `RETRIEVAL_MODE` | `hybrid` | `lexical` or `hybrid` (vector+keyword) |
| `MAX_UPLOAD_MB` | `25` | PDF upload limit |
| `CORS_ORIGINS` | localhost dev URLs | Comma-separated allowed origins |
| `LOG_LEVEL` | `INFO` | Backend logging |
| `DATA_DIR` | `./data` | Uploads + SQLite location |

API keys live **only** in `.env` on the backend. The frontend never sees them; it talks
exclusively to your FastAPI server.

---

## 7. Installation (non-Docker, fastest way to run)

Prerequisites: **Python 3.11+** and **Node.js 18+**.

```bash
# 1) Backend deps
pip install -r backend/requirements.txt

# 2) Frontend deps
cd frontend && npm install && cd ..

# 3) Configure environment (optional for offline dev; needed for Gemini)
cp .env.example .env
#   → put your GEMINI_API_KEY inside, and/or set EMBEDDING_PROVIDER=gemini

# 4) Create SAMPLE PDFs and seed demo users + documents
python scripts/build_sample_pdfs.py
python scripts/seed_data.py
```

`seed_data.py` creates:

| Account | Password | Role |
|---|---|---|
| `admin@bisbuddy.in` | `Admin@12345` | admin |
| `demo@bisbuddy.in` | `Demo@12345` | user |

…and ingests all four sample documents end-to-end through the real pipeline.

### Enabling Gemini (embeddings + generative answers) — full walkthrough in [`GEMINI_SETUP.md`](GEMINI_SETUP.md)

The app is fully functional **without** any API key (offline fallback mode), but adding
a free `GEMINI_API_KEY` upgrades retrieval to true semantic search and answers to
generative, streamed Gemini output:

```bash
cp .env.example .env
#   → set GEMINI_API_KEY=... and EMBEDDING_PROVIDER=gemini (see GEMINI_SETUP.md)

python scripts/check_gemini.py          # 1) verify the key works for chat + embeddings
python scripts/reindex_all.py           # 2) re-embed the corpus with Gemini vectors
                                        #    (--dry-run to preview; MANDATORY after switching providers)

python scripts/compare_answers.py --label before   # 3) baseline with hash embeddings
python scripts/compare_answers.py --label after    # 4) snapshot with Gemini embeddings
python scripts/compare_answers.py --compare before after   # 5) side-by-side quality diff
```

The comparison harness runs a fixed 6-question evaluation set through the live RAG
pipeline and reports retrieval hit rate, average vector score, latency and full answer
diffs; snapshots are saved under `data/comparisons/`.

### Database setup

- **Dev (default):** SQLite — zero setup. The DB file is created at `data/bisbuddy.db`.
- **Production:** PostgreSQL + pgvector
  ```bash
  docker run -d --name bisbuddy-db -e POSTGRES_USER=bisbuddy \
    -e POSTGRES_PASSWORD=bisbuddy -e POSTGRES_DB=bisbuddy -p 5432:5432 \
    pgvector/pgvector:pg16
  # inside psql: CREATE EXTENSION IF NOT EXISTS vector;
  # then set:
  #   DATABASE_URL=postgresql+psycopg://bisbuddy:bisbuddy@localhost:5432/bisbuddy
  ```
  Tables are created automatically on startup; `backend/app/database/migrations.py`
  is the idempotent hook for column-level migrations (swap in Alembic for prod).

---

## 8–11. Running

```bash
# Terminal 1 — backend (http://127.0.0.1:8000, docs at /docs)
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend (http://localhost:5173, proxies /api → :8000)
cd frontend
npm run dev
```

- **Running ingestion:** every admin upload runs the full pipeline automatically
  (status visible in Admin → table). `POST /api/documents/{id}/reindex` re-runs it.
- **Seeding again:** `python scripts/seed_data.py` (idempotent — existing rows skipped).

---

## 12. Adding documents

1. Login as an **admin** → **Admin Dashboard**.
2. Drop a PDF (≤ 25 MB, must contain a `%PDF` header and extractable text).
3. Optionally set title, standard number, year, type, category, official `source_url`.
4. Watch the status pipeline: `uploaded → extracting → chunking → embedding → indexed`.
5. Ask questions in chat — new content is immediately retrievable.

> Use official BIS PDFs with their source URL for real deployments. Never rely on the
> bundled SAMPLE documents for actual compliance decisions.

---

## 13. RAG explanation (for the team)

1. **Chunking** — cleaned text is split at detected headings (`4.2 Fineness`, `ANNEX B`,
   ALL-CAPS titles) and packed paragraph-wise up to `CHUNK_SIZE` characters with
   `CHUNK_OVERLAP` characters carried between chunks. Every chunk records its
   **page number** (from PDF char-offsets) and **section title**.
2. **Embeddings** — chunks and the user's question are embedded by the same provider
   (swap `EMBEDDING_PROVIDER`); vectors are stored on `DocumentChunk.embedding`.
3. **Retrieval** — cosine similarity over indexed chunks, blended with a keyword
   overlap score (`RETRIEVAL_MODE=hybrid`), filtered by document status/metadata.
4. **Reranking** — a second-stage scorer blends query-term coverage, exact phrase
   hits, standard-number matches (`IS 1234` etc.) and title alignment; the blended
   score becomes the citation's `relevance_score`.
5. **Grounded generation** — the top 5 chunks are serialised as numbered context
   blocks into the prompt. The system prompt *requires* `[n]` markers after every
   factual claim and refusal when context is insufficient. The API resolves the
   markers into structured `sources`; anything not cited isn't claimed as sourced.
6. **Fallback provider** — without `GEMINI_API_KEY`, an extractive provider answers
   using only sentences from the retrieved context that share terms with the
   question, and refuses otherwise. The app is never a mock; it just answers more
   conservatively.

---

## 14. API documentation

Interactive OpenAPI docs: **http://127.0.0.1:8000/docs**

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/register` | — | Create account → JWT |
| POST | `/api/auth/login` | — | Login → JWT |
| GET | `/api/auth/me` | user | Current user |
| POST | `/api/chat` | user | RAG answer + sources (JSON) |
| POST | `/api/chat/stream` | user | SSE: `meta` → `delta*` → `done`/`error` |
| GET | `/api/conversations` | user | List/search own conversations |
| GET/DELETE | `/api/conversations/{id}` | user | Detail / delete |
| POST | `/api/documents/upload` | **admin** | Upload PDF (multipart + metadata) |
| GET | `/api/documents` | user | List/search documents |
| GET | `/api/documents/{id}` | user | Metadata + chunk count |
| GET | `/api/documents/{id}/file` | user | Stream PDF (inline) |
| DELETE | `/api/documents/{id}` | **admin** | Delete doc + chunks + file |
| POST | `/api/documents/{id}/reindex` | **admin** | Re-run ingestion |
| GET | `/api/search` | user | Semantic chunk search (`?q=`) |
| GET | `/api/search/documents` | user | Metadata search |
| POST | `/api/feedback` | user | Rate an assistant message |
| GET | `/api/admin/stats` | **admin** | Dashboard counters |
| GET | `/api/admin/feedback` | **admin** | Recent feedback |
| GET | `/health` | — | Liveness + DB check |
| GET | `/api/config` | user | Non-sensitive runtime config |

Errors use proper HTTP codes (401/403/404/409/413/422/500/502) with friendly
`detail` messages; stack traces and secrets never reach the client and are logged
server-side instead (never logging keys or user content at INFO level).

---

## 15. Testing

```bash
cd backend
python -m pytest tests/ -q
```

Current result: **19 passed** — covering health, auth (register/login/dupe/401/403),
chunking (sections, pages, overlap, sizes), upload validation, and an **end-to-end
offline RAG test**: PDF upload → ingestion → chat question → retrieval → answer with
`IS 9999:2025` citation → persisted conversation, plus grounded-refusal and semantic
search tests. Tests run with the hash-embedding + fallback-LLM providers, so no API
key or network is needed in CI.

Frontend: `npm run build` performs the strict TypeScript check (currently clean);
component tests can be added with Vitest later.

---

## 16. Deployment

### Docker (recommended)

```bash
export SECRET_KEY=$(python -c "import secrets;print(secrets.token_hex(32))")
export GEMINI_API_KEY=your_key_here
docker compose up --build
# frontend  → http://localhost:8080
# backend   → http://localhost:8000  (docs at /docs)
# postgres  → localhost:5432 (pgvector image)
```

Then `docker compose exec backend python /app/../scripts/seed_data.py` is *not*
needed — mount the repo or run seeding locally against the composed DB.

### Notes

- Set a strong `SECRET_KEY` and real `GEMINI_API_KEY`; keep `.env` out of git.
- Put HTTPS in front (Caddy/Traefik/nginx) and restrict `CORS_ORIGINS` to your domain.
- For scale-out, run Alembic migrations and move uploads to object storage.

---

## 17. Limitations

- **SAMPLE data is synthetic** — answers are only as good as the indexed corpus; real
  deployments must index official BIS documents.
- Hash embeddings (offline mode) are lexical, not truly semantic — set
  `EMBEDDING_PROVIDER=gemini` for production-quality retrieval.
- Scanned/image PDFs need OCR, which is not bundled (extraction fails honestly).
- Chunk-page mapping is approximate for PDFs with complex multi-column layouts.
- The reranker is feature-based, not a neural cross-encoder.
- Single-instance deployment (background job queue is a natural next step).

## 18. Future improvements

- Alembic migrations + CI (GitHub Actions) pipeline
- Cross-encoder reranker (e.g. `bge-reranker-base`) behind the same interface
- OCR support (Tesseract) for scanned standards
- pgvector-native SQL `ORDER BY embedding <=> query` path
- Multi-language (Hindi + regional) answers and voice I/O
- official BIS portal integration for licence verification deep-links
- Analytics dashboard: popular questions, unanswered queries, feedback trends

---

## SIH demo script (10 minutes)

1. **Open** `http://localhost:5173` → landing page → **Get Started** → login
   `demo@bisbuddy.in / Demo@12345`.
2. Sidebar → select **Industry** mode (banner confirms).
3. Ask: *"What standards and requirements should I check before manufacturing cement?"*
4. RAG retrieves `IS 1234:2020` chunks; streamed answer appears.
5. Point out **citation chips [1]** and **Sources cards** (standard, page, % match).
6. **Click a citation chip** → PDF opens at the exact page in the document viewer.
7. Follow-up: *"And what about the licence application process?"* — answer uses
   conversation context + `BIS-PROCESS` document.
8. Switch to **Consumer** mode → ask *"How do I check a product is BIS certified?"*
   — simpler tone, consumer-guide citations.
9. Open **Admin Dashboard** (login as admin in another tab if needed).
10. **Upload a PDF** (use `data/sample_documents/sample_IS_3025_helmet_spec.pdf`).
11. Narrate the live status pipeline → `indexed` with chunk count.
12. Back in chat, ask: *"What is the shock absorption requirement for helmets?"* →
    answer cites the newly uploaded document.
13. Show **Documents** page semantic search and the 👍 feedback.
14. Close with the grounding demo: ask something out-of-corpus ("fees for dragon
    eggs certification") → honest refusal, no hallucination.
