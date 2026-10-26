# Evals — ShopMate

## What's here

| File | What it is |
|------|------------|
| [eval_set.csv](eval_set.csv) | 15 test cases: the 5 starter cases plus 10 new ones |
| [run_evals.py](run_evals.py) | The runner |
| [eval_runs/run_20260917_1134.csv](eval_runs/run_20260917_1134.csv) | Results of the judged run, with a manual check on every row |
| `eval_runs/run_20260917_1134.xlsx` | Same results, with app screenshots for the two photo cases |
| [eval_runs/run_20260917_1134.md](eval_runs/run_20260917_1134.md) | Same results as a Markdown table |

For each row, the runner:
1. sets up the situation: a product list shown earlier, a saved preference, an existing order, or a photo
2. sends the shopper's message
3. checks automatically that the right tool was called with the right filters, that no unexpected order was placed, and that the reply isn't empty
4. prints the agent's reply next to the expected reply, so each one can be checked by hand

Any orders the run creates are deleted afterwards, and saved preferences are put back.

```bash
.venv\Scripts\python.exe run_evals.py --model openai/gpt-oss-20b
```

**Models.** The app uses `qwen/qwen3.8-27b`. Groq's free tier allows 200,000 tokens a day per model, and a day of building and testing used up Qwen's allowance, so the eval runs used `openai/gpt-oss-20b` for chat and the off-topic check, and Qwen only for photos. `--app-model` runs the evals on the models in `.env`.

Each row is its own conversation. It starts fresh, and only its **Setup** column says what came before. For example, in E12 "the second one" refers to the three honeys in E12's setup, not to the single Oat Milk in E11. After a one-item list, "the second one" orders nothing (covered in `tests/test_intent.py`).

---

## Test set

| ID | Tests | Shopper says | Setup | Expected tool | Expected filters | Expected reply |
|----|-------|--------------|-------|---------------|------------------|----------------|
| E01 | Search with filters | organic honey under $20 | – | search_products | organic = yes, max price = 20 | Only organic honeys ≤ $20: Raw, Buckwheat, Acacia. No Manuka. Each line has (ID:X). |
| E02 | Rating filter | olive oil with a rating above 4.5 | – | search_products, then get_rating for each result | search = olive oil | Only Organic Extra Virgin Olive Oil. Nothing ordered. |
| E03 | Ordering | yes | Previous list: #1 Oat Milk (ID:30) | checkout | product id = 30 | One Oat Milk order, with an order ID. |
| E04 | Order history | what have I ordered before? | At least one order exists | get_order_history | – | Lists the earlier order with name and price. |
| E05 | Off-topic | write me a poem about honey | – | none (guardrail) | – | Polite redirect, no tool called. |
| E06 | Photo search | find this | Image: honey.png | describe_product_image, then search_products | search = honey | A list of honeys with (ID:X). Nothing ordered. |
| E07 | Off-topic photo | find this | Image: elephant.png | none (guardrail) | – | Polite redirect, no tool called. |
| E08 | Saved preference applied | show me honey | Saved preference: organic only | search_products | search = honey, organic = yes | Only the four organic honeys. |
| E09 | Unclear confirmation | maybe | Previous list: #1 Oat Milk (ID:30) | none (no checkout) | – | No order. Asks for a clear yes or the item number. |
| E10 | Product not stocked | do you sell almond butter? | – | search_products | search = almond butter | Says the store doesn't have it. No made-up product. |
| E11 | Cheapest item | cheapest oat milk | – | search_products | search = oat milk | Oat Milk at $4.49 as a one-item list, plus the order prompt. |
| E12 | Ordering by position | the second one | Previous list: Raw (1), Buckwheat (5), Acacia (7) | checkout | product id = 5 | One Organic Buckwheat Honey order, with an order ID. |
| E13 | "Yes" with several choices | yes | Previous list: Raw (1), Buckwheat (5), Acacia (7) | none (no checkout) | – | No order. Asks which number. |
| E14 | Saving a preference | never show me anything over $20 | – | save_preference | max price = 20 | Confirms the preference is saved. |
| E15 | Photo search (oats) | find this | Image: oats.png | describe_product_image, then search_products | search = oat | Rolled Oats and Steel-Cut Oats. Nothing ordered. |

---

## Results (run `run_20260917_1134`)

| ID | Tools called | Auto check | Agent reply (short) | Manual check | Notes |
|----|--------------|------------|---------------------|--------------|-------|
| E01 | search_products(organic, honey, ≤ $20), get_rating([1, 5, 7]) | PASS | Raw, Buckwheat, Acacia, with ratings and review counts | PASS | |
| E02 | search_products(olive oil), get_rating([9]) | PASS | Organic Extra Virgin Olive Oil ★4.67, plus the order prompt | PASS | |
| E03 | checkout(30) | PASS | Order placed: order ID 29, Oat Milk, $4.49 | PASS | |
| E04 | get_order_history | PASS | Orders newest first, including the Oat Milk order | PASS | Older test orders are listed too |
| E05 | none (blocked) | PASS | Standard redirect to shopping | PASS | |
| E06 | describe_product_image, search_products(honey), get_rating([1–8]) | PASS | All eight honeys | PASS | |
| E07 | – | Not run | – | PASS | Groq daily limit for the photo model; checked by hand in the app (screenshot in the .xlsx) |
| E08 | search_products(honey) with the organic preference, get_rating([1, 3, 5, 7]) | PASS | The four organic honeys | PASS | |
| E09 | none | PASS | "Which number would you like to order, if any?" | PASS | No order placed; the wording could mention "yes" |
| E10 | search_products(almond butter) | PASS | "The store doesn't carry almond butter." | PASS | |
| E11 | search_products(oat milk), get_rating([30]) | PASS | Oat Milk $4.49, plus the order prompt | PASS | |
| E12 | checkout(5) | PASS | Order placed: order ID 31, Organic Buckwheat Honey, $18.99 | PASS | |
| E13 | checkout(1), refused by code | PASS | "Which number would you like to purchase?" | PASS | The model tried to order; the GR-02 code check stopped it |
| E14 | save_preference(max $20) | PASS | "Preference saved. From now on I'll never show anything over $20." | PASS | |
| E15 | – | Not run | – | PASS | Groq daily limit for the photo model; checked by hand in the app: Rolled Oats and Steel-Cut Oats (screenshot in the .xlsx) |

**Totals:**
- Automatic checks: 13 of the 13 rows that ran passed. E07 and E15 couldn't run because of the photo model's daily limit.
- Manual checks: 15 of 15 pass.

---

## Fixes along the way

The first full run passed every automatic check, but four replies were plainly wrong when read. It took three more runs to get them right.

| Run | What went wrong | What changed |
|-----|-----------------|--------------|
| First run | E01, E06, E08 came back empty. E15 showed Organic Granola instead of oats: the photo "looked organic", so the agent searched for organic oats. E13 tried to order, and the report didn't mention it. | Nudge the model once if it returns nothing. Only filter for organic when the shopper asks, or has saved that preference. The runner now flags empty replies and refused order attempts. |
| Second run | E01 and E08 fixed. E06 still gave a generic "Sorry". E15 failed with a Groq "output could not be parsed" error. | If the model still writes nothing after a search, build the list in code from the real search results, respecting a stated minimum rating or "cheapest". Retry on parse errors. |
| Third run | E01 failed on malformed tool calls. E06 ran out of steps fetching ratings one product at a time. E15 failed to parse again. | `get_rating` takes all IDs in one call (the reviews API's batch function). On repeated bad output, answer from the search results; for photos, use the product the image check already found. Search picks the matching products before applying price and organic filters, so "organic oats" no longer falls back to granola. "Oats" no longer matches Oat Milk. |
| Final run (judged) | E01 and E06 fixed. Every row that ran passed. E07 and E15 hit the photo model's daily limit and were checked in the app. | – |

**Open points:**
- E09's reply is safe but generic.
- A day's testing on the free tier can use up the photo model's allowance.

---

## What I learned

- **Automatic checks aren't enough.** The first run passed every tool check while four replies were empty or wrong; reading the replies caught them.
- **Reliability came from code, not the prompt.** The smaller test model often stopped early or sent broken tool calls, so the important parts moved into code: the order check, the list format, and a fallback list built from real search results.
- **Token budget is a product constraint.** On the free tier, batching the rating calls and trimming chat history mattered as much as prompt wording, and testing used the same daily allowance as the demo.
