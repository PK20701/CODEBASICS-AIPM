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

def _term_matches(term: str, text: str) -> bool:
    # "honeys" should still find "honey"; nothing fancier than that.
    return term in text or (len(term) > 3 and term.endswith("s") and term[:-1] in text)


def search_products(keyword: str, max_price: float | None = None,
                    is_organic: bool | None = None) -> list[dict]:
    """PRD FR-01/02: every word of the keyword must appear in name, description or category.

    Products whose name or category match win; descriptions are only searched
    when nothing matches by name or category. Otherwise "honey" would also
    return Organic Granola ("...granola with honey...").
    """
    sql = "SELECT id, name, category, price, description, is_organic FROM products WHERE 1=1"
    params: list = []
    if max_price is not None:
        sql += " AND price <= ?"
        params.append(max_price)
    if is_organic:
        sql += " AND is_organic = 1"
    sql += " ORDER BY id"

    with closing(_connect()) as conn:
        rows = [dict(r) for r in conn.execute(sql, params)]

    terms = keyword.lower().split()

    def matching(fields: tuple[str, ...]) -> list[dict]:
        return [
            r for r in rows
            if all(_term_matches(t, " ".join(r[f] for f in fields).lower()) for t in terms)
        ]

    return matching(("name", "category")) or matching(("name", "category", "description"))


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
