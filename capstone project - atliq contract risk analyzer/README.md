# ContractGuard: AtliQ Contract Risk Analyzer (prototype)

A web tool that reads an incoming contract, checks every clause against AtliQ's own history, and gives the signer a short list of what to look at, most serious first. It never signs, sends or approves anything. A person decides.

Built for the AI PM capstone. Dataset "today" is 28 Sep 2026, so a few register entries that expired after that are shown as expired.

## What it does

1. **Home** shows every contract in a table (like the contract register), with a welcome line, status chips, search, a **+** button, and a second tab with the 14 past commitments (non-competes, exclusivity, most-favoured pricing, IP handed over, data location).
2. **Add contract or version**: paste text or upload a file (text, Markdown, PDF, Word). Optionally add unofficial discussions (call notes, chat export, transcript). The tool reads client, type, term, fees and law from the contract; the user confirms them and answers "were any terms agreed outside the contract?".
3. **Review** (typically 5 to 40 seconds): every clause is read. Findings are shown one line each, **Serious / Negotiable / Minor**, most serious first. Open one to see the exact quote from the contract, why it matters, and how it compares with past contracts.
4. **Decide**: *Accept risk* (a written reason is required for Serious ones) or *Needs review*. *Save draft* at any time.
5. **Proceed to manual signing**: records the contract as "in manual signing", queues any new restrictions (with computed end dates) for confirmation in the register, and downloads a summary with every decision and reason.
   Restrictions queued here appear in the **Past commitments** tab as "to confirm". Open one, check it against the source clause, correct the activity, customers, region or end date, then **Confirm** (or **Reject**). Only confirmed restrictions are used in later conflict checks; the contract being reviewed never collides with its own restrictions.
6. **Rate the review**: one tap, optional stars, reasons only when something was missed or the rating is 3 or lower. Never blocks.

## How it works (rules where a rule is enough, a model only for reading)

| Done by code (deterministic) | Done by the model (Gemini, Groq as backup) |
|---|---|
| Entity vs governing law and courts (AtliQ Inc is US only, Pvt Ltd is India) | Reading the contract into structured fields |
| Liability cap as a multiple of the last 12 months of fees; compared with past contracts | Spotting unusual or one-sided clauses |
| Payment days, uncapped delay penalties, cyber insurance above $1M | Reading call notes and chats for terms agreed outside the contract |
| Health data without a BAA, EU data without a DPA | Suggesting which past commitments might apply |
| Past-commitment matching by region, industry and hourly rates (e.g. Crestline most-favoured pricing) | |
| Date arithmetic for how long a new restriction lasts | |
| **Every quote is checked to appear in the source text.** If it does not, the item is shown as "Not sure, please cross-check" and never as fact | |

The tool never says "safe to sign" or "no conflict". Zero findings is shown as "No findings from the checks we ran. This is not a clearance." Expired restrictions are still shown, labelled expired.

## Run locally

Python 3.10+ only (no Node needed).

```bash
pip install -r requirements.txt
# create .env next to dev_server.py with your keys (never commit it):
#   GEMINI_API_KEY=...
#   GROQ_API_KEY=...        (backup, optional)
python dev_server.py
# open http://localhost:8765
```

## Deploy on Vercel

1. Push this folder to GitHub (the folder containing `vercel.json`, `api/`, `public/`).
2. In Vercel: **Add New Project**, import the repo, set the root directory to this folder, framework preset **Other**. No build command.
3. **Settings, Environment Variables**: add `GEMINI_API_KEY` and `GROQ_API_KEY` (Production and Preview). Redeploy.
4. Open the URL and run a sample from **Try a sample** on the Add screen.

`vercel.json` serves `public/` and runs `api/review.py` (Python serverless function, 60 s limit). The review runs as many short calls from the browser so no single call hits a time limit.

## Models, keys and limits

* **Gemini free tier first.** The free tier allows about 15 requests a minute per model, so the engine rotates `gemini-flash-lite-latest`, `gemini-3.1-flash-lite`, `gemini-3-flash-preview`, `gemini-3.6-flash`.
* **Groq automatically takes over** when Gemini is rate-limited or down (`gpt-oss-120b`, `qwen3.8-27b`, `gpt-oss-20b`). A small "backup model used" badge shows in the header. Groq's free tier is tighter (about 8,000 tokens a minute per model), so it can sustain roughly three reviews a minute.
* If both are exhausted, the app says so and nothing is lost; try again in a minute.
* Override with env vars: `GEMINI_MODEL_FAST`, `GEMINI_MODEL_SMART`, `GEMINI_ROTATION`, `GROQ_MODEL`, `GROQ_ROTATION`. `FORCE_GEMINI_FAIL=1` forces the backup path for testing.
* **Cost**: the 15 dataset drafts (about 2,900 tokens each) used about 11,000 input and 2,500 output tokens per review. A typical real contract is longer (about 6,000 tokens, 10 pages), modelled at about 18,000 input and 4,000 output tokens, roughly 5 cents a review with the recommended two-tier setup (a 40-page outlier is about 12 cents). Free tier today. See the cost estimate for the assumptions.

## Data and privacy

* No login in the demo; the greeting defaults to "Karandeep". Drafts, decisions, ratings, new register entries and the audit log live in the browser's localStorage only (the "Reset demo data" link is under **Principles**). The server stores nothing.
* Contract text is sent to the model providers for review. In production this would need an agreement with the provider and a retention decision (see the PRD).
* `data/register.json` (14 past commitments with verified quotes), `benchmark.json` (what 17 signed contracts look like), `principles.json` (9 light principles, a preference not a rule) were built from the 17 signed contracts in the dataset by `tools/make_data.py`, which also checks that every register quote appears in its source file.

## What was added to the dataset

* `public/samples/synthetic/`: 11 invented contracts for testing and demo (S01 to S10 are the core set; S11 shows the register building itself), plus 2 note files (call notes, chat export). Built by `tools/make_synthetic.py` with an answer key in `tests/answer_key.json`.

| ID | Case | What a correct review must find |
|---|---|---|
| S01 | Orion Retail MSA, clean | No Serious finding |
| S02 | Coastal Mutual Insurance (Brightwater-type) | Unlimited liability, uncapped delay penalty, 60-day payment, one-sided indemnity |
| S03 | Maple Street Bakery, $500k cap on $24k a year | Liability cap about 21x fees, Serious |
| S04 | Vantage "Mutual" NDA that binds only AtliQ | One-sided despite the title |
| S05 | Granite Peak, truly mutual NDA | No Serious finding |
| S06 | Sterling Care, patient data | No BAA; $5M cyber insurance vs AtliQ's $1M |
| S07 | Marina Bay Resorts (Dubai) | Collides with Al Noor non-compete until Sep 2029; new 6-month restriction recorded with computed end date |
| S08 | Redwood Software (US client) on the India entity | Wrong entity and law |
| S09 | Fieldstone Foods + call notes | Verbal 10% year-2 discount not in the contract |
| S10 | Bluewater Marine + chat export | Scope cut and 60-day payment agreed in chat, not in the contract |
| S11 | Coral Bay Hotels (Abu Dhabi), a second hotel group | The Al Noor collision; and, once S07's new restriction has been confirmed, a collision with Marina Bay too |

The 15 incoming drafts and 17 signed contracts from the dataset are also available in the sample picker and the contract pages.

## Tests

```bash
python tests/test_units.py                 # 63 offline unit tests: quotes, ratios, dates, entity/law, documents, segmentation, merge, confirmed register, API
python tests/test_register_chain.py        # sign S07, confirm its restriction, review S11: the new restriction must be found (uses the model)
python tests/eval_synthetic.py             # full pipeline on S01-S10 against the answer key
python -u tests/run_real.py                # full pipeline on the 15 real incoming drafts
FORCE_GEMINI_FAIL=1 python tests/eval_synthetic.py S06 S09 S07   # backup-model path
python tests/live_check.py https://your-app.vercel.app S06 S02 S07 S09 S01   # same calls the browser makes, against the deployed site
```

Results at submission (Gemini free tier):

* Unit tests: 63 of 63 pass.
* Register chain: a restriction extracted from S07 and confirmed by a person is found when S11 (another hotel group in the UAE) is reviewed; a pending, rejected or same-contract entry is never used.
* Synthetic set: 13 of 13 expected findings found, 0 false alarms on the two clean contracts (S01, S05), 0 unverified quotes on model findings except one empty-title item that is now filtered.
* Real drafts: 15 of 15 reviewed, every clause read (e.g. 85 of 85 on the 85-clause Harrington MSA), 4 to 40 seconds each (the drafts are shorter than a typical real contract). LoopMart's genuinely mutual NDA correctly gives no findings.
* Backup path: with Gemini forced off, three reviews in a row matched the answer key on Groq before its free-tier token limit was reached.

## Known limits

* Scanned PDFs without a text layer are not read (the Orbit scan in the dataset is provided as text).
* The register covers the 17 signed contracts on file; 13 other signed contracts are not in the dataset, and the review says so ("checked N past commitments from the 17 signed contracts on file").
* Model findings can be wrong or incomplete; the tool over-flags on purpose, and every finding carries its quote so a person can confirm in seconds. It is an aid for the signer, not legal advice.
* Browser-only storage means decisions are per browser. A production version would use a database and real login.

## Folder map

```
api/_core.py        review engine (rules, model client, prompts, quote verification)
api/review.py       Vercel function: one endpoint, several actions
dev_server.py       local server (same code as Vercel)
public/index.html   the whole web app
public/data/        register, benchmark, principles, contract tracker, sample list
public/samples/     signed, incoming and synthetic contracts
tools/              data and synthetic-contract builders
tests/              unit tests, evaluation against the answer key, real-draft runner, saved results
```
