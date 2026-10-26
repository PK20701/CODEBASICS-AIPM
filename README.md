# AI Product Management Portfolio: Codebasics AI PM Cohort 2

Work from the Codebasics **AI Product Management Live Bootcamp** (Cohort 2, 60+ hours of live training, in association with AtliQ Technologies). Completed with the **Certified AI Product Manager** certification (ID CB-176-20844) and **first prize at the capstone Demo Day**.

Four folders, four purposes:

| Folder | What it is | Weight |
|---|---|---|
| [`capstone project - atliq contract risk analyzer/`](capstone%20project%20-%20atliq%20contract%20risk%20analyzer/) | **ContractGuard**, the capstone prototype: a working web tool, a Python serverless API, 100 offline tests and the evals. Deployed on Vercel. | Main showcase |
| [`Capstone-Deliverables/`](Capstone-Deliverables/) | The documents behind the capstone: problem discovery, opportunity map, AI PRD, cost estimate, Demo Day deck. | Product thinking |
| [`Coursework/`](Coursework/) | Assignments from the programme: an AI-opportunity analysis, a RAG customer-care chatbot and a vibe-coded shopping agent. | Learning record |
| [`Learning-Journey/`](Learning-Journey/) | Week-by-week summary: what I learned, what I delivered, and how it adds value to my product work. | Reflection |

## Capstone at a glance: ContractGuard

- **Problem:** a CEO with no in-house lawyers reads every contract alone, late at night. A five-whys showed the cause is not slow reading but missing memory: nobody records what the company has already promised.
- **Approach:** code does the exact checks (entity and law, liability cap, payment terms, past-commitment matching, date arithmetic); the model only reads and extracts. Every quote is verified against the source text. The tool never signs, approves or says "safe to sign": a person decides.
- **Results on my test sets:** 24 of 24 known risks found on a gold set I wrote; 59 of 67 Serious findings valid (88%), labelled by me; 7 of 7 prompt-injection attacks handled; 14 of 14 expected findings on 11 synthetic contracts; 100 of 100 offline tests pass. About 5 cents a review (modelled); review time modelled at 25 hours a month falling to 6, to be measured in an 8-week pilot.
- **Delivery:** live app, serverless API, stored results for the built-in samples (exploring costs nothing), a quota checker, and a per-IP rate limit and daily cap on model calls.

**Try it:** <https://atliq-contract-risk-analyzer-contra.vercel.app/> (open "Incoming: gulf crown hotels msa draft"). Built-in samples are pre-computed; a contract you upload yourself may take longer or show a partial review.

Start at the [capstone README](capstone%20project%20-%20atliq%20contract%20risk%20analyzer/README.md), then the [deliverables](Capstone-Deliverables/README.md).

## What I learned

Week by week, with the evidence in this repo and the value it adds: **[Learning-Journey/](Learning-Journey/README.md)**.

## Credit

The capstone case (AtliQ Technologies, its contracts dataset and the brief) and the specifications for the coursework assignments were provided by Codebasics. The implementation, tests, evals, analysis and write-ups here are my own.

## Author

Prasanna Kamthekar. M.Tech Data Science (BITS Pilani); Certified AI Product Manager (Codebasics).
