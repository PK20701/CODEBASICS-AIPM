# ShopMate — AI Shopping Agent

A chat assistant for a small pantry store. Describe what you want, or attach a photo of it. ShopMate finds matching products with their customer ratings and places a one-item order when you confirm.

- Spec: [PRD.md](PRD.md)
- Guardrails: GUARDRAILS.md *(Step 4)*
- Evals: EVALS.md *(Step 5)*

## Demo

Loom (2 min): **<paste Loom link here>**

## Setup (Windows)

Run everything from this folder.

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe initial_setup/setup_db.py
```

Copy `.env.example` to `.env` and add your Groq API key (https://console.groq.com/keys):

```
GROQ_API_KEY=gsk_...
GROQ_MODEL=qwen/qwen3.8-27b
GROQ_REASONING_EFFORT=none
GROQ_VISION_MODEL=qwen/qwen3.8-27b
GROQ_VISION_REASONING_EFFORT=none
```

Groq's free tier allows 200,000 tokens a day per model. To test without using Qwen's quota, set `GROQ_MODEL=openai/gpt-oss-120b` and `GROQ_REASONING_EFFORT=low`. Photos still use Qwen. Restart the app after changing `.env`.

## Run

```bash
.venv\Scripts\streamlit.exe run app.py
```

Opens at http://localhost:8501. Type a request, or click the attachment icon in the chat box to add a product photo.

## Try it

| Say | You get |
|-----|---------|
| `organic honey with 4.5+ rating under $20` | Organic Raw, Organic Buckwheat, Organic Acacia Honey |
| `cheapest oat milk` | Oat Milk, $4.49, and an offer to order it |
| `yes` (after a one-item list) | Order confirmation with an order ID |
| Attach `resources/honey.png`, `find this` | A list of honeys |
| `what have I ordered before?` | Your past orders |
| `I always want organic`, restart, `show me honey` | Organic honeys only |

## How it is built

| File | Role |
|------|------|
| `app.py` | Streamlit chat with photo upload. Each reply has a collapsible "Tool calls" panel. |
| `agent.py` | Tool-calling loop, system prompt, and the output contract (list format, real prices and ratings, review counts). |
| `tools.py` | The 7 tools from PRD §7. `checkout` refuses any order the shopper did not confirm. |
| `intent.py` | Rules (no model) that read the shopper's message: which product they confirmed, order-history questions, standing preferences. |
| `tests/` | `test_intent.py` (offline rules) and `test_assignment_checks.py` (live end-to-end checks). |
| `logs/turns.jsonl` | Every turn's message, tool calls and reply, for tracing a reported problem. |
| `db.py` | Reads and writes `store.db`: products, orders, preferences. |
| `config.py` | Model names and limits. Secrets come only from `.env`. |
| `initial_setup/` | Provided store database and reviews API. Not modified. |

Decisions:

- **Model.** Groq `qwen/qwen3.8-27b` for the agent, photo recognition and (Step 4) the off-topic check. Pricing: https://groq.com/pricing
- **Preferences.** Stored in a `preferences` table in `store.db`. `setup_db.py` only resets `products` and `reviews`, so saved preferences survive. They are applied in code inside `search_products`, not left to the model.
- **Ratings.** Come only from `initial_setup/reviews_api.py`.
- **Critical replies are written by code.** Order confirmations (with order ID), order history and "Preference saved" are built from tool results, not worded by the model. Testing showed the model would otherwise invent orders or claim a preference was saved when it wasn't.

## Test

```bash
.venv\Scripts\python.exe tests\test_intent.py
```

```bash
.venv\Scripts\python.exe tests\test_assignment_checks.py 3
```

The second command calls Groq, runs the assignment's six checks plus edge cases three times, then removes the orders and preferences it created.

## Reset

- Clear orders: delete `store.db` and re-run `setup_db.py`.
- Clear preferences: say "I no longer want organic only", or delete `store.db` as above.
