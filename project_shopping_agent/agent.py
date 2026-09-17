"""ShopMate agent: tool-calling loop plus the output contract (PRD §6.3)."""

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime

from groq import BadRequestError, Groq, RateLimitError

import db
import guardrails
import intent
import tools
from config import (AGENT_MAX_TOKENS, HISTORY_MESSAGES, LLM_MODEL, LLM_REASONING_EFFORT, LLM_TEMPERATURE,
                    MAX_AGENT_STEPS, MAX_RATE_LIMIT_WAIT, OFF_TOPIC_REPLY, ROOT, SINGLE_ITEM_PROMPT,
                    TOOL_CALL_RETRIES, busy_error, groq_client, retry_after_seconds)
from initial_setup.reviews_api import get_product_rating

LOG_PATH = ROOT / "logs" / "turns.jsonl"

SYSTEM_PROMPT = f"""You are ShopMate, the shopping assistant for a small online pantry store.
The store sells 32 products: honey, oils, nuts and seeds, grains, tea and coffee, snacks, and dairy alternatives.

BROWSING
- When the shopper describes what they want, call search_products with a short keyword and any price cap or organic filter they stated.
- Then call get_rating ONCE with product_ids set to ALL result IDs.
- If the shopper stated a minimum rating, show only products whose average_rating meets it.
- If they ask for the cheapest, show only the lowest-priced match.
- Never order while browsing.
- If nothing matches, say the store has no matching product. Never invent products, prices or ratings.

PHOTO SEARCH
- If the shopper attached a photo, call describe_product_image first, then continue with browsing using its search_keyword.
  looks_organic is information only: do not set is_organic unless the shopper asked for organic.

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
EMPTY_REPLY_NUDGE = (
    "SYSTEM CHECK: you have not written a reply yet. If you still need ratings for any search result, "
    "call get_rating for them. Then write your reply to the shopper using the product list format."
)
EMPTY_REPLY_FALLBACK = "Sorry, I couldn't put that answer together. Please try asking again."
NO_ORDER_FALLBACK = (
    "No new order was placed. To order, search for a product and then reply "
    "\"yes\" or the item number from the list."
)
PREFERENCE_CLAIM = re.compile(r"\b(saved|i'?ll remember|noted|from now on|going forward)\b", re.IGNORECASE)
NO_PREFERENCE_FALLBACK = (
    "I haven't saved a preference. To set one, say for example \"I always want organic\" "
    "or \"never show me anything over $20\"."
)

# Used only when the list has to be built in code (see list_from_search).
MIN_RATING_AT_LEAST = re.compile(
    r"(\d(?:\.\d+)?)\s*\+|(?:at least|minimum|min\.?|or more)\s*(?:a\s*)?(?:rating\s*(?:of\s*)?)?(\d(?:\.\d+)?)"
)
MIN_RATING_ABOVE = re.compile(r"(?:above|over|more than|higher than|greater than)\s*(\d(?:\.\d+)?)")


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
    blocked: bool = False  # True when GR-01 stopped the message before the agent


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
            retryable = "tool_use_failed" in str(exc) or "output_parse_failed" in str(exc)
            if not retryable or bad_calls > TOOL_CALL_RETRIES:
                raise
        except RateLimitError as exc:
            # The SDK already retried. Wait out a per-minute window; give up on a daily one.
            rate_limited += 1
            wait = retry_after_seconds(str(exc))
            if wait is None or wait > MAX_RATE_LIMIT_WAIT or rate_limited > 3:
                raise busy_error(exc) from exc
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


def list_from_search(calls: list[dict], user_text: str, ctx: tools.ToolContext | None = None) -> str:
    """Build the product list in code when the model searched but never wrote a reply.

    Uses the last search's real results and respects a stated minimum rating or
    "cheapest". For a photo with no search yet, searches the keyword the image
    check found.
    """
    searches = _called(calls, "search_products")
    if searches:
        results = searches[-1]["result"]["results"]
    elif ctx is not None and ctx.image_bytes and (ctx.image_description or {}).get("search_keyword"):
        results = tools.search_products(ctx, ctx.image_description["search_keyword"])["results"]
    else:
        return ""
    products = [db.get_product(p["id"]) for p in results]
    rated = [(p, get_product_rating(p["id"])) for p in products if p]
    text = user_text.lower()
    if "rating" in text or "star" in text or "+" in text:
        m = MIN_RATING_AT_LEAST.search(text)
        if m:
            floor = float(m.group(1) or m.group(2))
            rated = [(p, r) for p, r in rated if r["average_rating"] >= floor]
        else:
            m = MIN_RATING_ABOVE.search(text)
            if m:
                rated = [(p, r) for p, r in rated if r["average_rating"] > float(m.group(1))]
    if "cheapest" in text and rated:
        lowest = min(p["price"] for p, _ in rated)
        rated = [(p, r) for p, r in rated if p["price"] == lowest]
    if not rated:
        return "Sorry, the store has no product matching that."
    lines = "\n\n".join(format_product_line(i, p, r) for i, (p, r) in enumerate(rated, 1))
    ending = SINGLE_ITEM_PROMPT if len(rated) == 1 else "Which number would you like to order, if any?"
    return f"{lines}\n\n{ending}"


def _called(calls: list[dict], name: str) -> list[dict]:
    """Successful calls of one tool in this turn."""
    return [c for c in calls if c["name"] == name and "error" not in c["result"]]


def run_turn(session: Session, user_text: str, image_bytes: bytes | None = None,
             image_mime: str | None = None) -> TurnResult:
    # GR-01: off-topic messages and photos never reach the agent.
    last_reply = next((m["content"] for m in reversed(session.history) if m["role"] == "assistant"), None)
    verdict = guardrails.check(user_text, image_bytes, image_mime, session.last_list, last_reply)
    if not verdict.on_topic:
        session.history.append({"role": "user", "content": user_text.strip() or "(photo)"})
        session.history.append({"role": "assistant", "content": OFF_TOPIC_REPLY})
        _log_turn(user_text, bool(image_bytes), None, [], {}, OFF_TOPIC_REPLY, guardrail=verdict.reason)
        return TurnResult(reply=OFF_TOPIC_REPLY, tool_calls=[], blocked=True)

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
    ctx.image_description = verdict.image_description
    recent_user = [m["content"] for m in session.history if m["role"] == "user"][-2:]
    ctx.organic_requested = any("organic" in m.lower() for m in recent_user)
    system = SYSTEM_PROMPT + _last_list_note(session.last_list)
    if confirmed_id:
        system += f"\n\nThe shopper's latest message confirms product ID {confirmed_id}. Call checkout with it."
    messages = [{"role": "system", "content": system}, *session.history[-HISTORY_MESSAGES:]]
    calls: list[dict] = []
    usage = {"llm_calls": 0, "input_tokens": 0, "output_tokens": 0}

    try:
        reply = _agent_loop(client, messages, force_tool, ctx, calls, usage, user_text)
    except Exception:
        session.history.pop()  # keep history alternating user/assistant for the next try
        raise
    return _finish_turn(session, user_text, image_bytes, confirmed_id, wants_preference, calls, usage, reply)


def _agent_loop(client: Groq, messages: list[dict], force_tool: str | None, ctx: tools.ToolContext,
                calls: list[dict], usage: dict, user_text: str) -> str:
    reply = ""
    corrected = False
    nudged = False
    for step in range(MAX_AGENT_STEPS):
        try:
            msg = _complete(client, messages, force_tool if step == 0 else None, usage)
        except BadRequestError:
            # The model keeps producing unusable output. If it already searched,
            # answer from the real results; otherwise report the error.
            reply = list_from_search(calls, user_text, ctx)
            if reply:
                return reply
            raise
        if not msg.tool_calls:
            reply = _strip_thinking(msg.content)
            if not reply:
                # Some models stop after the tool calls without writing anything.
                if nudged:
                    reply = list_from_search(calls, user_text, ctx) or EMPTY_REPLY_FALLBACK
                    break
                nudged = True
                messages.append({"role": "user", "content": EMPTY_REPLY_NUDGE})
                continue
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
        reply = (list_from_search(calls, user_text, ctx)
                 or "Sorry, I couldn't finish that request. Could you try rephrasing it?")
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
              usage: dict, reply: str, guardrail: str | None = None) -> None:
    """Append-only log so a reported problem can be traced to the exact tool calls."""
    LOG_PATH.parent.mkdir(exist_ok=True)
    entry = {
        "at": datetime.now().isoformat(timespec="seconds"),
        "user": user_text, "image": has_image, "confirmed_product_id": confirmed_id,
        "tool_calls": [{"name": c["name"], "args": c["args"], "result": c["result"]} for c in calls],
        "blocked_by_guardrail": guardrail, "usage": usage, "reply": reply,
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
