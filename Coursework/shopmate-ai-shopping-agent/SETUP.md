# Setup — AI Shopping Agent

> **This file is technical.** You do not need to understand every line. You can hand it to Claude Code as-is: open Claude Code in this folder and tell it to read `SETUP.md` and get the environment ready. Then confirm the two sanity checks at the bottom pass.

---

## 1. Prerequisites

- Python 3.10 or newer.
- An API key for an LLM provider of your choice. Photo search needs a model that accepts images, so pick a provider that offers one.
- Claude Code, installed and signed in.

## 2. Environment

Create a project-local virtual environment inside this folder and install everything into it. Never install into the global or shared interpreter.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

The starter kit itself has no third-party dependencies. Add packages for your agent (LLM SDK, agent framework, UI) as you build, and record them in a `requirements.txt` or `pyproject.toml` in this folder.

API keys go in a `.env` file in this folder. Never put keys in code, and never commit `.env`.

## 3. Create the store database

```bash
python initial_setup/setup_db.py
```

This creates `store.db` in this folder (one level up from the script). It contains three tables:

| Table | Purpose | Columns |
|-------|---------|---------|
| `products` | The catalogue. 32 rows across honey, oils, nuts, seeds, grains, tea, coffee, snacks, dairy alternatives. | `id`, `name`, `category`, `price`, `description`, `is_organic` (0 or 1) |
| `reviews` | Customer reviews. About 100 rows. | `id`, `product_id`, `rating`, `reviewer_name`, `review_text` |
| `orders` | Empty until the agent places orders. | `id`, `product_id`, `product_name`, `price`, `ordered_at` |

Running the script again is safe. It resets `products` and `reviews` and leaves `orders` alone.

## 4. The reviews API

`initial_setup/reviews_api.py` is a stand-in for a third-party ratings service. It reads `store.db` and exposes two functions:

| Function | Returns |
|----------|---------|
| `get_product_rating(product_id)` | `{"product_id", "average_rating", "review_count"}` for one product |
| `get_ratings_for_products(product_ids)` | The same, as a list, for many products in one call |

**Rule for the agent:** ratings come only through these functions. The agent must not query the `reviews` table directly. Treat the API as if it belonged to another company.

Both scripts in `initial_setup/` are infrastructure. Build on top of them; do not modify them. Import the API from your agent code with:

```python
from initial_setup.reviews_api import get_product_rating, get_ratings_for_products
```

Run your agent from this folder so the import resolves.

## 5. Test images

`resources/` contains three images:

| File | Use |
|------|-----|
| `honey.png` | A product the store sells. Photo search should find honeys. |
| `oats.png` | A product the store sells. Photo search should find oats. |
| `elephant.png` | Not a product. Use it to test the off-topic guardrail. |

## 6. Sanity checks

Both must pass before you build anything.

```bash
python initial_setup/setup_db.py
```

Expected: `Database created at: .../project_shopping_agent/store.db`

```bash
python initial_setup/reviews_api.py
```

Expected: a short list of product ratings, starting with `Product 1: 4.62 stars (4 reviews)`.

## 7. Folder layout after setup

```
project_shopping_agent/
├── assignment.md
├── PRODUCT_BRIEF.md
├── PRD_TEMPLATE.md
├── SETUP.md
├── eval_set.csv          <- starter eval cases; you extend this
├── .env                  <- your API keys (never committed)
├── .venv/                <- your virtual environment
├── store.db              <- created by setup_db.py
├── initial_setup/
│   ├── setup_db.py
│   └── reviews_api.py
├── resources/
│   ├── honey.png
│   ├── oats.png
│   └── elephant.png
└── your agent code, PRD.md, GUARDRAILS.md, EVALS.md go here
```
