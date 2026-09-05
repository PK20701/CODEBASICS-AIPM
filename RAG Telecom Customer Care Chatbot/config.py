"""Central configuration for the RAG telecom customer-care chatbot.

Every path, model name and tunable lives here so ingestion, retrieval and the
two front-ends (CLI + Streamlit) stay in agreement.  Secrets are never stored
here -- they are read from the local .env file (NFR-03).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root == folder containing this file.
ROOT = Path(__file__).resolve().parent

load_dotenv(ROOT / ".env")

# --- Data sources (section 8 of the PRD) --------------------------------
# The checked-in folder is "Data"; fall back to "data" so the project also
# works on case-sensitive filesystems where the folder was cloned lowercase.
DATA_DIR = ROOT / "Data" if (ROOT / "Data").is_dir() else ROOT / "data"
FAQ_CSV = DATA_DIR / "faq.csv"
TICKETS_DB = DATA_DIR / "tickets.db"
GUIDE_PDF = DATA_DIR / "telecom_guide.pdf"
PLANS_JSON = DATA_DIR / "plans.json"

# --- Vector store (FR-17, NFR-05) ---------------------------------------
CHROMA_DIR = ROOT / "chroma_store"

FAQ_COLLECTION = "faq"
TICKETS_COLLECTION = "tickets"
GUIDES_COLLECTION = "guides"
PLANS_COLLECTION = "plans"

# Human-readable label injected into the prompt context (FR-08).
COLLECTION_LABELS = {
    FAQ_COLLECTION: "FAQ",
    TICKETS_COLLECTION: "TICKETS",
    GUIDES_COLLECTION: "GUIDES",
    PLANS_COLLECTION: "PLANS",
}

# --- Embeddings (FR-09, NFR-02) -----------------------------------------
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# --- Retrieval (FR-06, FR-07) -------------------------------------------
TOP_K = 3  # default per collection

# Per-collection overrides.
#
# The plan catalogue is a small, closed set that customers ask comparison
# questions about ("which unlimited plan is cheapest?").  Those are only
# answerable correctly if the model sees every plan: embedding similarity
# ranks by wording, not by price, so a top-3 slice can easily omit the plan
# that actually wins the comparison and the answer looks confident but wrong.
# Chroma returns at most what a collection holds, so this covers the whole
# catalogue with room to grow.
COLLECTION_TOP_K = {
    PLANS_COLLECTION: 50,
}


def top_k_for(collection: str) -> int:
    """How many documents to pull from one collection."""
    return COLLECTION_TOP_K.get(collection, TOP_K)

# --- Chunking the PDF guide (FR-16) -------------------------------------
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100

# --- LLM (FR-12, FR-13) -------------------------------------------------
LLM_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.6-27b")
LLM_TEMPERATURE = 0
LLM_REASONING_EFFORT = "none"

# Explicit output cap. Groq rejects a request up-front when the model's
# *potential* output exceeds the account's output-tokens-per-minute limit
# (free tier is 1000 OTPM), so leaving this unset fails with a 429 even for
# a short answer. A Tier-1 support reply needs far less than this anyway.
LLM_MAX_TOKENS = 512

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# --- Interaction log (FR-05a) -------------------------------------------
FEEDBACK_LOG = ROOT / "logs" / "interactions.jsonl"

# --- Escalation copy (FR-11) --------------------------------------------
ESCALATION_LINE = (
    "I don't have that information in NovaCell's knowledge base. "
    "Please call 611 or use the MyTelecom app to reach a support agent."
)

# --- Sample questions shown in the sidebar (FR-02) ----------------------
SAMPLE_QUESTIONS = [
    "Why is my mobile internet so slow?",
    "I was charged twice this month - what do I do?",
    "How do I activate roaming before travelling abroad?",
    "My eSIM won't activate on my new phone.",
    "There is an echo on my calls. How do I fix it?",
    "How do I download an itemised bill?",
    "Which unlimited plan is cheapest?",
    "What does the International Day Pass cost?",
]


def require_api_key() -> str:
    """Return the Groq API key or explain exactly how to set it."""
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your key "
            "from https://console.groq.com/keys"
        )
    return GROQ_API_KEY
