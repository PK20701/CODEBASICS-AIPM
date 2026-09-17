"""The agent's tools (PRD §7): JSON schemas for the model plus their implementations."""

import base64
import json
import re
import sys

from groq import RateLimitError

import db
from config import (LLM_TEMPERATURE, ROOT, TOOL_MAX_TOKENS, VISION_MODEL, VISION_REASONING_EFFORT,
                    ServiceBusy,
                    groq_client)

sys.path.insert(0, str(ROOT))
from initial_setup.reviews_api import get_product_rating  # noqa: E402  (PRD FR-09)


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": (
                "Keyword search across product name, description and category. "
                "Use a short product keyword such as 'honey' or 'olive oil'; put 'organic' in "
                "is_organic, not in the keyword. Saved shopper preferences are applied automatically. "
                "Does not return ratings -- call get_rating for each result."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Product keyword, e.g. 'honey'."},
                    "max_price": {"type": ["number", "null"], "description": "Price cap in dollars, if the shopper stated one."},
                    "is_organic": {"type": ["boolean", "string", "null"], "description": "true only if the shopper asked for organic."},
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_rating",
            "description": "Average customer rating and review count for one product, from the reviews API.",
            "parameters": {
                "type": "object",
                "properties": {"product_id": {"type": "integer"}},
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "checkout",
            "description": (
                "Place an order for ONE product. Only call this after the shopper clearly confirmed "
                "a product from the last list you showed, using the (ID:X) from that list."
            ),
            "parameters": {
                "type": "object",
                "properties": {"product_id": {"type": "integer"}},
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_product_image",
            "description": (
                "Identify the product in the photo the shopper attached to their latest message. "
                "Returns the product, a search keyword and whether it looks organic."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_history",
            "description": "List the shopper's previous orders.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_preference",
            "description": (
                "Save a STANDING preference the shopper wants applied in future sessions, e.g. "
                "'I always want organic' or 'never show me anything over $20'. "
                "Do not use for a one-off constraint in a single search."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "organic_only": {"type": ["boolean", "string", "null"], "description": "true to always show organic only; false to stop."},
                    "max_price": {"type": ["number", "null"], "description": "Standing price cap in dollars."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_preferences",
            "description": "Return the shopper's saved standing preferences.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


class ToolContext:
    """Per-turn state the tools need but the model must not supply itself."""

    def __init__(self, image_bytes: bytes | None, image_mime: str | None, last_list: list[dict],
                 confirmed_product_id: int | None = None):
        self.image_bytes = image_bytes
        self.image_mime = image_mime or "image/png"
        # Products in the last list the shopper saw: [{"position", "id", "name"}].
        self.last_list = last_list
        # GR-02: the product the shopper's latest message clearly confirmed (intent.py), if any.
        self.confirmed_product_id = confirmed_product_id
        self.order_placed = False


# --- Implementations ------------------------------------------------------

def search_products(ctx: ToolContext, keyword: str, max_price: float | None = None,
                    is_organic: bool | None = None) -> dict:
    prefs = db.get_preferences()
    applied = []
    # PRD FR-25: saved preferences are enforced here, not left to the model.
    if prefs["organic_only"]:
        is_organic = True
        applied.append("organic only")
    if prefs["max_price"] is not None:
        max_price = prefs["max_price"] if max_price is None else min(max_price, prefs["max_price"])
        applied.append(f"max price ${prefs['max_price']:g}")

    products = db.search_products(keyword, max_price=max_price, is_organic=is_organic)
    note = None
    if not products and applied and db.search_products(keyword):
        # The store does sell it; the shopper's own saved preference hid it.
        note = (f"The store sells '{keyword}' but none of it matches the shopper's saved preference "
                f"({', '.join(applied)}). Tell the shopper that, and that they can change the preference.")
    return {
        "filters_used": {"keyword": keyword, "max_price": max_price, "is_organic": bool(is_organic)},
        "saved_preferences_applied": applied,
        "note": note,
        "results": [
            {"id": p["id"], "name": p["name"], "price": p["price"], "is_organic": bool(p["is_organic"])}
            for p in products
        ],
    }


def get_rating(ctx: ToolContext, product_id: int) -> dict:
    return get_product_rating(int(product_id))


def checkout(ctx: ToolContext, product_id: int) -> dict:
    product_id = int(product_id)
    # PRD FR-17: the ID must come from the list the shopper was shown.
    if product_id not in {item["id"] for item in ctx.last_list}:
        return {"error": f"Product ID {product_id} is not in the last list shown to the shopper. Do not guess IDs."}
    # GR-02: code-level check that the shopper clearly said yes to THIS product.
    if ctx.confirmed_product_id is None:
        return {"error": "NOT ORDERED: the shopper's latest message is not a clear confirmation. "
                         "Do not order. Ask them to confirm with yes or the item number."}
    if product_id != ctx.confirmed_product_id:
        return {"error": f"NOT ORDERED: the shopper confirmed product ID {ctx.confirmed_product_id}, "
                         f"not {product_id}."}
    if ctx.order_placed:
        return {"error": "NOT ORDERED: an order was already placed for this message. One product per order."}
    product = db.get_product(product_id)
    if not product:
        return {"error": f"Product ID {product_id} does not exist."}
    order = db.create_order(product)
    ctx.order_placed = True
    return {
        "order_id": order["id"],
        "product_id": order["product_id"],
        "product_name": order["product_name"],
        "price": order["price"],
        "ordered_at": order["ordered_at"],
    }


def describe_product_image(ctx: ToolContext) -> dict:
    if not ctx.image_bytes:
        return {"error": "The shopper has not attached a photo to this message."}
    b64 = base64.b64encode(ctx.image_bytes).decode()
    client = groq_client()
    try:
        resp = _describe(client, b64, ctx.image_mime)
    except RateLimitError as exc:
        raise ServiceBusy("ShopMate has hit the Groq free-tier usage limit. Please try again later.") from exc
    return _parse_json(resp.choices[0].message.content or "")


def _describe(client, b64: str, mime: str):
    return client.chat.completions.create(
        model=VISION_MODEL,
        temperature=LLM_TEMPERATURE,
        reasoning_effort=VISION_REASONING_EFFORT,
        max_tokens=TOOL_MAX_TOKENS,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": (
                    "Identify the grocery product in this photo. Reply with JSON only: "
                    '{"product": "<what it is>", "search_keyword": "<one or two generic words, e.g. honey>", '
                    '"looks_organic": true|false, "is_product": true|false}'
                )},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ],
        }],
    )


def get_order_history(ctx: ToolContext) -> dict:
    return {"orders": db.list_orders()}


def save_preference(ctx: ToolContext, organic_only: bool | None = None, max_price: float | None = None) -> dict:
    if organic_only is not None:
        db.set_preference("organic_only", "1" if organic_only else None)
    if max_price is not None:
        db.set_preference("max_price", str(float(max_price)))
    return {"saved_preferences": db.get_preferences()}


def get_preferences(ctx: ToolContext) -> dict:
    return {"saved_preferences": db.get_preferences()}


TOOLS = {
    "search_products": search_products,
    "get_rating": get_rating,
    "checkout": checkout,
    "describe_product_image": describe_product_image,
    "get_order_history": get_order_history,
    "save_preference": save_preference,
    "get_preferences": get_preferences,
}


BOOL_ARGS = {"is_organic", "organic_only"}
NUMBER_ARGS = {"max_price"}
INT_ARGS = {"product_id"}


def coerce_args(args: dict) -> dict:
    """The model sometimes sends "True" or "20" as strings; normalise before use."""
    out = {}
    for key, value in args.items():
        if value is None or value == "":
            continue
        try:
            if key in BOOL_ARGS and isinstance(value, str):
                value = value.strip().lower() in ("true", "yes", "1")
            elif key in NUMBER_ARGS:
                value = float(str(value).replace("$", ""))
            elif key in INT_ARGS:
                value = int(str(value).replace("#", ""))
        except ValueError:
            continue
        out[key] = value
    return out


def run_tool(ctx: ToolContext, name: str, args: dict) -> dict:
    fn = TOOLS.get(name)
    if fn is None:
        return {"error": f"Unknown tool {name}."}
    try:
        return fn(ctx, **args)
    except TypeError as exc:
        return {"error": f"Bad arguments for {name}: {exc}"}


def _parse_json(text: str) -> dict:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    match = re.search(r"\{.*\}", text, flags=re.S)
    try:
        return json.loads(match.group(0)) if match else {"error": "Could not read the image."}
    except json.JSONDecodeError:
        return {"error": "Could not read the image."}
