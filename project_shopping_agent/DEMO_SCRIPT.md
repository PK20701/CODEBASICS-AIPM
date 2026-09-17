# ShopMate — 2-Minute Demo Script (Loom)

**Speaker:** Prasanna Kamthekar, Product Manager
**Length:** about 2 minutes, about 280 spoken words. Screen plus voice, no editing.

## Before you record

1. Start the app: `.venv\Scripts\streamlit.exe run app.py`, then open http://localhost:8501.
2. Clear old test data so the history looks clean. Close the app first, delete `store.db`, run `.venv\Scripts\python.exe initial_setup/setup_db.py`, then start the app again.
3. Have `resources/honey.png` ready to attach.
4. Replies take 10–25 seconds. Keep talking while ShopMate is "Looking...", or pause the recording.

---

## 0:00–0:15 — The problem

> "This is ShopMate, a shopping assistant for a small online pantry store containing multiple products. Our shoppers are busy and already knows what they want. They don't want to click through category pages and filters for placing the order of item which they already have in mind. They want to say it once and be done in two messages. Shoppers also want system should know their preference and easy to filter out item via simple instruction to make overall experience enriched"
> "Today I will demo how shoppers can interact with ShopMate, a shopping assistant & how it responds, Lets get started " 

## 0:15–0:40 — Search with constraints

**Type:** `organic honey with 4.5+ rating under $20`

> "Here's a real request with three constraints: organic, rated 4.5 or higher, and under twenty dollars. ShopMate searches the catalogue, pulls each product's rating from the reviews service, and returns exactly three honeys. Manuka isn't listed. It's organic and highly rated, but it costs thirty dollars. Every line has the same format: name, product ID, price, and rating, with review counts underneath. The format stays the same every time, so it's easy to scan and easy to test."

## 0:40–1:00 — Order in one word

**Type:** `cheapest oat milk`, then `yes`

> "Now a quick one: cheapest oat milk. There's one match, Oat Milk at four forty-nine, and ShopMate asks before doing anything. I say yes, and the order is placed with an order ID. A key product decision: ShopMate never orders unless the shopper clearly says yes to a product from the list. That rule is enforced in code, not just in the prompt."

## 1:00–1:20 — Photo search

**Attach** `honey.png`, **type** `find this`

> "Sometimes the shopper doesn't know the product name, just what it looks like. I upload a photo of a honey jar. ShopMate recognises it and shows the honeys we stock, in the same format."

## 1:20–1:35 — Order history

**Type:** `what have I ordered before?`

> "What have I ordered before? The answer comes straight from the orders table, so it shows the oat milk order I just placed, with its order ID, price, and date."

## 1:35–1:55 — Preferences that persist

**Type:** `I always want organic`, **refresh the browser**, then **type** `honey`

> "Last, personalisation. I tell ShopMate I always want organic, and it confirms the preference is saved. I refresh to start a new session, then ask for honey without mentioning organic. Only organic honeys come back. The shopper never has to repeat themselves."

## 1:55–2:00 — Close

> "So that's ShopMate: say what you want, see the best matches with real ratings, and order with one word, safely. Next up are guardrails for off-topic requests, and an evaluation set to measure quality. Thanks."

---

## After recording

- Paste the Loom link into `README.md` under **Demo**.
- To remove the organic preference, say `I no longer want organic only`.
