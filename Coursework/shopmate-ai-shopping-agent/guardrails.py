"""GR-01 off-topic guardrail (PRD §8). Runs in code BEFORE the agent.

GR-02 (no order without a yes) lives in intent.resolve_confirmation and tools.checkout.
"""

import json
import re
from dataclasses import dataclass

from groq import RateLimitError

import intent
from config import (GUARDRAIL_MODEL, LLM_REASONING_EFFORT, LLM_TEMPERATURE, TOOL_MAX_TOKENS,
                    VISION_MODEL, VISION_REASONING_EFFORT, busy_error, groq_client, prepare_image)

TEXT_PROMPT = """You are the gatekeeper for ShopMate, the assistant of a small online pantry store
(honey, oils, nuts and seeds, grains, tea and coffee, snacks, dairy alternatives).

Decide if the shopper's message is about shopping in this store.
ON TOPIC: finding, comparing or asking about grocery/pantry products (even ones the store may not stock),
prices, ratings, organic, ordering, confirming or declining an order, order history, shopping preferences,
greetings, thanks, or asking what ShopMate can do.
OFF TOPIC: anything else, e.g. poems, stories, jokes, weather, news, coding, homework, general knowledge,
health or medical advice, recipes, or chit-chat unrelated to shopping here, even if it mentions a product
("write me a poem about honey" is OFF TOPIC).

Reply with JSON only: {"on_topic": true|false}"""

IMAGE_PROMPT = """Look at this photo. Is its main subject a grocery or pantry product a shop could sell
(e.g. a jar of honey, oats, milk, oil, nuts, tea, coffee, snacks), packaged or loose?
Animals, people, places, vehicles and other non-food objects are NOT products.
Reply with JSON only:
{"is_grocery_product": true|false, "product": "<what it is>", "search_keyword": "<one or two generic words, e.g. honey>", "looks_organic": true|false}"""


@dataclass
class Verdict:
    on_topic: bool
    reason: str                     # "rule", "text-check", "image-check", "check-failed"
    image_description: dict | None = None  # reused by describe_product_image, saves a second vision call


def check(text: str, image_bytes: bytes | None, image_mime: str | None,
          last_list: list[dict], last_reply: str | None) -> Verdict:
    if image_bytes:
        return _check_image(image_bytes, image_mime or "image/png")

    t = text.strip()
    # Clearly on-topic shapes need no model call.
    if (intent.resolve_confirmation(t, last_list) is not None
            or intent.is_order_history_question(t)
            or intent.is_preference_statement(t)
            or _is_short_reply(t)):
        return Verdict(True, "rule")
    return _check_text(t, last_reply)


SHORT_REPLY = re.compile(
    r"^(yes|yeah|yep|no|nope|maybe|not sure|ok|okay|sure|thanks|thank you|hi|hello|hey|"
    r"#?\d+|the (first|second|third|fourth|fifth|last) one)[\s.!?]*$",
    re.IGNORECASE,
)


def _is_short_reply(t: str) -> bool:
    return bool(SHORT_REPLY.match(t))


def _check_text(text: str, last_reply: str | None) -> Verdict:
    context = f"ShopMate's previous reply:\n{last_reply[:600]}\n\n" if last_reply else ""
    content = _ask(GUARDRAIL_MODEL, LLM_REASONING_EFFORT, [
        {"role": "system", "content": TEXT_PROMPT},
        {"role": "user", "content": f"{context}Shopper's message:\n{text}"},
    ])
    data = _parse(content)
    if data is None or "on_topic" not in data:
        # Fail open: the agent's own prompt also keeps it to shopping.
        return Verdict(True, "check-failed")
    return Verdict(str(data["on_topic"]).lower() == "true", "text-check")


def _check_image(image_bytes: bytes, mime: str) -> Verdict:
    mime, b64 = prepare_image(image_bytes)
    content = _ask(VISION_MODEL, VISION_REASONING_EFFORT, [{
        "role": "user",
        "content": [
            {"type": "text", "text": IMAGE_PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ],
    }])
    data = _parse(content)
    if data is None:
        # An unreadable photo cannot be searched anyway; redirect rather than guess.
        return Verdict(False, "check-failed")
    on_topic = str(data.get("is_grocery_product")).lower() == "true"
    description = {k: data.get(k) for k in ("product", "search_keyword", "looks_organic")} if on_topic else None
    return Verdict(on_topic, "image-check", description)


def _ask(model: str, effort: str, messages: list[dict]) -> str:
    try:
        resp = groq_client().chat.completions.create(
            model=model,
            temperature=LLM_TEMPERATURE,
            reasoning_effort=effort,
            max_tokens=TOOL_MAX_TOKENS,
            messages=messages,
        )
    except RateLimitError as exc:
        raise busy_error(exc) from exc
    return resp.choices[0].message.content or ""


def _parse(text: str) -> dict | None:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
