"""Shared access to the local embedding model and the persisted Chroma store.

Both the ingest scripts and the retriever go through here so a single
embedding model instance is reused per process (loading all-MiniLM-L6-v2
costs a few seconds, so we do it once).
"""

from __future__ import annotations

import threading
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

import config


# The retriever fans out across collections in threads. lru_cache alone is not
# enough there: concurrent first-callers all miss the cache and each builds its
# own copy of the embedding model. These locks make construction happen once.
_EMBEDDINGS_LOCK = threading.Lock()
_COLLECTION_LOCK = threading.Lock()


@lru_cache(maxsize=1)
def _build_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def get_embeddings() -> HuggingFaceEmbeddings:
    """Local sentence-transformers embeddings -- no external API (FR-09)."""
    with _EMBEDDINGS_LOCK:
        return _build_embeddings()


@lru_cache(maxsize=8)
def _build_collection(name: str) -> Chroma:
    config.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=name,
        embedding_function=get_embeddings(),
        persist_directory=str(config.CHROMA_DIR),
    )


def get_collection(name: str) -> Chroma:
    """Open (or create) one persisted Chroma collection (FR-17, NFR-05)."""
    with _COLLECTION_LOCK:
        return _build_collection(name)


def replace_documents(collection_name: str, documents, ids) -> int:
    """Write documents into a collection so re-running an ingest is idempotent.

    Chroma upserts on a known id, so a re-run overwrites in place rather than
    duplicating.  Ids that disappeared from the source are deleted (FR-17).
    """
    store = get_collection(collection_name)

    existing = set(store.get(include=[])["ids"])
    stale = existing - set(ids)
    if stale:
        store.delete(ids=list(stale))

    store.add_documents(documents=documents, ids=ids)
    return len(documents)


def collection_counts() -> dict[str, int]:
    """Document count per collection -- used by the UI health panel."""
    counts = {}
    for name in (
        config.FAQ_COLLECTION,
        config.TICKETS_COLLECTION,
        config.GUIDES_COLLECTION,
        config.PLANS_COLLECTION,
    ):
        try:
            counts[name] = len(get_collection(name).get(include=[])["ids"])
        except Exception:
            counts[name] = 0
    return counts
