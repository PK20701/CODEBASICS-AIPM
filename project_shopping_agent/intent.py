"""Rule-based reading of the shopper's latest message.

These decisions are too important to leave to the model:
- PRD FR-16 / GR-02: did the shopper clearly confirm a product from the last list?
- PRD FR-22: is this an order-history question that must hit the orders table?
- PRD FR-23: is this a standing preference that must be saved?
"""

import re

NOT_A_YES = re.compile(
    r"\b(maybe|perhaps|not sure|unsure|no|nope|not|don'?t|do not|cancel|wait|later|hmm+|might|"
    r"undecided|think about|what|which|how|why|tell me|show me|more about|compare)\b"
)
YES = re.compile(
    r"^(yes|yeah|yep|yup|sure|ok|okay|confirm|confirmed|please do|go ahead|do it|sounds good|"
    r"order it|buy it|get it|i'?ll take it|take it|yes please|yes,? order it|place the order|place order)\b"
)
ORDER_VERB = re.compile(r"\b(order|buy|take|get|purchase|checkout|check out|go with|choose|pick|want|i'?ll have)\b")
ORDINALS = {
    "first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3, "fourth": 4, "4th": 4,
    "fifth": 5, "5th": 5, "sixth": 6, "6th": 6, "seventh": 7, "7th": 7, "eighth": 8, "8th": 8,
}
POSITION = re.compile(
    r"(?:#\s*(\d+)|\b(?:number|no\.?|item|option)\s*#?\s*(\d+)\b|\b("
    + "|".join(ORDINALS) + r")\b(?:\s+one)?|^\s*(\d+)\s*$)"
)


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("’", "'")).strip(" .!")


def resolve_confirmation(text: str, last_list: list[dict]) -> int | None:
    """Return the product ID the shopper clearly confirmed, or None.

    last_list: [{"position", "id", "name"}] from the last product list shown.
    """
    if not last_list:
        return None
    t = _normalise(text)
    by_position = {item["position"]: item["id"] for item in last_list}

    m = POSITION.search(t)
    if m:
        if NOT_A_YES.search(t) and not ORDER_VERB.search(t):
            return None
        if re.search(r"\b(maybe|perhaps|not sure|don'?t|do not|cancel|not)\b", t):
            return None
        pos = m.group(1) or m.group(2) or m.group(4)
        pos = int(pos) if pos else ORDINALS[m.group(3)]
        short = len(t.split()) <= 4
        if ORDER_VERB.search(t) or YES.search(t) or short:
            return by_position.get(pos)
        return None

    if re.search(r"\b(maybe|perhaps|not sure|unsure|don'?t|do not|cancel|no|nope|not)\b", t):
        return None

    if YES.search(t) and len(last_list) == 1:
        return last_list[0]["id"]

    # "order the organic raw honey"
    if ORDER_VERB.search(t):
        named = [item["id"] for item in last_list if item["name"].lower() in t]
        if len(named) == 1:
            return named[0]
    return None


ORDER_HISTORY = re.compile(
    r"\b(ordered|did i (order|buy)|order history|past orders?|previous orders?|my orders?|orders? (i|i've) (placed|made)|"
    r"bought before|purchased before|purchase history)\b"
)


def is_order_history_question(text: str) -> bool:
    """PRD FR-22: "what have I ordered before?" must be answered from the orders table."""
    t = _normalise(text)
    return bool(ORDER_HISTORY.search(t))


PREFERENCE = re.compile(
    r"\b(always|never|from now on|going forward|in future|in the future|every time|no longer|"
    r"stop showing|don'?t show me|remember)\b"
)
PREFERENCE_TOPIC = re.compile(r"\b(organic|over|under|above|more than|less than|price|\$|expensive)")


def is_preference_statement(text: str) -> bool:
    t = _normalise(text)
    return bool(PREFERENCE.search(t) and PREFERENCE_TOPIC.search(t))
