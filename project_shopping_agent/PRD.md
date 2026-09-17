# Product Requirements Document — ShopMate

**Date:** 2026-09-14
**Author:** Prasanna Kamthekar

> The "Source" column points to the section of `PRODUCT_BRIEF.md` each requirement comes from. Items marked **Decision** are choices the brief leaves to us.

---

## 1. Overview

ShopMate is a chat assistant for a small online pantry store with 32 products. A shopper types what they want, or uploads a photo of it, and ShopMate returns the matching products from the store with their customer ratings. When the shopper confirms a choice, ShopMate places a one-item order. It remembers past orders and standing preferences such as "always organic", so the shopper never has to repeat themselves.

---

## 2. Problem

- Shoppers who already know what they want still have to click through category pages and filter menus to find it.
- Checking constraints (price, organic, rating) means comparing product pages and a separate reviews source by hand.
- Standing preferences have to be re-applied on every visit.

---

## 3. Goals

| Goal | How we know |
|------|-------------|
| Constrained queries return the right products and only those | "organic honey with 4.5+ rating under $20" returns IDs 1, 5, 7 and nothing else |
| Every product list is scannable and testable | Every product line matches the output format in 6.3, including `(ID:X)` |
| No order is ever placed without a clear yes, and never for the wrong product | Zero `checkout` calls in evals without a confirmation; the ordered ID is always from the last list shown |
| Off-topic requests never reach the agent | "write me a poem", "what's the weather" and `elephant.png` get a redirect with no tool calls |
| A preference stated once is honoured in later sessions | After "I always want organic" and an app restart, a honey search shows only organic honeys |
| A shopper can go from request to order in two messages | Request → list; "yes" or a number → order confirmation with order ID |

---

## 4. Non-Goals

- No shopping cart, multiple items per order, or quantities. One product per order.
- No payments, returns, cancellations, or delivery tracking.
- No login or multi-user support. A single shopper is assumed.
- No document retrieval (RAG). The structured store data is used directly.
- No product recommendations beyond what matches the shopper's request.
- No changes to `initial_setup/`.

---

## 5. Users

A busy shopper who already knows roughly what they want and has constraints in mind. They want to state the request in one message and order in the next, without browsing.

---

## 6. Functional Requirements

### 6.1 Search

| ID | Requirement | Source |
|----|-------------|--------|
| FR-01 | The shopper can describe a product in plain language and the agent searches the store's `products` table by keyword across name, description, and category. | Capabilities: Text search; Tools |
| FR-02 | A multi-word keyword matches a product when every word appears somewhere in its name, description, or category (e.g. "raw honey" matches "Organic Raw Honey"). Name and category matches take priority; descriptions are searched only when no name or category matches, so "honey" does not return Organic Granola ("…granola with honey…"). | Capabilities: Text search |
| FR-03 | When the shopper states a price cap, no product above that price is shown (`max_price` filter). | Capabilities: Filtering |
| FR-04 | When the shopper asks for organic, only products with `is_organic = 1` are shown (`is_organic` filter). | Capabilities: Filtering |
| FR-05 | When the shopper states a minimum rating, the agent fetches the rating of each search result with `get_rating` and shows only products whose average rating meets it. | Capabilities: Filtering; Flows: Browsing |
| FR-06 | Searching never places an order. | Flows: Browsing |
| FR-07 | If no product matches, the agent says so plainly and does not invent a product. | Must never: invent a product |

### 6.2 Ratings

| ID | Requirement | Source |
|----|-------------|--------|
| FR-08 | Every product shown includes its average rating and review count. | Capabilities: Ratings |
| FR-09 | Ratings come only from `initial_setup/reviews_api.py`. The agent never reads the `reviews` table directly. | Tools; SETUP §4 |
| FR-10 | The agent never states a price or rating that is not in the store data or the reviews API. | Must never: invent a price or rating |

### 6.3 Output format

| ID | Requirement | Source |
|----|-------------|--------|
| FR-11 | Every product list uses exactly this plain-text line format, with one blank line between entries: `#N. <name> (ID:<id>) — $<price> ★<rating> — organic`. The `— organic` suffix appears only for organic products. | Output contract |
| FR-12 | `(ID:X)` is present on every product line. | Output contract |
| FR-13 | Each product's review count is shown below the list in one line, e.g. "Review counts: #1 — 4 reviews, #2 — 4 reviews", so the list lines keep the exact format in FR-11. **Decision:** the brief asks for review counts but its line format has no slot for them. | Capabilities: Ratings; Output contract |
| FR-14 | If exactly one product qualifies, it is still shown as a list, followed by: "Would you like to order it? Just say yes or give me the number." | Output contract |

Example:

```
#1. Organic Raw Honey (ID:1) — $14.99 ★4.62 — organic

#2. Organic Buckwheat Honey (ID:5) — $18.99 ★4.62 — organic
```

### 6.4 Ordering

| ID | Requirement | Source |
|----|-------------|--------|
| FR-15 | The shopper can pick from the last list shown by position ("the second one", "order #3") or, for a single-item list, by saying "yes". | Capabilities: Ordering |
| FR-16 | Clear confirmations: "yes", "yes please", "order it", "order #2", "the second one", "I'll take #1". Not confirmations: "maybe", "not sure", "what about cheaper ones?", "no", or a "yes" when the last list had more than one product and no number was given (the agent asks which one). | Capabilities: Ordering; Must never: order without confirmation |
| FR-17 | The product ID passed to `checkout` is taken from the last list shown in the conversation. The agent never guesses an ID. | Flows: Ordering |
| FR-18 | `checkout` places an order for one product and returns a confirmation with the order ID, product name, and price. The agent may only tell the shopper an order was placed when `checkout` succeeded in that turn; code checks this. The confirmation text (order ID, product, price) is written by code from the `checkout` result. After an order, the list is used up: a further "yes" places no new order. | Tools; Must never: invent |

### 6.5 Photo search

| ID | Requirement | Source |
|----|-------------|--------|
| FR-19 | The shopper can upload a product photo in the chat. | Capabilities: Photo search |
| FR-20 | `describe_product_image` returns what the product is, a search keyword, and whether it looks organic. | Tools |
| FR-21 | After identifying the product, the agent continues with the browsing flow (search, ratings, list). | Flows: Photo search |

### 6.6 Memory and preferences

| ID | Requirement | Source |
|----|-------------|--------|
| FR-22 | "What have I ordered before?" is answered from the `orders` table with order ID, product name, price, and order date. Code recognises order-history questions and always calls `get_order_history`; the answer is written from its result, never from chat memory. | Memory and personalization |
| FR-23 | The shopper can state two kinds of standing preference: organic only ("I always want organic") and a price cap ("never show me anything over $20"). Code recognises these statements and always calls `save_preference`; the "Preference saved" reply is written from what was actually stored. | Capabilities: Preferences |
| FR-24 | Preferences are stored in a `preferences` table in `store.db` and persist across app restarts. **Decision:** `setup_db.py` resets only `products` and `reviews`, so this table survives re-runs and sits next to the rest of the store data. | Memory and personalization |
| FR-25 | Saved preferences are applied in code on every search: organic-only forces `is_organic = 1`; a saved price cap sets `max_price`, and if the shopper states a different cap in the message, the lower of the two is used. | Memory and personalization |

---

## 7. Tools

| Tool | What it does | Backed by |
|------|--------------|-----------|
| `search_products` | Keyword search across name, description, and category, with optional `max_price` and `is_organic` filters. Saved preferences are applied here. | `products` table |
| `get_rating` | Average rating and review count for one product. | `reviews_api.py` |
| `checkout` | Places an order for one product and returns the order ID, product name, and price. | `orders` table |
| `describe_product_image` | Takes the uploaded image and returns the product, a search keyword, and whether it looks organic. | Vision-capable model on Groq |
| `get_order_history` | Returns the shopper's past orders. | `orders` table |
| `save_preference` | Stores "organic only" or a price cap. Exists because the brief requires preferences that persist across sessions. | `preferences` table |
| `get_preferences` | Returns the saved preferences so the agent can mention them when relevant. | `preferences` table |

---

## 8. Guardrails

| ID | Guardrail | Enforced by |
|----|-----------|-------------|
| GR-01 | **Off-topic.** Before the agent runs, each message (and any uploaded image) is checked for whether it is about shopping in this store. Off-topic input ("write me a poem", "what's the weather", a photo of an elephant) gets a polite redirect and never reaches the agent. | Code: a separate classifier call before the agent |
| GR-02 | **No order without a yes.** `checkout` runs only when the shopper's latest message is a clear confirmation (FR-16) and the product ID is in the last list shown (FR-17). | Prompt (instruction to the agent) **and** code (`intent.py` decides which product, if any, was confirmed; `checkout` refuses any other call) |

---

## 9. Demonstration Scenarios

### Scenario 1 — Search with filters

User: `organic honey with 4.5+ rating under $20`

Expected:

```text
→ search_products(keyword="honey", is_organic=true, max_price=20)
→ get_rating for each result; keep ratings ≥ 4.5
→ List of Organic Raw Honey (ID:1), Organic Buckwheat Honey (ID:5), Organic Acacia Honey (ID:7). No Manuka.
```

### Scenario 2 — Cheapest match

User: `cheapest oat milk`

Expected:

```text
→ search_products(keyword="oat milk"), then get_rating
→ #1. Oat Milk (ID:30) — $4.49 ★4.33, with the single-item order prompt
```

### Scenario 3 — Photo search

User: uploads `resources/honey.png`, says `find this`

Expected:

```text
→ describe_product_image → keyword "honey"
→ search_products(keyword="honey")
→ A list of honeys in the standard format
```

### Scenario 4 — Ordering

User: `yes` (after a single-item list showing Oat Milk, ID:30)

Expected:

```text
→ checkout(product_id=30)
→ Order confirmation with order ID, product name, and price
```

### Scenario 5 — Ambiguous confirmation

User: `maybe` (after a list)

Expected:

```text
→ No checkout call
→ Agent asks the shopper to confirm clearly
```

### Scenario 6 — Order history

User: `what have I ordered before?`

Expected:

```text
→ get_order_history
→ The earlier order with product name and price
```

### Scenario 7 — Saved preference

User: `I always want organic`, then restarts the app and says `show me honey`

Expected:

```text
→ save_preference(organic_only=true)
→ After restart: search_products applies is_organic=true
→ Only organic honeys (IDs 1, 3, 5, 7)
```

### Scenario 8 — Off-topic

User: `write me a poem about honey` (or uploads `resources/elephant.png`)

Expected:

```text
→ Guardrail blocks the message; no tool is called
→ Polite redirect back to shopping in the store
```

---

## 10. Acceptance Criteria

- [ ] "organic honey with 4.5+ rating under $20" shows exactly Organic Raw, Organic Buckwheat, and Organic Acacia Honey.
- [ ] "cheapest oat milk" shows Oat Milk at $4.49.
- [ ] Uploading `honey.png` with "find this" shows a list of honeys.
- [ ] "yes" after a single-item list places an order and shows an order ID.
- [ ] "maybe" after a list places no order.
- [ ] "what have I ordered before?" shows the order just placed.
- [ ] "I always want organic", then restart and search for honey, shows only organic honeys.
- [ ] Every product line contains `(ID:X)` and follows the format in 6.3.
- [ ] "write me a poem", "what's the weather", and `elephant.png` get a redirect with no tool calls.
- [ ] A product the store does not sell returns a plain "not found" with no invented product.

---

## 11. Technology and Build Instructions

| Component | Choice |
|-----------|--------|
| Language | Python 3.10+ |
| LLM provider and model | Groq, `qwen/qwen3.8-27b` (agent and tool calling) |
| Vision model | Groq, `qwen/qwen3.8-27b` (`describe_product_image`) |
| Off-topic guardrail model | Groq, `qwen/qwen3.8-27b` (classifier call before the agent) |
| UI | Streamlit chat with image upload |
| Preferences stored in | `preferences` table in `store.db` |

Rules for Claude Code:

1. Read `SETUP.md` first. Build on top of `initial_setup/`; do not modify it.
2. Ratings come only from `initial_setup/reviews_api.py`.
3. Keep API keys in `.env`.
4. Do not add anything outside this PRD.
