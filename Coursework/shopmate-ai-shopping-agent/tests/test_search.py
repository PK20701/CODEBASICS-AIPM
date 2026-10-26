"""Offline checks for keyword search (db.search_products). Read-only: no orders or preferences change.

Run: .venv\\Scripts\\python.exe tests\\test_search.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import search_products  # noqa: E402

CASES = [
    # (keyword, max_price, is_organic, expected ids)
    ("honey", None, None, [1, 2, 3, 4, 5, 6, 7, 8]),      # not Organic Granola ("...with honey")
    ("honey", 20, True, [1, 5, 7]),                        # no Manuka ($29.99)
    ("honeys", None, None, [1, 2, 3, 4, 5, 6, 7, 8]),     # plural falls back to singular
    ("raw honey", None, None, [1]),
    ("oat milk", None, None, [30]),
    ("oats", None, None, [18, 20]),                        # not Oat Milk
    ("oats", None, True, []),                              # organic oats: none, not granola
    ("olive oil", None, None, [9]),
    ("granola", None, None, [25]),
    ("almond butter", None, None, []),
    ("milk", 4.0, None, [31, 32]),
]


def main() -> int:
    failures = 0
    for keyword, max_price, organic, expected in CASES:
        got = [p["id"] for p in search_products(keyword, max_price, organic)]
        ok = got == expected
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {keyword!r} max={max_price} organic={organic} -> {got}"
              + ("" if ok else f" (expected {expected})"))
    print(f"\n{len(CASES) - failures}/{len(CASES)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
