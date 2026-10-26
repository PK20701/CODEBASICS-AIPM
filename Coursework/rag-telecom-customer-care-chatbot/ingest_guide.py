"""Ingest data/telecom_guide.pdf into the `guides` collection (FR-16).

The PDF is split into 600-character chunks with a 100-character overlap so a
procedure that straddles a chunk boundary is still retrievable.
"""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

import config
from vectorstore import replace_documents


def load_pages() -> list[Document]:
    """One Document per PDF page, tagged with its 1-based page number."""
    reader = PdfReader(str(config.GUIDE_PDF))

    pages = []
    for number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(Document(page_content=text, metadata={"page": number}))
    return pages


def load_guide_documents() -> tuple[list[Document], list[str]]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(load_pages())

    documents = []
    ids = []
    for index, chunk in enumerate(chunks, start=1):
        page_number = chunk.metadata.get("page", 0)
        chunk.metadata = {
            "source": "guides",
            "identifier": f"GUIDE p.{page_number} #{index}",
            "page": page_number,
        }
        documents.append(chunk)
        ids.append(f"guide-{index:04d}")

    return documents, ids


def main() -> None:
    if not config.GUIDE_PDF.is_file():
        raise SystemExit(f"Guide PDF not found: {config.GUIDE_PDF}")

    documents, ids = load_guide_documents()
    count = replace_documents(config.GUIDES_COLLECTION, documents, ids)
    print(
        f"Ingested {count} guide chunks "
        f"({config.CHUNK_SIZE}-char, {config.CHUNK_OVERLAP}-char overlap) "
        f"into collection '{config.GUIDES_COLLECTION}'."
    )


if __name__ == "__main__":
    main()
