"""Merged retriever across the knowledge collections (FR-06 - FR-08).

Top-k is fetched from each collection in parallel and the results are
concatenated in registry order, so the prompt always sees FAQ entries first,
then ticket resolutions, then guide chunks, then plan catalogue entries.

To register a new knowledge source (NFR-06): write an `ingest_*.py` that fills a
new collection, then add its name to `COLLECTIONS` below and a display label to
`COLLECTION_LABELS` in config.py -- nothing else changes.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

import config
from vectorstore import get_collection

# Registry of the collections the retriever fans out to.
COLLECTIONS = [
    config.FAQ_COLLECTION,
    config.TICKETS_COLLECTION,
    config.GUIDES_COLLECTION,
    config.PLANS_COLLECTION,
]


class MergedRetriever(BaseRetriever):
    """Fan out one question to every registered collection, merge the hits."""

    collections: list[str] = COLLECTIONS
    top_k: int | None = None  # None -> per-collection depth from config

    def depth_for(self, collection: str) -> int:
        """Documents to pull from one collection; an explicit top_k wins."""
        if self.top_k is not None:
            return self.top_k
        return config.top_k_for(collection)

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun | None = None
    ) -> list[Document]:
        def search(name: str) -> list[Document]:
            return get_collection(name).similarity_search(
                query, k=self.depth_for(name)
            )

        with ThreadPoolExecutor(max_workers=len(self.collections)) as pool:
            results = pool.map(search, self.collections)

        return [document for hits in results for document in hits]


def build_retriever(top_k: int | None = None) -> MergedRetriever:
    """Merge each collection's hits into one document list (FR-07).

    Depth comes from config per collection; pass `top_k` to force one depth
    across all of them (used by tests).
    """
    return MergedRetriever(collections=COLLECTIONS, top_k=top_k)


def source_label(document: Document) -> str:
    """FAQ / TICKETS / GUIDES label used in the prompt context (FR-08)."""
    source = document.metadata.get("source", "")
    return config.COLLECTION_LABELS.get(source, source.upper() or "SOURCE")


def citation(document: Document) -> str:
    """Short human-readable citation for the Sources panel (FR-13a)."""
    identifier = document.metadata.get("identifier", "unknown")
    if source_label(document) == "TICKETS":
        return f"TICKET {identifier}"
    return identifier


def format_context(documents: list[Document]) -> str:
    """Render retrieved documents as a source-labelled context block."""
    if not documents:
        return "(no relevant documents were retrieved)"

    blocks = []
    for document in documents:
        identifier = document.metadata.get("identifier", "unknown")
        blocks.append(
            f"[{source_label(document)} | {identifier}]\n{document.page_content.strip()}"
        )
    return "\n\n---\n\n".join(blocks)
