"""Streamlit front-end for the NovaCell telecom care bot.

    streamlit run app.py

Covers FR-01 - FR-05a and FR-13a: free-text chat, sidebar sample questions,
session history, clear-conversation, streamed tokens, per-answer Sources panel
and thumbs up/down feedback.
"""

from __future__ import annotations

import time

import streamlit as st

import chain
import config
from interaction_log import log_answer, log_feedback
from retriever import citation
from vectorstore import collection_counts

st.set_page_config(page_title="NovaCell Care Assistant", page_icon="📶", layout="centered")


# --- Session state -------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []  # [{role, content, sources?}]
if "pending" not in st.session_state:
    st.session_state.pending = None  # question queued by a sidebar click


@st.cache_data(show_spinner="Loading knowledge base…")
def cached_counts() -> dict[str, int]:
    """Document counts; cached so the embedding model loads once per process."""
    return collection_counts()


def clear_conversation() -> None:
    st.session_state.messages = []
    st.session_state.pending = None


def queue(question: str) -> None:
    st.session_state.pending = question


# --- Header (rendered first so the page paints before the KB probe) ------

st.title("📶 NovaCell Care Assistant")
st.caption(
    "Answers come only from NovaCell's FAQ, resolved tickets, telecom guide and "
    "plan catalogue. "
    "No account access — for anything personal, call 611 or use the MyTelecom app."
)


# --- Sidebar -------------------------------------------------------------

with st.sidebar:
    st.header("Sample questions")
    st.caption("Click one to send it straight to the assistant.")
    for index, question in enumerate(config.SAMPLE_QUESTIONS):
        st.button(
            question,
            key=f"sample-{index}",
            use_container_width=True,
            on_click=queue,
            args=(question,),
        )

    st.divider()
    st.button(
        "🗑️ Clear conversation",
        use_container_width=True,
        on_click=clear_conversation,
    )

    st.divider()
    st.caption("Knowledge base")
    counts = cached_counts()
    if sum(counts.values()) == 0:
        st.warning("Empty. Run `python ingest_all.py` first.")
    else:
        st.caption(
            f"FAQ {counts[config.FAQ_COLLECTION]} · "
            f"Tickets {counts[config.TICKETS_COLLECTION]} · "
            f"Guide chunks {counts[config.GUIDES_COLLECTION]} · "
            f"Plans {counts[config.PLANS_COLLECTION]}"
        )
    st.caption(f"Model: `{config.LLM_MODEL}`")


def render_sources(sources: list[str], key: str) -> None:
    """Expandable Sources section listing every retrieved document (FR-13a)."""
    if not sources:
        return
    with st.expander(f"📚 Sources ({len(sources)})"):
        for source in sources:
            st.markdown(f"- `{source}`")


def render_feedback(index: int, message: dict) -> None:
    """👍 / 👎 on every assistant answer, written to the log (FR-05a)."""
    question = ""
    if index > 0 and st.session_state.messages[index - 1]["role"] == "user":
        question = st.session_state.messages[index - 1]["content"]

    if message.get("rating"):
        st.caption("Thanks for the feedback.")
        return

    up, down, _ = st.columns([1, 1, 8])
    if up.button("👍", key=f"up-{index}"):
        log_feedback(question, message["content"], "up")
        message["rating"] = "up"
        st.rerun()
    if down.button("👎", key=f"down-{index}"):
        log_feedback(question, message["content"], "down")
        message["rating"] = "down"
        st.rerun()


# --- Conversation history (FR-03) ---------------------------------------

for index, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            render_sources(message.get("sources", []), key=str(index))
            render_feedback(index, message)


# --- New question --------------------------------------------------------

typed = st.chat_input("Ask about data, billing, SIM, roaming, calls or your account…")
question = typed or st.session_state.pending
st.session_state.pending = None

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            started = time.perf_counter()
            documents, tokens = chain.answer_stream(question)
            answer_text = st.write_stream(tokens)  # token-by-token (FR-05)
            elapsed = time.perf_counter() - started

            sources = list(dict.fromkeys(citation(document) for document in documents))
            render_sources(sources, key="live")
            log_answer(question, answer_text, sources, elapsed)

            st.session_state.messages.append(
                {"role": "assistant", "content": answer_text, "sources": sources}
            )
            st.rerun()
        except Exception as error:
            friendly = (
                "Sorry — I couldn't reach the answering service just now. "
                "Please try again, or call 611 for help."
            )
            st.warning(friendly)
            with st.expander("Technical detail"):
                st.code(str(error))
            st.session_state.messages.append(
                {"role": "assistant", "content": friendly, "sources": []}
            )
