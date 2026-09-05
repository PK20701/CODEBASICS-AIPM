"""Ingest resolved tickets from data/tickets.db into the `tickets` collection (FR-15).

One resolved ticket == one vector document.  Unresolved / escalated tickets are
skipped: only cases with a verified resolution should ground an answer.
"""

from __future__ import annotations

import sqlite3

from langchain_core.documents import Document

import config
from vectorstore import replace_documents


def load_ticket_documents() -> tuple[list[Document], list[str]]:
    documents: list[Document] = []
    ids: list[str] = []

    conn = sqlite3.connect(config.TICKETS_DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT ticket_id, category, issue_type, description, resolution
            FROM tickets
            WHERE status = 'resolved'
            ORDER BY id
            """
        ).fetchall()
    finally:
        conn.close()

    for row in rows:
        content = (
            f"Issue: {row['issue_type']}\n"
            f"Category: {row['category']}\n"
            f"Customer reported: {row['description']}\n"
            f"Resolution: {row['resolution']}"
        )
        documents.append(
            Document(
                page_content=content,
                metadata={
                    "source": "tickets",
                    "identifier": row["ticket_id"],
                    "category": row["category"],
                    "issue_type": row["issue_type"],
                },
            )
        )
        ids.append(f"ticket-{row['ticket_id']}")

    return documents, ids


def main() -> None:
    if not config.TICKETS_DB.is_file():
        raise SystemExit(f"Ticket database not found: {config.TICKETS_DB}")

    documents, ids = load_ticket_documents()
    count = replace_documents(config.TICKETS_COLLECTION, documents, ids)
    print(f"Ingested {count} resolved tickets into collection '{config.TICKETS_COLLECTION}'.")


if __name__ == "__main__":
    main()
