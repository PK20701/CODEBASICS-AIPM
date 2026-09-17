"""
Reviews API — reads from the `reviews` table in store.db and returns
aggregated rating information for products.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "store.db")


def get_product_rating(product_id: int) -> dict:
    """Return average rating and review count for a single product."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT AVG(rating), COUNT(*) FROM reviews WHERE product_id = ?",
        (product_id,),
    )
    row = cursor.fetchone()
    conn.close()

    avg = round(row[0], 2) if row and row[0] is not None else 0.0
    count = row[1] if row else 0
    return {"product_id": product_id, "average_rating": avg, "review_count": count}


def get_ratings_for_products(product_ids: list[int]) -> list[dict]:
    """Return ratings for a list of product IDs."""
    if not product_ids:
        return []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    placeholders = ",".join("?" * len(product_ids))
    cursor.execute(
        f"""
        SELECT product_id, AVG(rating), COUNT(*)
        FROM reviews
        WHERE product_id IN ({placeholders})
        GROUP BY product_id
        """,
        product_ids,
    )
    rows = cursor.fetchall()
    conn.close()

    ratings_map = {r[0]: {"average_rating": round(r[1], 2), "review_count": r[2]} for r in rows}
    return [
        {
            "product_id": pid,
            "average_rating": ratings_map.get(pid, {}).get("average_rating", 0.0),
            "review_count":   ratings_map.get(pid, {}).get("review_count", 0),
        }
        for pid in product_ids
    ]


if __name__ == "__main__":
    # Single product
    result = get_product_rating(1)
    print("Single product rating:")
    print(f"  Product {result['product_id']}: {result['average_rating']} stars ({result['review_count']} reviews)")

    # Multiple products
    print("\nBatch ratings:")
    results = get_ratings_for_products([1, 3, 5, 7])
    for r in results:
        print(f"  Product {r['product_id']}: {r['average_rating']} stars ({r['review_count']} reviews)")
