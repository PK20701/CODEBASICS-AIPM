"""Central configuration for ShopMate. Secrets come only from .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# Same file that initial_setup/setup_db.py creates.
DB_PATH = ROOT / "store.db"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# PRD §11: one model for agent, vision and guardrail. The vision model is a
# separate setting so it can be swapped if the chat model does not take images.
LLM_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
VISION_MODEL = os.getenv("GROQ_VISION_MODEL", LLM_MODEL)
GUARDRAIL_MODEL = os.getenv("GROQ_GUARDRAIL_MODEL", LLM_MODEL)

LLM_TEMPERATURE = 0
# Qwen3 thinks before answering by default; not needed for tool routing.
LLM_REASONING_EFFORT = os.getenv("GROQ_REASONING_EFFORT", "none")
# Qwen accepts "none"; gpt-oss models need "low"/"medium"/"high".
VISION_REASONING_EFFORT = os.getenv("GROQ_VISION_REASONING_EFFORT", "none")
# Qwen sometimes writes Python-style `True`, which Groq's strict tool-call
# validation rejects before we see it. Retry the call this many times.
TOOL_CALL_RETRIES = 2
# Free tier allows ~7000 input tokens/minute. On a 429 the SDK waits for the
# time Groq asks for (retry-after) and tries again, this many times.
RATE_LIMIT_RETRIES = 6
# Longest we keep a shopper waiting for a rate-limit window to clear.
MAX_RATE_LIMIT_WAIT = 30

# Only the most recent chat messages are resent each turn (the last product
# list is passed separately), to stay within the free-tier token budget.
HISTORY_MESSAGES = 9
# Groq's free tier rejects requests whose potential output exceeds its
# output-tokens-per-minute limit, so every call sets an explicit cap.
AGENT_MAX_TOKENS = 700
TOOL_MAX_TOKENS = 200

# Safety net against a tool-calling loop that never ends.
MAX_AGENT_STEPS = 8

SINGLE_ITEM_PROMPT = "Would you like to order it? Just say yes or give me the number."

OFF_TOPIC_REPLY = (
    "I can only help with shopping in this store: honey, oils, nuts and seeds, "
    "grains, tea and coffee, snacks, and dairy alternatives. "
    "What can I find for you?"
)


class ServiceBusy(Exception):
    """Groq's free-tier limit was hit and the wait is too long to hold the shopper."""


def groq_client():
    from groq import Groq
    return Groq(api_key=require_api_key(), max_retries=RATE_LIMIT_RETRIES)


def require_api_key() -> str:
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your key "
            "from https://console.groq.com/keys"
        )
    return GROQ_API_KEY
