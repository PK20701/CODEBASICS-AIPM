"""Data access for store.db: products, orders and preferences.

Ratings are deliberately absent -- they come only from
initial_setup/reviews_api.py (PRD FR-09).
"""

import sqlite3
from contextlib import closing

from config import DB_PATH


def _connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise RuntimeError(
            f"{DB_PATH.name} not found. Run: python initial_setup/setup_db.py"
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_preferences_table() -> None:
    """PRD FR-24: preferences live next to the store data.

    setup_db.py only resets products and reviews, so this table survives.
    """
    with closing(_connect()) as conn, conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )


# --- Products -------------------------------------------------------------

def search_products(keyword: str, max_price: float | None = None,
                    is_organic: bool | None = None) -> list[dict]:
    """PRD FR-01/02: every word of the keyword must appear in name, description or category.

    Products whose name or category match win; descriptions are only searched
    when the store has nothing by that name or category. Otherwise "honey" would
    also return Organic Granola ("...granola with honey..."). The choice is made
    before the price/organic filters, so "organic oats" finds no oats rather than
    falling back to granola.
    """
    with closing(_connect()) as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT id, name, category, price, description, is_organic FROM products ORDER BY id"
        )]

    everything = " ".join(f"{r['name']} {r['category']} {r['description']}" for r in rows).lower()
    # "oats" should find Rolled Oats, not Oat Milk; only fall back to the
    # singular ("honeys" -> "honey") when the word as typed matches nothing.
    terms = [t if t in everything or len(t) <= 3 or not t.endswith("s") else t[:-1]
             for t in keyword.lower().split()]

    def matching(fields: tuple[str, ...]) -> list[dict]:
        return [
            r for r in rows
            if all(t in " ".join(r[f] for f in fields).lower() for t in terms)
        ]

    found = matching(("name", "category")) or matching(("name", "category", "description"))
    return [
        r for r in found
        if (max_price is None or r["price"] <= max_price) and (not is_organic or r["is_organic"])
    ]


def get_product(product_id: int) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT id, name, category, price, description, is_organic FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()
    return dict(row) if row else None


# --- Orders ---------------------------------------------------------------

def create_order(product: dict) -> dict:
    with closing(_connect()) as conn, conn:
        cur = conn.execute(
            "INSERT INTO orders (product_id, product_name, price) VALUES (?, ?, ?)",
            (product["id"], product["name"], product["price"]),
        )
        row = conn.execute(
            "SELECT id, product_id, product_name, price, ordered_at FROM orders WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
    return dict(row)


def list_orders() -> list[dict]:
    with closing(_connect()) as conn:
        return [dict(r) for r in conn.execute(
            "SELECT id, product_id, product_name, price, ordered_at FROM orders ORDER BY id DESC"
        )]


# --- Preferences ----------------------------------------------------------

def get_preferences() -> dict:
    """Returns {"organic_only": bool, "max_price": float | None}."""
    ensure_preferences_table()
    with closing(_connect()) as conn:
        raw = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM preferences")}
    return {
        "organic_only": raw.get("organic_only") == "1",
        "max_price": float(raw["max_price"]) if "max_price" in raw else None,
    }


def set_preference(key: str, value: str | None) -> None:
    """A value of None removes the preference."""
    ensure_preferences_table()
    with closing(_connect()) as conn, conn:
        if value is None:
            conn.execute("DELETE FROM preferences WHERE key = ?", (key,))
        else:
            conn.execute(
                "INSERT INTO preferences (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
