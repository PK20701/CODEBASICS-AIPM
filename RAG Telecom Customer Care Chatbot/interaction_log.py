"""Append-only interaction log backing the thumbs up / down control (FR-05a).

One JSON object per line in logs/interactions.jsonl so support ops can grep it
or load it into pandas without a schema migration.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import config


def _append(record: dict) -> None:
    config.FEEDBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
    record["timestamp"] = datetime.now(timezone.utc).isoformat()
    with config.FEEDBACK_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_answer(question: str, answer: str, sources: list[str], latency_s: float) -> None:
    _append(
        {
            "event": "answer",
            "question": question,
            "answer": answer,
            "sources": sources,
            "latency_s": round(latency_s, 3),
            "model": config.LLM_MODEL,
        }
    )


def log_feedback(question: str, answer: str, rating: str) -> None:
    """rating is "up" or "down"."""
    _append({"event": "feedback", "rating": rating, "question": question, "answer": answer})
