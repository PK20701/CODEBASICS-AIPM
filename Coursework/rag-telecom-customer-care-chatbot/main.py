"""Interactive CLI REPL for the telecom care bot (FR-18, FR-19).

    python main.py

Type a question and the grounded answer streams back with its sources.
Type `quit` (or Ctrl-C) to exit.
"""

from __future__ import annotations

import time

import chain
import config
from interaction_log import log_answer
from retriever import citation

BANNER = """
NovaCell Telecom Care Assistant (CLI)
Answers are grounded in the FAQ, resolved tickets and the telecom guide.
Type 'quit' to exit.
"""


def ask(question: str) -> None:
    started = time.perf_counter()

    documents, tokens = chain.answer_stream(question)

    print("\nAssistant: ", end="", flush=True)
    pieces = []
    for token in tokens:
        pieces.append(token)
        print(token, end="", flush=True)
    print()

    answer_text = "".join(pieces)
    sources = [citation(document) for document in documents]

    if sources:
        print("\nSources:")
        for source in dict.fromkeys(sources):  # de-duplicate, keep order
            print(f"  - {source}")

    elapsed = time.perf_counter() - started
    print(f"\n({elapsed:.1f}s)\n")
    log_answer(question, answer_text, sources, elapsed)


def main() -> None:
    print(BANNER)

    try:
        config.require_api_key()
    except RuntimeError as error:
        raise SystemExit(str(error))

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return

        if not question:
            continue
        if question.lower() in {"quit", "exit"}:
            print("Goodbye.")
            return

        try:
            ask(question)
        except Exception as error:  # keep the REPL alive on a transient API error
            print(f"\n[error] {error}\n")


if __name__ == "__main__":
    main()
