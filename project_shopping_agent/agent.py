"""ShopMate agent: tool-calling loop plus the output contract (PRD §6.3)."""

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime

from groq import BadRequestError, Groq, RateLimitError

import db
import intent
import tools
from config import (AGENT_MAX_TOKENS, LLM_MODEL, LLM_REASONING_EFFORT, LLM_TEMPERATURE,
                    HISTORY_MESSAGES, MAX_AGENT_STEPS, MAX_RATE_LIMIT_WAIT, ROOT, SINGLE_ITEM_PROMPT,
                    TOOL_CALL_RETRIES, ServiceBusy, groq_client)

LOG_PATH = ROOT / "logs" / "turns.jsonl"
from initial_setup.reviews_api import get_product_rating

SYSTEM_PROMPT = f"""You are ShopMate, the shopping assistant for a small online pantry store.
The store sells 32 products: honey, oils, nuts and seeds, grains, tea and coffee, snacks, and dairy alternatives.

BROWSING
- When the shopper describes what they want, call search_products with a short keyword and any price cap or organic filter they stated.
- Then call get_rating for EVERY result (you may call it for several products at once).
- If the shopper stated a minimum rating, show only products whose average_rating meets it.
- If they ask for the cheapest, show only the lowest-priced match.
- Never order while browsing.
- If nothing matches, say the store has no matching product. Never invent products, prices or ratings.

PHOTO SEARCH
- If the shopper attached a photo, call describe_product_image first, then continue with browsing using its search_keyword.

PRODUCT LIST FORMAT (mandatory, plain text, one blank line between entries):
#1. Organic Raw Honey (ID:1) — $14.99 ★4.62 — organic

#2. Wildflower Honey (ID:2) — $12.99 ★3.83
- Add " — organic" only for organic products. Always include (ID:X).
- Do not write review counts; they are added automatically.
- If exactly one product qualifies, still show it as a list and end with: "{SINGLE_ITEM_PROMPT}"
- Otherwise end by asking which number they would like to order, if any.

ORDERING
- Only call checkout when the shopper's latest message clearly confirms: "yes" after a one-item list, or a number/position from the last list ("the second one", "order #3").
- Use the (ID:X) from the last list you showed. Never guess an ID.
- "maybe", "not sure", "no", or a question is NOT a confirmation. If they say "yes" but the last list had several products, ask which number.
- After checkout, confirm with the order ID, product name and price.

MEMORY
- "What have I ordered before?" -> call get_order_history.
- A standing preference ("I always want organic", "never show me anything over $20") -> call save_preference and confirm it is saved.
- Saved preferences are applied automatically inside search_products. If a search returns a "note", tell the shopper what it says; do not search for other products instead.

Each order is a single product; there is no cart. Do not talk about adding items, baskets, or reordering.
Stay on shopping in this store. Keep replies short."""

PRODUCT_LINE = re.compile(r"^\s*#(\d+)\.\s.*?\(ID:\s*(\d+)\).*$")

# A reply that claims an order exists. Only allowed after a successful checkout.
ORDER_CLAIM = re.compile(r"order\s*(id|#|number)|order\s+(has\s+been\s+|was\s+|is\s+)?placed|placed\s+(your|the|an)\s+order",
                         re.IGNORECASE)
ORDER_CLAIM_CORRECTION = (
    "SYSTEM CHECK: your reply says an order was placed, but checkout was not called successfully in this turn, "
    "so no order exists. If the shopper clearly confirmed a product from the last list, call checkout now. "
    "Otherwise, do not claim an order; ask them to confirm."
)
NO_ORDER_FALLBACK = (
    "No new order was placed. To order, search for a product and then reply "
    "\"yes\" or the item number from the list."
)


@dataclass
class Session:
    """Conversation state for one shopper session (resets when the app restarts)."""
    history: list[dict] = field(default_factory=list)   # user/assistant text only
    last_list: list[dict] = field(default_factory=list)  # products in the last list shown

    def record_assistant(self, text: str) -> None:
        self.history.append({"role": "assistant", "content": text})
        shown = parse_product_list(text)
        if shown:
            self.last_list = shown


@dataclass
class TurnResult:
    reply: str
    tool_calls: list[dict]
    usage: dict = field(default_factory=dict)  # llm_calls, input_tokens, output_tokens


def parse_product_list(text: str) -> list[dict]:
    items = []
    for line in text.splitlines():
        m = PRODUCT_LINE.match(line)
        if m:
            product = db.get_product(int(m.group(2)))
            if product:
                items.append({"position": int(m.group(1)), "id": product["id"], "name": product["name"]})
    return items


def format_product_line(position: int, product: dict, rating: dict) -> str:
    line = f"#{position}. {product['name']} (ID:{product['id']}) — ${product['price']:.2f} ★{rating['average_rating']:.2f}"
    return line + (" — organic" if product["is_organic"] else "")


def enforce_output_contract(text: str) -> str:
    """PRD FR-10..FR-14: rebuild every product line from store data.

    The model decides WHICH products to show; code guarantees the line format,
    the real price and rating, the review counts, and the single-item prompt.
    Lines pointing at an ID that does not exist are dropped.
    """
    out: list[str] = []
    counts: list[str] = []
    last_product_idx = None
    for line in text.splitlines():
        m = PRODUCT_LINE.match(line)
        if not m:
            out.append(line)
            continue
        product = db.get_product(int(m.group(2)))
        if not product:
            continue
        position = len(counts) + 1
        rating = get_product_rating(product["id"])
        # Exactly one blank line between entries.
        if last_product_idx is not None:
            del out[last_product_idx + 1:]
            out.append("")
        out.append(format_product_line(position, product, rating))
        last_product_idx = len(out) - 1
        counts.append(f"#{position} — {rating['review_count']} reviews")

    if not counts:
        return text.strip()

    out.insert(last_product_idx + 1, "")
    out.insert(last_product_idx + 2, "Review counts: " + ", ".join(counts))
    out.insert(last_product_idx + 3, "")
    result = "\n".join(out).strip()
    if len(counts) == 1 and SINGLE_ITEM_PROMPT not in result:
        result += "\n\n" + SINGLE_ITEM_PROMPT
    return re.sub(r"\n{3,}", "\n\n", result)


def _strip_thinking(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()


def _last_list_note(last_list: list[dict]) -> str:
    if not last_list:
        return "\n\nLAST LIST SHOWN: none yet."
    items = "; ".join(f"#{i['position']} {i['name']} (ID:{i['id']})" for i in last_list)
    return f"\n\nLAST LIST SHOWN: {items}"


def _retry_after_seconds(message: str) -> float | None:
    m = re.search(r"try again in ((?:\d+h)?(?:\d+m)?(?:[\d.]+s)?)", message)
    if not m or not m.group(1):
        return None
    parts = {unit: value for value, unit in re.findall(r"([\d.]+)([hms])", m.group(1))}
    return float(parts.get("h", 0)) * 3600 + float(parts.get("m", 0)) * 60 + float(parts.get("s", 0))


def _complete(client: Groq, messages: list[dict], force_tool: str | None, usage: dict):
    """One model call; retries malformed tool calls and short rate-limit waits."""
    tool_choice = {"type": "function", "function": {"name": force_tool}} if force_tool else "auto"
    bad_calls = 0
    rate_limited = 0
    while True:
        try:
            resp = client.chat.completions.create(
                model=LLM_MODEL,
                temperature=LLM_TEMPERATURE,
                reasoning_effort=LLM_REASONING_EFFORT,
                max_tokens=AGENT_MAX_TOKENS,
                messages=messages,
                tools=tools.TOOL_SCHEMAS,
                tool_choice=tool_choice,
            )
            if resp.usage:
                usage["input_tokens"] += resp.usage.prompt_tokens
                usage["output_tokens"] += resp.usage.completion_tokens
                usage["llm_calls"] += 1
            return resp.choices[0].message
        except BadRequestError as exc:
            bad_calls += 1
            if "tool_use_failed" not in str(exc) or bad_calls > TOOL_CALL_RETRIES:
                raise
        except RateLimitError as exc:
            # The SDK already retried. Wait out a per-minute window; give up on a daily one.
            rate_limited += 1
            wait = _retry_after_seconds(str(exc))
            if wait is None or wait > MAX_RATE_LIMIT_WAIT or rate_limited > 3:
                when = f" in about {int(wait // 60)} min {int(wait % 60)} s" if wait else " shortly"
                raise ServiceBusy(
                    "ShopMate has hit the Groq free-tier usage limit. "
                    f"Please try again{when}."
                ) from exc
            time.sleep(wait + 1)


# --- Replies written by code, from tool results (never by the model) --------

def order_confirmation(order: dict) -> str:
    return (
        "Order placed ✅\n\n"
        f"Order ID: {order['order_id']}\n"
        f"Product: {order['product_name']} (ID:{order['product_id']})\n"
        f"Price: ${order['price']:.2f}"
    )


def order_history_text(orders: list[dict]) -> str:
    if not orders:
        return "You haven't ordered anything yet."
    lines = [
        f"Order ID {o['id']} — {o['product_name']} — ${o['price']:.2f} — ordered {o['ordered_at'][:16]}"
        for o in orders
    ]
    return "Your past orders (newest first):\n\n" + "\n".join(lines)


def preference_text(prefs: dict) -> str:
    parts = []
    if prefs["organic_only"]:
        parts.append("only show organic products")
    if prefs["max_price"] is not None:
        parts.append(f"never show anything over ${prefs['max_price']:g}")
    if not parts:
        return "Preference saved. You have no standing filters now, so I'll show all products."
    return "Preference saved. From now on I'll " + " and ".join(parts) + "."


PREFERENCE_CLAIM = re.compile(r"\b(saved|i'?ll remember|noted|from now on|going forward)\b", re.IGNORECASE)
NO_PREFERENCE_FALLBACK = (
    "I haven't saved a preference. To set one, say for example \"I always want organic\" "
    "or \"never show me anything over $20\"."
)


def _called(calls: list[dict], name: str, ok: bool = True) -> list[dict]:
    return [c for c in calls if c["name"] == name and (not ok or "error" not in c["result"])]


def run_turn(session: Session, user_text: str, image_bytes: bytes | None = None,
             image_mime: str | None = None) -> TurnResult:
    client = groq_client()
    content = user_text.strip() or "Find this product."
    if image_bytes:
        content += "\n\n[The shopper attached a photo. Call describe_product_image to identify it.]"
    session.history.append({"role": "user", "content": content})

    # Decided in code before the model runs (intent.py).
    confirmed_id = None if image_bytes else intent.resolve_confirmation(user_text, session.last_list)
    wants_preference = not image_bytes and intent.is_preference_statement(user_text)
    wants_history = not image_bytes and intent.is_order_history_question(user_text)
    if wants_preference:
        force_tool = "save_preference"
    elif confirmed_id:
        force_tool = "checkout"
    elif wants_history:
        force_tool = "get_order_history"
    else:
        force_tool = None

    ctx = tools.ToolContext(image_bytes, image_mime, session.last_list, confirmed_id)
    system = SYSTEM_PROMPT + _last_list_note(session.last_list)
    if confirmed_id:
        system += f"\n\nThe shopper's latest message confirms product ID {confirmed_id}. Call checkout with it."
    messages = [{"role": "system", "content": system}, *session.history[-HISTORY_MESSAGES:]]
    calls: list[dict] = []
    usage = {"llm_calls": 0, "input_tokens": 0, "output_tokens": 0}

    try:
        reply = _agent_loop(client, messages, force_tool, ctx, calls, usage)
    except Exception:
        session.history.pop()  # keep history alternating user/assistant for the next try
        raise
    return _finish_turn(session, user_text, image_bytes, confirmed_id, wants_preference, calls, usage, reply)


def _agent_loop(client: Groq, messages: list[dict], force_tool: str | None, ctx: "tools.ToolContext",
                calls: list[dict], usage: dict) -> str:
    reply = ""
    corrected = False
    for step in range(MAX_AGENT_STEPS):
        msg = _complete(client, messages, force_tool if step == 0 else None, usage)
        if not msg.tool_calls:
            reply = _strip_thinking(msg.content)
            grounded = any(
                (c["name"] == "checkout" and "order_id" in c["result"]) or c["name"] == "get_order_history"
                for c in calls
            )
            if ORDER_CLAIM.search(reply) and not grounded:
                # FR-18 / must-never: an order confirmation must come from checkout.
                if corrected:
                    reply = NO_ORDER_FALLBACK
                    break
                corrected = True
                messages.append({"role": "assistant", "content": reply})
                messages.append({"role": "user", "content": ORDER_CLAIM_CORRECTION})
                continue
            break

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": c.id, "type": "function",
                 "function": {"name": c.function.name, "arguments": c.function.arguments}}
                for c in msg.tool_calls
            ],
        })
        for c in msg.tool_calls:
            try:
                args = tools.coerce_args(json.loads(c.function.arguments or "{}") or {})
            except json.JSONDecodeError:
                args = {}
            result = tools.run_tool(ctx, c.function.name, args)
            calls.append({"name": c.function.name, "args": args, "result": result})
            messages.append({"role": "tool", "tool_call_id": c.id, "content": json.dumps(result, default=str)})
        # An order or an order-history lookup fully answers the message; stop here.
        if _called(calls, "checkout") or _called(calls, "get_order_history"):
            break
    else:
        reply = "Sorry, I couldn't finish that request. Could you try rephrasing it?"
    return reply


def _finish_turn(session: Session, user_text: str, image_bytes: bytes | None, confirmed_id: int | None,
                 wants_preference: bool, calls: list[dict], usage: dict, reply: str) -> TurnResult:
    orders = _called(calls, "checkout")
    history = _called(calls, "get_order_history")
    saved = _called(calls, "save_preference")
    if orders:
        reply = order_confirmation(orders[-1]["result"])
    elif history:
        reply = order_history_text(history[-1]["result"]["orders"])
    elif saved:
        pref_line = preference_text(saved[-1]["result"]["saved_preferences"])
        reply = pref_line + ("\n\n" + reply if _called(calls, "search_products") and reply else "")
    elif PREFERENCE_CLAIM.search(reply) and wants_preference:
        reply = NO_PREFERENCE_FALLBACK
    elif confirmed_id:
        reply = NO_ORDER_FALLBACK

    reply = enforce_output_contract(reply)
    session.record_assistant(reply)
    if orders:
        # The list has been used; a later stray "yes" must not order it again.
        session.last_list = []
    _log_turn(user_text, bool(image_bytes), confirmed_id, calls, usage, reply)
    return TurnResult(reply=reply, tool_calls=calls, usage=usage)


def _log_turn(user_text: str, has_image: bool, confirmed_id: int | None, calls: list[dict],
              usage: dict, reply: str) -> None:
    """Append-only log so a reported problem can be traced to the exact tool calls."""
    LOG_PATH.parent.mkdir(exist_ok=True)
    entry = {
        "at": datetime.now().isoformat(timespec="seconds"),
        "user": user_text, "image": has_image, "confirmed_product_id": confirmed_id,
        "tool_calls": [{"name": c["name"], "args": c["args"], "result": c["result"]} for c in calls],
        "usage": usage, "reply": reply,
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
