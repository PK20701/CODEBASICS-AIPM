# ShopMate — AI Shopping Agent

ShopMate is a chat assistant for a small online pantry store. You tell it what you want, or show it a photo. It finds matching products, shows their customer ratings, and places a one-item order when you say yes.

| Document | What it covers |
|----------|----------------|
| [PRD.md](PRD.md) | The spec this build follows |
| [GUARDRAILS.md](GUARDRAILS.md) | The off-topic check and the "no order without a yes" rule |
| [EVALS.md](EVALS.md) | Test set, results, and what the evals taught us |

## Demo

**[Watch the 2-minute demo](https://drive.google.com/file/d/1CFlVn2TscPi_uJRLclXPngnis56c5bBa/view?usp=drive_link)**

## Setup (Windows)

Run everything from this folder.

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe initial_setup/setup_db.py
```

Copy `.env.example` to `.env` and add a Groq API key from https://console.groq.com/keys:

```
GROQ_API_KEY=gsk_...
GROQ_MODEL=qwen/qwen3.8-27b
GROQ_REASONING_EFFORT=none
GROQ_VISION_MODEL=qwen/qwen3.8-27b
GROQ_VISION_REASONING_EFFORT=none
```

Groq's free tier allows 200,000 tokens a day per model. If Qwen's allowance runs out, set `GROQ_MODEL=openai/gpt-oss-20b` and `GROQ_REASONING_EFFORT=low` for chat. Photos still use Qwen. Restart the app after editing `.env`.

## Run

```bash
.venv\Scripts\streamlit.exe run app.py
```

The app opens at http://localhost:8501. Type a request, or use the attachment icon in the chat box to add a photo.

## Try it

| Say | You get |
|-----|---------|
| `organic honey with 4.5+ rating under $20` | Organic Raw, Organic Buckwheat and Organic Acacia Honey |
| `cheapest oat milk` | Oat Milk at $4.49, and an offer to order it |
| `yes` (after a one-item list) | An order confirmation with the order ID |
| `honey.png` + `find this` | A list of honeys |
| `what have I ordered before?` | Your past orders |
| `I always want organic`, restart, `honey` | Organic honeys only |
| `write me a poem` or `elephant.png` | A polite note that ShopMate only helps with shopping |

## How it's built

| File | Role |
|------|------|
| `app.py` | Streamlit chat with photo upload |
| `agent.py` | The agent loop, system prompt, and the product list format |
| `tools.py` | The seven tools listed in PRD §7 |
| `guardrails.py` | Off-topic check, run before the agent on every message and photo |
| `intent.py` | Plain rules that read a message: which product was confirmed, order-history questions, saved preferences |
| `db.py` | Products, orders and preferences in `store.db` |
| `config.py` | Model names, limits, and shared helpers. Keys are read from `.env` only. |
| `run_evals.py`, `eval_set.csv`, `eval_runs/` | Evals (see [EVALS.md](EVALS.md)) |
| `tests/` | Offline and live tests |
| `initial_setup/` | The provided store database and reviews API, unchanged |

Key decisions:

- **Model.** Groq `qwen/qwen3.8-27b` handles chat, photos and the off-topic check. Pricing: https://groq.com/pricing
- **Preferences.** Saved in a `preferences` table in `store.db`. `setup_db.py` only resets products and reviews, so preferences survive. They're applied in code inside `search_products`, not left to the model.
- **Ratings.** Come only from `initial_setup/reviews_api.py`, with all search results fetched in one call.
- **Critical replies come from code.** Order confirmations, order history and "Preference saved" messages are built from real tool results. In testing, the model sometimes claimed an order or a saved preference that didn't exist.
- **Logging.** Each turn is written to `logs/turns.jsonl` (message, tool calls, reply) so problems can be traced.

## Tests

| Script | Checks | Calls Groq? |
|--------|--------|-------------|
| `tests/test_intent.py` | Order confirmation, order history and preference rules | No |
| `tests/test_search.py` | Product search and filters | No |
| `tests/test_assignment_checks.py` | The six build checks plus ordering and preference edge cases | Yes |
| `tests/test_guardrails.py` | Both guardrails | Yes |
| `run_evals.py` | The eval set (see [EVALS.md](EVALS.md)) | Yes |

Run any of them with `.venv\Scripts\python.exe <script>`. For example:

```bash
.venv\Scripts\python.exe run_evals.py --model openai/gpt-oss-20b
```

Live scripts use a gpt-oss model for chat by default, so testing doesn't use up Qwen's daily allowance. They remove the orders and preferences they create. Don't use the app while one is running, because both write to `store.db`.

## Reset

- **Remove all orders:** delete `store.db` and run `setup_db.py` again.
- **Remove the organic preference:** say `I no longer want organic only`.
