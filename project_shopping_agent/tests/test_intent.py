"""Offline checks for the rule-based confirmation and preference detection.

Run: .venv\\Scripts\\python.exe tests\\test_intent.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from intent import is_order_history_question, is_preference_statement, resolve_confirmation  # noqa: E402

ONE = [{"position": 1, "id": 30, "name": "Oat Milk"}]
THREE = [
    {"position": 1, "id": 1, "name": "Organic Raw Honey"},
    {"position": 2, "id": 5, "name": "Organic Buckwheat Honey"},
    {"position": 3, "id": 7, "name": "Organic Acacia Honey"},
]

CONFIRMATION_CASES = [
    # (message, last list, expected product id)
    ("yes", ONE, 30),
    ("Yes please", ONE, 30),
    ("yes, order it", ONE, 30),
    ("ok", ONE, 30),
    ("sure", ONE, 30),
    ("go ahead", ONE, 30),
    ("1", ONE, 30),
    ("#1", ONE, 30),
    ("order it", ONE, 30),
    ("the second one", THREE, 5),
    ("order #3", THREE, 7),
    ("I'll take #1", THREE, 1),
    ("number 2 please", THREE, 5),
    ("2", THREE, 5),
    ("I want the third one", THREE, 7),
    ("yes, the first one", THREE, 1),
    ("order the organic acacia honey", THREE, 7),
    # Not confirmations
    ("yes", THREE, None),            # which one?
    ("maybe", ONE, None),
    ("not sure", ONE, None),
    ("no", ONE, None),
    ("no thanks", ONE, None),
    ("maybe the second one", THREE, None),
    ("don't order #2", THREE, None),
    ("tell me more about #2", THREE, None),
    ("what about the second one?", THREE, None),
    ("order #9", THREE, None),       # not in list
    ("what have I ordered before?", ONE, None),
    ("what have I ordered before?", THREE, None),
    ("cheapest oat milk", ONE, None),
    ("honey", THREE, None),
    ("I always want organic", ONE, None),
    ("yes", [], None),               # nothing shown yet
]

PREFERENCE_CASES = [
    ("I always want organic", True),
    ("never show me anything over $20", True),
    ("From now on only organic please", True),
    ("I no longer want organic only", True),
    ("organic honey under $20", False),
    ("honey", False),
    ("what have I ordered before?", False),
    ("yes", False),
]


HISTORY_CASES = [
    ("what have I ordered before?", True),
    ("What did I order before", True),
    ("show my past orders", True),
    ("order history", True),
    ("what have i bought before?", True),
    ("order #2", False),
    ("yes", False),
    ("honey", False),
    ("cheapest oat milk", False),
]


def main() -> int:
    failures = 0
    for text, expected in HISTORY_CASES:
        got = is_order_history_question(text)
        ok = got == expected
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  history {text!r} -> {got} (expected {expected})")
    for text, last_list, expected in CONFIRMATION_CASES:
        got = resolve_confirmation(text, last_list)
        ok = got == expected
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  confirm {text!r} (list of {len(last_list)}) -> {got} (expected {expected})")
    for text, expected in PREFERENCE_CASES:
        got = is_preference_statement(text)
        ok = got == expected
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  preference {text!r} -> {got} (expected {expected})")
    total = len(CONFIRMATION_CASES) + len(PREFERENCE_CASES) + len(HISTORY_CASES)
    print(f"\n{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
