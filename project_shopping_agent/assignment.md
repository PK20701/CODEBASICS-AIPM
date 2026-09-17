# Assignment 1 — AI Shopping Agent

**Cohort:** AI Product Management
**Mode:** Vibe-coded, entirely inside Claude Code. You are the product owner; Claude Code is the engineer. You do not write code by hand.
**Due:** 17th

---

## What you are given

| File | What it is | When to use it |
|------|------------|----------------|
| `PRODUCT_BRIEF.md` | What the product is and what it must do. | Read first. Everything is built from it. |
| `SETUP.md` | Technical setup. Hand it to Claude Code as-is. | Before you build. |
| `PRD_TEMPLATE.md` | The shape your PRD must take. | Step 1. |
| `eval_set.csv` | Five starter test cases. | Step 5. |
| `initial_setup/` | Creates the store database and the reviews API. | Do not modify. |
| `resources/` | Three test images: honey, oats, and an elephant. | Steps 2, 4 and 5. |

---

## How to work

Open a terminal in this folder, run `claude`, and stay there. Tell Claude Code to read the files above rather than pasting them. Review everything it produces before accepting it. It will happily add things that are not in the brief; catching that is your job.

When something is wrong, describe what you saw and what you expected. *"I said 'yes' and it ordered Manuka honey, but the list showed Raw Honey as #1."* Do not try to diagnose the code.

---

## Before you start: setup

`SETUP.md` is technical by design. You do not need to understand it. Open Claude Code in this folder and tell it to read `SETUP.md` and get the environment ready. It will create the virtual environment, the store database, and the `.env` file for your API key. When it is done, ask it to run the two sanity checks at the bottom of `SETUP.md` and show you the output. Both must pass before Step 1.

---

## The five steps

### Step 1 — PRD

Tell Claude Code to read `PRODUCT_BRIEF.md`, `PRD_TEMPLATE.md` and `SETUP.md`, and write `PRD.md` following the template. One rule for it: add nothing that is not in the brief.

Then read the PRD yourself. For every requirement, ask where in the brief it comes from. If you cannot point to a line, cut it. Usual suspects: a shopping cart, quantities, a recommendation engine. Rewrite the overview and goals in your own words if they read like a copy of the brief.

When you are happy, tell Claude Code: the PRD is the spec, build only what is in it.

### Step 2 — The agent

Tell Claude Code to build the whole thing from `PRD.md`: all the tools, the three flows, memory and preferences, and a chat interface with image upload. Streamlit is a good default. Let it finish.

Then run these checks yourself:

| Say this | You should see |
|----------|----------------|
| "organic honey with 4.5+ rating under $20" | Organic Raw Honey, Organic Buckwheat Honey, Organic Acacia Honey. Not Manuka (too expensive). |
| "cheapest oat milk" | Oat Milk at $4.49. |
| Upload `resources/honey.png`, "find this" | A list of honeys. |
| "yes" after a single-item list | An order confirmation with an order ID. |
| "what have I ordered before?" | The order you just placed. |
| "I always want organic", then restart the app and search for honey | Only organic honeys. |

For every miss, tell Claude Code what you saw and what you expected, and re-run all the checks after each fix. One fix often breaks something else.

### Step 3 — Demo video

When the checks pass, record a two-minute Loom of the working agent. Screen plus your voice, no editing. Do it now, before guardrails and evals change things. Put the link in your README.

Talk like a product manager showing a stakeholder the build: what the shopper is trying to do, and what they get back.

### Step 4 — Guardrails

Two guardrails:

1. **Off-topic guardrail.** Before the agent runs, check whether the message is about shopping in this store. "Write me a poem", "what's the weather", and the elephant photo get a polite redirect and never reach the agent.
2. **No order without a yes.** The agent must not call checkout unless the shopper clearly confirmed. Ask Claude Code whether this is enforced in the prompt only or also in code, and decide which you want.

Describe each one to Claude Code in plain language, let it build, and test with the inputs above.

Then have Claude Code write `GUARDRAILS.md` with one short block per guardrail: what it blocks, where it sits, one input that trips it and one that does not. Edit it until you could explain every line.

### Step 5 — Evals

`eval_set.csv` has five test cases. Each row is: what the shopper says, any setup needed, which tool should be called with which filters, and what the reply should contain.

1. **Extend it to 10 to 15 cases.** Add at least: photo search with `honey.png`, the elephant photo, a saved preference being applied, an ambiguous confirmation like "maybe", and a product the store does not sell. Write rows yourself, or describe the situations to Claude Code and correct what it drafts.
2. **Have Claude Code build a runner.** For each row it runs the agent, checks that the right tool was called with the right filters, and prints the agent's reply next to your expected reply.
3. **Judge the replies yourself.** Go down the list. Pass or fail, with a note on every fail.
4. **Fix and re-run.** Ask Claude Code to fix what failed, run again, and note what changed.

Have Claude Code write `EVALS.md`: the full test set, a results table with your pass/fail per row, and two or three sentences on what you learned.

---

## Deliverables

### Due 17th

| # | Deliverable | What to hand in |
|---|-------------|-----------------|
| 1 | Agent | Code, `PRD.md`, and a `README.md` that says how to run it. All generated by Claude Code. |
| 2 | Demo | Two-minute Loom link in the README. |
| 3 | Guardrails | `GUARDRAILS.md` and the working guardrails. |
| 4 | Evals | `EVALS.md`, your extended `eval_set.csv`, the runner, and one run's results with your pass/fail on each row. |

### Next week

Not due now, but keep an eye on both while you build:

- **Metrics.** What would tell you this agent is working in production? Note ideas as they occur to you.
- **Cost.** Every shopper message triggers one or more LLM calls, billed on tokens. Note which model you used and bookmark your provider's pricing page. Next class turns this into a cost per conversation.
