# Gemini Configuration Walkthrough (BIS Buddy)

This guide takes BIS Buddy from **offline fallback mode** (hash embeddings + extractive
answers) to **full Gemini mode** (neural embeddings + generative streaming answers).
It takes about 5 minutes.

---

## 0. What changes when you add the key

| Capability | Before (no key) | After (key configured) |
|---|---|---|
| Chat answers | Extractive, quoted from retrieved chunks | Generative Gemini `gemini-3.1-flash-lite`, streaming |
| Embeddings | Local hashing trick (lexical matching only) | Google `gemini-embedding-001` (true semantic search) |
| Retrieval quality | Good for exact-word matches | Understands paraphrases ("PPE for head" finds helmet docs) |
| Cost | Free, offline | Free tier is generous (see quotas below) |

Nothing else changes: the grounding contract, citations, statuses, and DB schema are
identical. If the key is ever removed or the API is unreachable, the app automatically
falls back — it never breaks.

---

## 1. Get an API key (free)

1. Open **https://aistudio.google.com/apikey** and sign in with any Google account.
2. Click **Create API key** → pick/create a project → copy the key
   (looks like `AIzaSy...`).
3. Free tier includes both `gemini-3.1-flash-lite` (chat) and `gemini-embedding-001`
   (embeddings) — no billing account required for development use.

> Keep the key private. It lives only in `.env` on the server side; the frontend never
> sees it (all Gemini calls happen in the FastAPI backend).

---

## 2. Create / edit your `.env`

From the project root:

```bash
cp .env.example .env
```

Then edit `.env` and set these three lines:

```ini
# --- LLM (Gemini) ---
GEMINI_API_KEY=AIzaSy...your-real-key...
GEMINI_MODEL=gemini-3.1-flash-lite

# --- Embeddings ---
EMBEDDING_PROVIDER=gemini
GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001
```

Notes:

- The app looks for `.env` at the **project root** or in **`backend/`** — either works.
- `GEMINI_API_KEY` may also be exported as a real environment variable; real env vars
  always win over `.env` values.
- Every variable is documented in `.env.example`.

---

## 3. Verify the configuration

```bash
python scripts/check_gemini.py
```

Expected output:

```
[OK]   .env file: C:\...\BIS-SAHAYAK\.env
       embedding provider: gemini
       llm model:          gemini-3.1-flash-lite
[OK]   GEMINI_API_KEY found (AIzaSy...ab12)

Testing embeddings endpoint (gemini-embedding-001)...
[OK]   Embeddings OK - provider=gemini, dim=768

Testing chat endpoint (gemini-3.1-flash-lite)...
[OK]   Chat OK - model replied: 'READY'

RESULT: Gemini is fully configured - embeddings and chat both work.
```

If a check fails, the script prints the exact API error (bad key, quota, blocked
model...) — fix `.env` and re-run.

---

## 4. Re-index all documents with Gemini embeddings

**Important:** your existing chunks were embedded with the hash provider (768-dim
lexical vectors). They are not comparable with Gemini vectors, so after switching
`EMBEDDING_PROVIDER=gemini` you **must** re-index:

```bash
# Preview what will be re-processed (no changes):
python scripts/reindex_all.py --dry-run

# Re-run the real pipeline (extract -> clean -> chunk -> embed -> index):
python scripts/reindex_all.py
```

Every document goes through the standard ingestion statuses again
(`extracting → chunking → embedding → indexed`) and each chunk row records
`embedding_model=gemini`, visible in the admin dashboard. You can also re-index a
single document from the admin UI with its **Re-index** button.

If the key is wrong or the API is down mid-run, the document is marked `failed` with
the API error stored in `error_message` — nothing is silently half-indexed.

---

## 5. Measure the difference (before/after comparison)

The comparison harness runs a fixed 6-question evaluation set through the *live* RAG
pipeline and saves full snapshots (retrieval scores, citations used, complete answers)
to `data/comparisons/`.

**Before switching** (hash embeddings + extractive answers):

```bash
python scripts/compare_answers.py --label before
```

**After** completing steps 2–4 (Gemini embeddings + generative answers):

```bash
python scripts/compare_answers.py --label after

# Side-by-side comparison:
python scripts/compare_answers.py --compare before after
```

The comparison prints retrieval hit rate (did the right standard rank #1), average
top vector score, latency, and per-question answer diffs. Full answer text for both
runs is saved in the JSON snapshots.

---

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `API key not valid` | Typo / revoked key | Re-copy the key from AI Studio into `.env` |
| `429 RESOURCE_EXHAUSTED` | Free-tier quota hit | Wait a minute; lower `RETRIEVAL_TOP_K`; the fallback provider keeps the app usable |
| Embeddings check fails but chat works | Model name wrong | Keep `GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001` |
| Answers look extractive after switching | Backend not restarted or re-index skipped | Restart uvicorn; run `python scripts/reindex_all.py` |
| Answers cut off mid-sentence | gemini-3.x thinking models reason inside `max_output_tokens` | Keep `GEMINI_MAX_OUTPUT_TOKENS=8192` (or higher) |
| `.env` changes have no effect | Server started before edit | Restart the backend; check `scripts/check_gemini.py` shows your file path |

---

## 7. Quotas & cost reference (free tier, measured September 2026)

| Model | Free-tier behaviour |
|---|---|
| `gemini-3.1-flash-lite` | Generous daily allowance (non-thinking, fast) — demo default |
| `gemini-3.6-flash` | Higher quality but THINKS; free tier is only ~20 requests/day — paid key recommended |
| `gemini-embedding-001` | Generous per-minute allowance |

Ingestion batches 100 chunks per embedding request, so a typical standard (20–60
chunks) costs 1–2 requests. When Google retires a model you use, the API's 404 error
tells you the replacement name — update `GEMINI_MODEL` / `GEMINI_EMBEDDING_MODEL` in
`.env` and re-run `python scripts/check_gemini.py`. Check current official limits at
https://ai.google.dev/pricing — they change over time.
