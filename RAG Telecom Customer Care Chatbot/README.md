# NovaCell RAG Telecom Customer Care Chatbot

A Retrieval-Augmented Generation assistant that answers Tier-1 telecom support
questions grounded **only** in NovaCell's own knowledge: the public FAQ, past
resolved tickets, and the official PDF guide. Built to [PRD.md](PRD.md).

```
question ──▶ merged retriever ──▶ ChatPromptTemplate ──▶ Qwen3.6-27B (Groq) ──▶ streamed answer
                ├── chroma · faq       top-3               temperature 0        + Sources panel
                ├── chroma · tickets   top-3               reasoning_effort=none
                ├── chroma · guides    top-3
                └── chroma · plans     all 14 (see below)
```

Embeddings run locally (`all-MiniLM-L6-v2`) — no embedding API cost, no data
leaving the machine at index time. Only generation calls out to Groq.

---

## Setup

> Commands below are **Windows PowerShell**. Note that `&&` is not a valid
> statement separator in Windows PowerShell 5.1 — run each line on its own, or
> use `;` to chain.

Everything installs into a **project-local `.venv`** (NFR-04) — nothing touches
your global Python.

```bash
uv venv .venv --python 3.13
```

```bash
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

> With `uv` this is much faster: `$env:VIRTUAL_ENV=".venv"; uv pip install -r requirements.txt`

Add your Groq API key (free at <https://console.groq.com/keys>):

```bash
Copy-Item .env.example .env
```

Then edit `.env` and set `GROQ_API_KEY=gsk_...`.

## Build the knowledge base

One command ingests all three sources into `chroma_store/`:

```bash
.\.venv\Scripts\python.exe ingest_all.py
```

The first run downloads the ~90 MB embedding model. The store persists to disk,
so the app never re-ingests on start (NFR-05). Re-running any ingest script is
idempotent — documents are keyed by id, so edits overwrite in place.

| Script | Source | Documents |
|---|---|---|
| `ingest_faq.py` | `Data/faq.csv` | 1 per row |
| `ingest_tickets.py` | `Data/tickets.db` | 1 per **resolved** ticket |
| `ingest_guide.py` | `Data/telecom_guide.pdf` | 600-char chunks, 100-char overlap |
| `ingest_plans.py` | `Data/plans.json` | 1 per plan / add-on |

## Run

Easiest — the launcher handles paths, and builds the knowledge base if missing:

```bash
.\run.ps1
```

Then open <http://localhost:8501>. Press `Ctrl+C` in the terminal to stop it.

Equivalent long form:

```bash
.\.venv\Scripts\python.exe -m streamlit run app.py
```

CLI REPL (type `quit` to exit):

```bash
.\run_cli.ps1
```

> Prefer `python.exe -m streamlit` over `streamlit.exe`. The `.exe` shim in
> `Scripts\` resolves the interpreter through a trampoline that can fail with
> *"did not find executable at ...python.exe"* if the uv-managed Python is moved
> or relinked; `-m` avoids that indirection entirely.

---

## How grounding is enforced

- The system prompt allows **only** the retrieved context — no internal
  knowledge fallback (FR-10), at `temperature=0` (FR-12).
- Each of the 9 retrieved documents is labelled by origin (`FAQ` / `TICKETS` /
  `GUIDES`) with its identifier before it reaches the model (FR-08).
- When context is insufficient the bot says so and routes the customer to 611
  or the MyTelecom app (FR-11).
- Personal account questions ("what's my balance?") are explicitly out of scope
  and answered with the same handoff — there is no CRM or billing integration.
- Every answer ships an expandable **Sources** list of the documents actually
  retrieved (FR-13a), so any claim can be traced back.

## Tested with

Python 3.13.15 on Windows, with LangChain 1.6 / langchain-groq 1.1,
ChromaDB 1.5, sentence-transformers 6.0, Streamlit 1.63.

Note: `MergerRetriever` was removed in LangChain 1.x, so the three-collection
fan-out is implemented directly in [retriever.py](retriever.py) as a
`BaseRetriever` that queries each collection in a thread pool.

## Plans & pricing

`Data/plans.json` is the plan catalogue: 14 entries covering prepaid, postpaid,
family, specialty (student / 55+), data-only and add-ons (roaming passes,
hotspot boost). Each entry becomes one document in the `plans` collection,
labelled `PLANS` in the prompt context and cited by plan id (e.g.
`POST-UNLIMITED-PLUS`).

The catalogue is not uniformly shaped — plans price with `monthly_price` while
add-ons use `price` + `price_unit`, `data_gb` is sometimes a number, sometimes
null (unlimited) and sometimes free text, and only some entries carry
`eligibility`, `coverage` or `lines_included`. [ingest_plans.py](ingest_plans.py)
renders each field only when present, so a document never asserts a detail the
catalogue does not contain.

**Why plans use a different retrieval depth.** Every other collection returns
top-3. Plans returns the whole catalogue, via `COLLECTION_TOP_K` in
[config.py](config.py). Embedding similarity ranks by wording, not by price, so
a top-3 slice answers *"which unlimited plan is cheapest?"* confidently and
wrongly — it returned `Prepaid Unlimited (USD 45)` while Student Unlimited
(USD 30) and the 55+ Plan (USD 40) were never retrieved. Pulling all 14 costs
about 1,900 extra prompt tokens per query (~2,900 total, retrieval still ~0.08s)
and makes comparison questions correct. To trade that back, lower the value or
delete the entry to fall back to `TOP_K`.

## Groq free-tier note

Groq enforces an **output-tokens-per-minute** limit (1000 on the free tier) and
rejects a request up-front if the model's *potential* output exceeds it — so
leaving `max_tokens` unset returns a 429 even for a one-paragraph answer.
`LLM_MAX_TOKENS` in [config.py](config.py) sets an explicit cap (512), which is
well above what a Tier-1 reply needs. Raise it if you move to a paid tier.

## Files

| File | Role |
|---|---|
| `config.py` | Paths, model names, chunking, top-k, escalation copy |
| `vectorstore.py` | Local embeddings + persisted Chroma collections |
| `ingest_faq.py` / `ingest_tickets.py` / `ingest_guide.py` / `ingest_plans.py` | Per-source ingestion |
| `ingest_all.py` | Runs all four |
| `retriever.py` | Merged 4-collection retriever, per-collection depth, citations |
| `chain.py` | LCEL chain: retrieve → prompt → Groq → streamed string |
| `app.py` | Streamlit chat UI |
| `main.py` | CLI REPL |
| `interaction_log.py` | Appends answers and 👍/👎 to `logs/interactions.jsonl` |

## Adding a knowledge source

1. Write `ingest_<source>.py` that builds `Document`s and calls
   `replace_documents("<collection>", docs, ids)`.
2. Add the collection name to `COLLECTIONS` in [retriever.py](retriever.py) and
   a display label to `COLLECTION_LABELS` in [config.py](config.py).

No other file changes (NFR-06).

## Feedback log

`logs/interactions.jsonl` — one JSON object per line:

```json
{"event": "answer",   "question": "...", "answer": "...", "sources": ["FAQ-2"], "latency_s": 1.8}
{"event": "feedback", "rating": "down", "question": "...", "answer": "..."}
```

Git-ignored (it holds customer question text). Support ops can review it locally to
see deflection quality and which thumbs-down answers point at missing FAQ content.
