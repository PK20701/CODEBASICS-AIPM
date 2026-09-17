"""Live end-to-end checks: the six Step 2 checks from assignment.md plus the
ordering and preference edge cases that broke before. Calls Groq.

Run: .venv\\Scripts\\python.exe tests\\test_assignment_checks.py [rounds] [--test-model MODEL]

--test-model runs the agent on another Groq model (e.g. openai/gpt-oss-120b)
so testing does not use up the app model's free daily quota. That model has
no image input, so the photo check is skipped in that mode.

Orders and preferences created by the test are removed at the end.
"""

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ARGS = argparse.ArgumentParser()
ARGS.add_argument("rounds", nargs="?", type=int, default=3)
ARGS.add_argument("--test-model", help="Groq model to use instead of GROQ_MODEL from .env")
OPTS = ARGS.parse_args()
if OPTS.test_model:
    # Must be set before config.py loads .env (load_dotenv does not override).
    os.environ["GROQ_MODEL"] = OPTS.test_model
    os.environ["GROQ_REASONING_EFFORT"] = "low" if OPTS.test_model.startswith("openai/gpt-oss") else "none"

import db  # noqa: E402
from agent import Session, parse_product_list, run_turn  # noqa: E402
from config import DB_PATH, SINGLE_ITEM_PROMPT  # noqa: E402

HONEY_IDS = set(range(1, 9))
ORGANIC_HONEY_IDS = {1, 3, 5, 7}
results: list[tuple[str, bool, str]] = []


def order_ids() -> list[int]:
    with sqlite3.connect(DB_PATH) as conn:
        return [r[0] for r in conn.execute("SELECT id FROM orders ORDER BY id")]


def clear_preferences() -> None:
    db.set_preference("organic_only", None)
    db.set_preference("max_price", None)


def turn(session: Session, text: str, image: bytes | None = None):
    r = run_turn(session, text, image, "image/png" if image else None)
    time.sleep(6)  # stay under Groq's free-tier tokens-per-minute limit
    return r, [i["id"] for i in parse_product_list(r.reply)], [c["name"] for c in r.tool_calls]


def check(name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"\n        {detail}"), flush=True)


def one_round(n: int) -> None:
    print(f"\n=== Round {n} ===", flush=True)
    clear_preferences()

    # 1. organic honey with 4.5+ rating under $20
    s = Session()
    before = order_ids()
    r, shown, names = turn(s, "organic honey with 4.5+ rating under $20")
    search = [c for c in r.tool_calls if c["name"] == "search_products"]
    check("1 filters: shows exactly Raw, Buckwheat, Acacia", set(shown) == {1, 5, 7}, f"shown={shown}\n{r.reply}")
    check("1 filters: search used organic + $20 cap",
          bool(search) and search[0]["args"].get("is_organic") is True and search[0]["args"].get("max_price") == 20,
          f"search={search[:1]}")
    check("1 filters: no order placed", order_ids() == before, f"tools={names}")

    # 2. cheapest oat milk
    s = Session()
    r, shown, names = turn(s, "cheapest oat milk")
    check("2 cheapest: Oat Milk at $4.49 only", shown == [30] and "$4.49" in r.reply, f"shown={shown}\n{r.reply}")
    check("2 cheapest: single-item order prompt", SINGLE_ITEM_PROMPT in r.reply, r.reply)

    # 2b. "maybe" does not order
    before = order_ids()
    r, _, names = turn(s, "maybe")
    check("2b 'maybe': no order", order_ids() == before, f"tools={names}\n{r.reply}")

    # 4. yes after a single-item list
    before = order_ids()
    r, _, names = turn(s, "yes")
    new = [i for i in order_ids() if i not in before]
    check("4 yes: exactly one new order", len(new) == 1, f"new orders={new} tools={names}\n{r.reply}")
    new_id = new[0] if new else None
    check("4 yes: reply shows the order ID", new_id is not None and f"Order ID: {new_id}" in r.reply, r.reply)
    check("4 yes: ordered Oat Milk", "Oat Milk" in r.reply, r.reply)

    # 4b. a stray "yes" after ordering does not order again
    before = order_ids()
    r, _, names = turn(s, "yes")
    check("4b second 'yes': no repeat order", order_ids() == before, f"tools={names}\n{r.reply}")

    # 5. order history, same session and after restart
    for label, sess in (("same session", s), ("new session", Session())):
        before = order_ids()
        r, _, names = turn(sess, "what have I ordered before?")
        check(f"5 history ({label}): no order placed", order_ids() == before, f"tools={names}\n{r.reply}")
        check(f"5 history ({label}): lists the order just placed",
              "get_order_history" in names and new_id is not None and f"Order ID {new_id} — Oat Milk" in r.reply,
              f"tools={names}\n{r.reply}")

    # Multi-item list: "yes" asks which; "the second one" orders #2
    s = Session()
    turn(s, "organic honey with 4.5+ rating under $20")
    before = order_ids()
    r, _, names = turn(s, "yes")
    check("multi 'yes': no order, asks which", order_ids() == before, f"tools={names}\n{r.reply}")
    r, _, names = turn(s, "the second one")
    new = [i for i in order_ids() if i not in before]
    check("multi 'the second one': orders Buckwheat (ID 5)",
          len(new) == 1 and "Organic Buckwheat Honey" in r.reply and f"Order ID: {new[0]}" in r.reply,
          f"new={new} tools={names}\n{r.reply}")

    # 3. photo search (needs an image-capable model)
    if OPTS.test_model:
        print("  SKIP  3 photo: test model has no image input", flush=True)
    else:
        photo_check()

    preference_checks()


def photo_check() -> None:
    s = Session()
    before = order_ids()
    r, shown, names = turn(s, "find this", (ROOT / "resources" / "honey.png").read_bytes())
    check("3 photo: identified the image", "describe_product_image" in names, f"tools={names}")
    check("3 photo: shows a list of honeys", bool(shown) and set(shown) <= HONEY_IDS, f"shown={shown}\n{r.reply}")
    check("3 photo: no order placed", order_ids() == before, f"tools={names}")


def preference_checks() -> None:
    # 6. preference persists across restart
    s = Session()
    r, _, names = turn(s, "I always want organic")
    check("6 pref: save_preference called and stored",
          "save_preference" in names and db.get_preferences()["organic_only"], f"tools={names} prefs={db.get_preferences()}")
    check("6 pref: reply confirms it", "Preference saved" in r.reply, r.reply)
    for query in ("honey", "show me honey"):
        s = Session()  # app restart
        r, shown, names = turn(s, query)
        check(f"6 after restart '{query}': organic honeys only",
              set(shown) == ORGANIC_HONEY_IDS, f"shown={shown}\n{r.reply}")

    # Price-cap preference on top of organic
    s = Session()
    r, _, names = turn(s, "never show me anything over $20")
    check("pref cap: stored $20", db.get_preferences()["max_price"] == 20, f"tools={names} prefs={db.get_preferences()}")
    s = Session()
    r, shown, _ = turn(s, "honey")
    check("pref cap after restart: organic honeys under $20", set(shown) == {1, 5, 7}, f"shown={shown}\n{r.reply}")
    clear_preferences()


def main() -> int:
    rounds = OPTS.rounds
    from config import LLM_MODEL
    print(f"Agent model: {LLM_MODEL}", flush=True)
    start_orders = set(order_ids())
    saved_prefs = db.get_preferences()
    try:
        for n in range(1, rounds + 1):
            one_round(n)
    finally:
        created = [i for i in order_ids() if i not in start_orders]
        with sqlite3.connect(DB_PATH) as conn:
            conn.executemany("DELETE FROM orders WHERE id = ?", [(i,) for i in created])
        clear_preferences()
        if saved_prefs["organic_only"]:
            db.set_preference("organic_only", "1")
        if saved_prefs["max_price"] is not None:
            db.set_preference("max_price", str(saved_prefs["max_price"]))
        print(f"\nCleaned up {len(created)} test orders; preferences restored.")

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed over {rounds} round(s)")
    for name, _, detail in failed:
        print(f"FAILED: {name}\n  {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
