# Product Brief — AI Shopping Agent

## The product

**ShopMate** is a conversational shopping assistant for a small online pantry store. The store stocks 32 products across honey, oils, nuts and seeds, grains, tea and coffee, snacks, and dairy alternatives. Roughly half of them are organic. Prices range from about $3.50 to $30.

Instead of clicking through category pages and filter menus, a shopper tells the assistant what they want in plain language, or shows it a photo, and the assistant finds the right products, shows how other customers rated them, and places the order once the shopper says yes.

## Who it is for

A busy shopper who already knows roughly what they want. They do not want to browse. They want to say *"organic honey under $20 with at least a 4.5 rating"* and be done in two messages.

## The job to be done

> "When I know what kind of product I want and what my constraints are, help me find the best match in this store and order it, without making me repeat myself."

## What the assistant must do

| Capability | What the shopper experiences |
|------------|------------------------------|
| **Text search** | "I want organic honey under $20" returns matching products from the store. |
| **Photo search** | Shopper uploads a photo of a product (say, a jar of honey). The assistant works out what it is and searches for it in the store. |
| **Ratings** | Every product shown comes with its average customer rating and review count, pulled from the reviews API. |
| **Filtering** | Price cap, organic only, and minimum rating are all respected when the shopper states them. |
| **Ordering** | The shopper picks a product from the list ("the second one", "order #3", "yes") and the assistant places the order. |
| **Order history** | "What have I ordered before?" is answered from the orders table. |
| **Preferences** | If the shopper says "I always want organic" or "never show me anything over $20", the assistant remembers that in future sessions without being told again. |

## Tools the agent needs

At minimum:

| Tool | What it does | Backed by |
|------|--------------|-----------|
| `search_products` | Keyword search across name, description, and category, with optional `max_price` and `is_organic` filters. | `products` table |
| `get_rating` | Average rating and review count for a product. | `reviews_api.py` |
| `checkout` | Places an order for one product and returns a confirmation with the order ID. | `orders` table |
| `describe_product_image` | Takes an image, returns what the product is, a search keyword, and whether it looks organic. | A vision-capable model |
| `get_order_history` | Returns what the shopper has ordered before. | `orders` table |

You may add tools. You should be able to explain why each one exists.

## The three flows

- **Browsing.** Shopper describes what they want. Agent searches, fetches ratings for each candidate, applies any minimum-rating filter, and presents the list. It does not order.
- **Photo search.** Shopper provides an image. Agent identifies the product, then continues with the browsing flow.
- **Ordering.** Shopper confirms a choice. Agent takes the product ID from the list it showed earlier and calls checkout. It never guesses an ID.

## The output contract

Every product list uses exactly this line format, plain text, one blank line between entries:

```
#1. Organic Raw Honey (ID:1) — $14.99 ★4.62 — organic

#2. Organic Buckwheat Honey (ID:5) — $18.99 ★4.62 — organic
```

The `(ID:X)` is mandatory. It is how the agent knows what to order later, and it is what the evals will check.

If exactly one product qualifies, still show it as a list and ask: *"Would you like to order it? Just say yes or give me the number."*

## Memory and personalization

- The agent answers "what have I ordered before?" from the orders table.
- Preferences such as "always organic" or "nothing over $20" persist across sessions. You decide where they are stored (a small table, a JSON file, anything durable) and how they are applied. Document the decision.

## What the assistant must never do

- Place an order without an explicit confirmation from the shopper.
- Invent a product, a price, or a rating that is not in the store data.
- Answer requests that have nothing to do with shopping in this store.

## Explicit non-goals for this assignment

- No shopping cart with multiple items or quantities. One product per order.
- No payments, returns, cancellations, or delivery tracking.
- No login or multi-user support. Assume a single shopper.
- No document retrieval (RAG). The store data is structured, and that is enough.

## What "good" looks like

1. Given a query with constraints, the right products come back and the wrong ones do not.
2. The product list is always in the same format, so it is scannable and testable.
3. The assistant never orders on its own, and never orders the wrong product.
4. Off-topic requests are politely redirected.
5. Preferences stated once are honoured next time.
