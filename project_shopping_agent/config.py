"""Settings and small shared helpers for ShopMate. API keys come only from .env."""

import base64
import io
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from PIL import Image

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# The database initial_setup/setup_db.py creates.
DB_PATH = ROOT / "store.db"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# --- Models (PRD §11) ------------------------------------------------------
# One model does chat, photos and the off-topic check. Photos and the check can
# be pointed elsewhere, e.g. when the chat model can't read images.
LLM_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
VISION_MODEL = os.getenv("GROQ_VISION_MODEL", LLM_MODEL)
GUARDRAIL_MODEL = os.getenv("GROQ_GUARDRAIL_MODEL", LLM_MODEL)

LLM_TEMPERATURE = 0
# Qwen accepts "none" (no thinking step); gpt-oss models need "low", "medium" or "high".
LLM_REASONING_EFFORT = os.getenv("GROQ_REASONING_EFFORT", "none")
VISION_REASONING_EFFORT = os.getenv("GROQ_VISION_REASONING_EFFORT", "none")

# --- Limits ----------------------------------------------------------------
# Groq rejects malformed tool calls (e.g. Python-style `True`) before we see them.
TOOL_CALL_RETRIES = 2
# The Groq SDK waits and retries on a rate limit this many times.
RATE_LIMIT_RETRIES = 6
# Longest we'll keep a shopper waiting for a per-minute limit to clear.
MAX_RATE_LIMIT_WAIT = 30
# Chat messages resent each turn; the last product list is passed separately.
HISTORY_MESSAGES = 9
# Groq's free tier refuses calls whose possible output is too large, so every call sets a cap.
AGENT_MAX_TOKENS = 700
TOOL_MAX_TOKENS = 200
# Stops a tool-calling loop that never ends.
MAX_AGENT_STEPS = 8
# Photos are resized to this longest side: smaller, faster uploads.
MAX_IMAGE_SIDE = 384

# --- Fixed wording ---------------------------------------------------------
SINGLE_ITEM_PROMPT = "Would you like to order it? Just say yes or give me the number."

OFF_TOPIC_REPLY = (
    "I can only help with shopping in this store: honey, oils, nuts and seeds, "
    "grains, tea and coffee, snacks, and dairy alternatives. "
    "What can I find for you?"
)


# --- Helpers ---------------------------------------------------------------

class ServiceBusy(Exception):
    """Groq's free-tier limit was hit and the wait is too long to hold the shopper."""


def require_api_key() -> str:
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your key "
            "from https://console.groq.com/keys"
        )
    return GROQ_API_KEY


def groq_client() -> Groq:
    return Groq(api_key=require_api_key(), max_retries=RATE_LIMIT_RETRIES)


def retry_after_seconds(message: str) -> float | None:
    """Turn Groq's "try again in 11m39.8s" into seconds."""
    m = re.search(r"try again in ((?:\d+h)?(?:\d+m)?(?:[\d.]+s)?)", message)
    if not m or not m.group(1):
        return None
    parts = {unit: value for value, unit in re.findall(r"([\d.]+)([hms])", m.group(1))}
    return float(parts.get("h", 0)) * 3600 + float(parts.get("m", 0)) * 60 + float(parts.get("s", 0))


def busy_error(exc: Exception) -> ServiceBusy:
    wait = retry_after_seconds(str(exc))
    when = f" in about {int(wait // 60)} min {int(wait % 60)} s" if wait else " shortly"
    return ServiceBusy(f"ShopMate has hit the Groq free-tier usage limit. Please try again{when}.")


def prepare_image(image_bytes: bytes) -> tuple[str, str]:
    """Return (mime type, base64) for a resized JPEG copy of the photo."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return "image/jpeg", base64.b64encode(buf.getvalue()).decode()
