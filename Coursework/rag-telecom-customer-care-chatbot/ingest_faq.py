"""Ingest data/faq.csv into the `faq` Chroma collection (FR-14).

One CSV row == one vector document.  Re-running the script is safe: documents
are keyed by the FAQ id, so edits overwrite in place (US-06).
"""

from __future__ import annotations

import csv

from langchain_core.documents import Document

import config
from vectorstore import replace_documents


def load_faq_documents() -> tuple[list[Document], list[str]]:
    documents: list[Document] = []
    ids: list[str] = []

    with config.FAQ_CSV.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            faq_id = (row.get("id") or "").strip()
            question = (row.get("question") or "").strip()
            answer = (row.get("answer") or "").strip()
            if not question or not answer:
                continue

            documents.append(
                Document(
                    page_content=f"Q: {question}\nA: {answer}",
                    metadata={
                        "source": "faq",
                        "identifier": f"FAQ-{faq_id}",
                        "category": (row.get("category") or "general").strip(),
                        "question": question,
                    },
                )
            )
            ids.append(f"faq-{faq_id}")

    return documents, ids


def main() -> None:
    if not config.FAQ_CSV.is_file():
        raise SystemExit(f"FAQ file not found: {config.FAQ_CSV}")

    documents, ids = load_faq_documents()
    count = replace_documents(config.FAQ_COLLECTION, documents, ids)
    print(f"Ingested {count} FAQ entries into collection '{config.FAQ_COLLECTION}'.")


if __name__ == "__main__":
    main()
