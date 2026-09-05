"""The LCEL RAG chain: retrieve -> prompt -> Groq -> string (section 9 of the PRD).

`answer_stream()` is the single entry point both front-ends use.  It returns the
retrieved documents up front (so the UI can render the Sources panel) plus a
token generator (FR-05).
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

import config
from retriever import build_retriever, format_context

SYSTEM_PROMPT = """You are NovaCell's telecom customer-care assistant.

You answer using ONLY the context below, which is retrieved from NovaCell's own \
knowledge sources and labelled by origin (FAQ, TICKETS, GUIDES, PLANS). You have no \
other knowledge about NovaCell.

Rules:
1. Use only facts present in the context. Never invent prices, policies, phone \
numbers, timeframes, settings or menu paths that are not written there.
2. If the context does not contain enough information to answer confidently, say so \
plainly and tell the customer: "{escalation}" Do not guess.
3. You have no access to the customer's account, balance, usage or billing records. \
If the question needs personal account data, say that and point them to the MyTelecom \
app or 611.
4. For plan, price or add-on questions, use only the PLANS entries. Quote plan names \
and prices exactly as written, including the currency, and say what the price covers \
(per month, per line, per day). Never estimate, convert or discount a price. If the \
customer asks which plan is cheapest or best, compare only the PLANS entries in the \
context and name the plans you compared.
5. Answer in plain, friendly English for a non-technical customer. Prefer short \
numbered steps for anything the customer has to do.
6. Be concise -- a few sentences or up to six steps. Do not restate the question.

Context:
{context}"""

PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_PROMPT), ("human", "{question}")]
)


@lru_cache(maxsize=1)
def get_llm() -> ChatGroq:
    """Deterministic Groq chat model (FR-12, FR-13)."""
    config.require_api_key()
    return ChatGroq(
        model=config.LLM_MODEL,
        temperature=config.LLM_TEMPERATURE,
        api_key=config.GROQ_API_KEY,
        reasoning_effort=config.LLM_REASONING_EFFORT,
        max_tokens=config.LLM_MAX_TOKENS,
    )


@lru_cache(maxsize=1)
def _retriever():
    return build_retriever()


def retrieve(question: str) -> list[Document]:
    """The source-labelled context documents for a question (FR-06, FR-07)."""
    return _retriever().invoke(question)


def _generation_chain():
    return PROMPT | get_llm() | StrOutputParser()


def answer_stream(question: str) -> tuple[list[Document], Iterator[str]]:
    """Retrieve context, then stream the grounded answer token by token.

    Returns (documents, token_iterator).  Documents come back before the first
    token so the caller can render the Sources panel immediately.
    """
    documents = retrieve(question)

    if not documents:
        return [], iter([config.ESCALATION_LINE])

    payload = {
        "context": format_context(documents),
        "question": question,
        "escalation": config.ESCALATION_LINE,
    }
    return documents, _generation_chain().stream(payload)


def answer(question: str) -> tuple[list[Document], str]:
    """Non-streaming convenience wrapper."""
    documents, tokens = answer_stream(question)
    return documents, "".join(tokens)
