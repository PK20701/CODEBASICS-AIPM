"""Eval runner for eval_set.csv.

For each row of eval_set.csv:
  1. apply the setup (previous product list, saved preference, existing order, photo),
  2. send the shopper's message to the agent,
  3. check the expected tool was called with the expected filters (automatic),
  4. print the agent's reply next to the expected reply so it can be checked by hand.

Results go to eval_runs/run_<timestamp>.csv (with empty manual_check / notes columns)
and a Markdown copy of the same table.

Run:  .venv\\Scripts\\python.exe run_evals.py [--app-model | --model NAME] [--only E01,E03]

Chat runs on openai/gpt-oss-120b unless --app-model or --model is given
(tests/live_models.py), so evals don't use up Qwen's free daily quota.
Photos use the vision model in .env.
Orders created by the run are removed and saved preferences are restored.
"""

import argparse
import csv
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tests"))
import live_models  # noqa: E402,F401  (must come before project imports)

import db  # noqa: E402
from agent import Session, parse_product_list, run_turn  # noqa: E402
from config import DB_PATH, GUARDRAIL_MODEL, LLM_MODEL, VISION_MODEL, ServiceBusy  # noqa: E402

EVAL_SET = ROOT / "eval_set.csv"
RUNS_DIR = ROOT / "eval_runs"
TOOL_NAMES = ["search_products", "get_rating", "checkout", "describe_product_image",
              "get_order_history", "save_preference", "get_preferences"]
LIST_ITEM = re.compile(r"#(\d+)\.\s*([^#(]+?)\s*\(ID:(\d+)\)")


# --- Setup -----------------------------------------------------------------

def order_ids() -> list[int]:
    with sqlite3.connect(DB_PATH) as conn:
        return [r[0] for r in conn.execute("SELECT id FROM orders ORDER BY id")]


def clear_preferences() -> None:
    db.set_preference("organic_only", None)
    db.set_preference("max_price", None)


def apply_setup(setup: str, session: Session) -> tuple[bytes | None, list[str]]:
    """Returns (image bytes, notes). Unknown setup text is reported, not ignored."""
    notes: list[str] = []
    image = None
    if not setup.strip():
        return image, notes

    m = re.search(r"Image:\s*(\S+)", setup, re.IGNORECASE)
    if m:
        image = (ROOT / m.group(1)).read_bytes()

    items = LIST_ITEM.findall(setup)
    if items:
        shown = "\n\n".join(f"#{pos}. {name.strip()} (ID:{pid})" for pos, name, pid in items)
        session.history.append({"role": "user", "content": "Show me some options."})
        session.record_assistant(shown)

    if re.search(r"saved preference:\s*organic only", setup, re.IGNORECASE):
        db.set_preference("organic_only", "1")

    if re.search(r"order exists", setup, re.IGNORECASE):
        order = db.create_order(db.get_product(30))
        notes.append(f"setup created order {order['id']} (Oat Milk)")

    if not (m or items or "preference" in setup.lower() or "order exists" in setup.lower()):
        notes.append(f"SETUP NOT UNDERSTOOD: {setup}")
    return image, notes


# --- Automatic tool / filter check ------------------------------------------

def parse_filters(text: str) -> dict:
    filters = {}
    for part in text.split(","):
        if "=" not in part:
            continue
        key, value = (s.strip().lower() for s in part.split("=", 1))
        if key == "organic":
            filters["is_organic"] = value in ("yes", "true")
        elif key == "max price":
            filters["max_price"] = float(value.replace("$", ""))
        elif key == "search":
            filters["keyword"] = value
        elif key == "product id":
            filters["product_id"] = int(value)
    return filters


def call_matches(call: dict, filters: dict) -> bool:
    if call["name"] == "search_products":
        used = call["result"].get("filters_used", {})  # what was really applied, incl. saved preferences
        for key, want in filters.items():
            if key == "keyword" and want not in str(call["args"].get("keyword", "")).lower():
                return False
            if key == "is_organic" and bool(used.get("is_organic")) != want:
                return False
            if key == "max_price" and used.get("max_price") != want:
                return False
        return True
    for key, want in filters.items():
        got = call["args"].get(key)
        if got is None or (float(got) if key == "max_price" else got) != want:
            return False
    return "error" not in call["result"]


def auto_check(row: dict, result, new_orders: list[int]) -> tuple[str, str]:
    expected = row["expected_tool"].lower()
    calls = result.tool_calls
    names = [c["name"] for c in calls]
    problems: list[str] = []
    info: list[str] = []
    if not result.reply.strip():
        problems.append("reply is empty")
    refused = [c["args"] for c in calls if c["name"] == "checkout" and "error" in c["result"]]
    if refused:
        info.append(f"checkout attempted but refused by code (GR-02): {refused}")

    if expected.startswith("none"):
        if "guardrail" in expected:
            if not result.blocked:
                problems.append("guardrail did not block")
            if calls:
                problems.append(f"tools were called: {names}")
        if new_orders:
            problems.append(f"order placed: {new_orders}")
        return ("PASS" if not problems else "FAIL"), "; ".join(problems + info)

    wanted = [t for t in TOOL_NAMES if t in expected]
    for tool in wanted:
        if tool not in names:
            problems.append(f"{tool} not called")

    filters = parse_filters(row["expected_filters"])
    primary = wanted[0] if wanted else None
    if primary and filters and not any(call_matches(c, filters) for c in calls if c["name"] == primary):
        got = [c["args"] for c in calls if c["name"] == primary]
        problems.append(f"{primary} filters {filters} not matched; got {got}")

    if "for each result" in expected:
        searched = {p["id"] for c in calls if c["name"] == "search_products" for p in c["result"].get("results", [])}
        rated = {r["product_id"] for c in calls if c["name"] == "get_rating"
                 for r in c["result"].get("ratings", [])}
        if searched - rated:
            problems.append(f"no rating fetched for {sorted(searched - rated)}")

    if "checkout" in wanted:
        if len(new_orders) != 1:
            problems.append(f"expected 1 new order, found {len(new_orders)}")
    elif new_orders:
        problems.append(f"unexpected order placed: {new_orders}")

    return ("PASS" if not problems else "FAIL"), "; ".join(problems + info)


# --- Run ---------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="comma-separated row ids, e.g. E01,E03")
    args = parser.parse_args()

    with EVAL_SET.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if args.only:
        wanted = {x.strip().upper() for x in args.only.split(",")}
        rows = [r for r in rows if r["id"].upper() in wanted]

    started = datetime.now()
    print(f"Eval run {started:%Y-%m-%d %H:%M} | agent: {LLM_MODEL} | guardrail: {GUARDRAIL_MODEL} | vision: {VISION_MODEL}")
    start_orders = set(order_ids())
    saved_prefs = db.get_preferences()
    out: list[dict] = []

    try:
        for row in rows:
            clear_preferences()
            session = Session()
            image, notes = apply_setup(row["setup"], session)
            before = order_ids()
            not_run = False
            try:
                result = run_turn(session, row["shopper_says"], image, "image/png" if image else None)
            except ServiceBusy as exc:  # quota, not the agent: re-run later with --only
                result, not_run = None, True
                notes.append(f"NOT RUN: {exc}")
            except Exception as exc:  # record and continue with the next row
                result = None
                notes.append(f"ERROR: {exc}")
            new_orders = [i for i in order_ids() if i not in before]

            if result is None:
                check = "NOT RUN" if not_run else "FAIL"
                detail, reply, called, tokens = "; ".join(notes), "", "", ""
            else:
                check, detail = auto_check(row, result, new_orders)
                detail = "; ".join([*notes, detail] if detail else notes)
                reply = result.reply
                called = ", ".join(
                    c["name"] + ("(" + ", ".join(f"{k}={v}" for k, v in c["args"].items()) + ")" if c["args"] else "")
                    for c in result.tool_calls
                ) or ("none (blocked by guardrail)" if result.blocked else "none")
                tokens = result.usage.get("input_tokens", 0) + result.usage.get("output_tokens", 0)

            shown = [i["id"] for i in parse_product_list(reply)]
            out.append({
                "id": row["id"], "what_it_tests": row["what_it_tests"], "shopper_says": row["shopper_says"],
                "setup": row["setup"], "expected_tool": row["expected_tool"],
                "expected_filters": row["expected_filters"], "tools_called": called,
                "auto_tool_check": check, "auto_notes": detail, "products_shown": shown,
                "expected_reply": row["expected_reply"], "agent_reply": reply, "agent_tokens": tokens,
                "manual_check": "", "notes": "",
            })
            print(f"\n{'=' * 78}\n{row['id']} — {row['what_it_tests']} | shopper: {row['shopper_says']!r}"
                  f"{' | setup: ' + row['setup'] if row['setup'] else ''}")
            print(f"tools: {called}\nauto tool check: {check}{' — ' + detail if detail else ''}")
            print(f"--- expected reply ---\n{row['expected_reply']}\n--- agent reply ---\n{reply}")
            time.sleep(4)  # stay under the per-minute token limit
    finally:
        created = [i for i in order_ids() if i not in start_orders]
        with sqlite3.connect(DB_PATH) as conn:
            conn.executemany("DELETE FROM orders WHERE id = ?", [(i,) for i in created])
        clear_preferences()
        if saved_prefs["organic_only"]:
            db.set_preference("organic_only", "1")
        if saved_prefs["max_price"] is not None:
            db.set_preference("max_price", str(saved_prefs["max_price"]))

    RUNS_DIR.mkdir(exist_ok=True)
    stem = RUNS_DIR / f"run_{started:%Y%m%d_%H%M}"
    with stem.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        writer.writeheader()
        writer.writerows(out)
    write_markdown(stem.with_suffix(".md"), started, out)

    passed = sum(r["auto_tool_check"] == "PASS" for r in out)
    not_run = [r["id"] for r in out if r["auto_tool_check"] == "NOT RUN"]
    print(f"\nAutomatic tool checks: {passed}/{len(out) - len(not_run)} passed")
    if not_run:
        print(f"Not run (Groq usage limit): {', '.join(not_run)}. Re-run later with --only {','.join(not_run)}")
    print(f"Results: {stem.with_suffix('.csv').name} and {stem.with_suffix('.md').name} in {RUNS_DIR}")
    return 0


def write_markdown(path: Path, started: datetime, out: list[dict]) -> None:
    def cell(text) -> str:
        return str(text).replace("|", "\\|").replace("\n", "<br>")

    lines = [
        f"# Eval run {started:%Y-%m-%d %H:%M}",
        "",
        f"Agent `{LLM_MODEL}` · guardrail `{GUARDRAIL_MODEL}` · vision `{VISION_MODEL}`",
        "",
        "| ID | Tests | Shopper says | Tools called | Auto check | Expected reply | Agent reply | Manual check |",
        "|----|-------|--------------|--------------|------------|----------------|-------------|--------------|",
    ]
    for r in out:
        auto = r["auto_tool_check"] + (f"<br>{cell(r['auto_notes'])}" if r["auto_notes"] else "")
        lines.append(
            f"| {r['id']} | {cell(r['what_it_tests'])} | {cell(r['shopper_says'])} | {cell(r['tools_called'])} "
            f"| {auto} | {cell(r['expected_reply'])} | {cell(r['agent_reply'])} | |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
