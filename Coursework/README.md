# Coursework: Codebasics AI PM Cohort 2

Assignments and practice builds from the programme. The capstone has its own folder at the repo root.

| Folder | What it is | Built with | Evidence |
|---|---|---|---|
| [`ai-opportunity-assignment-amazon/`](ai-opportunity-assignment-amazon/) | Understand a real business (Amazon Shopping app) and propose AI features, each with the problem, type of AI, data needed and the metric it moves. | Analysis and writing | Three-page PDF |
| [`hello-ai/`](hello-ai/) | Environment check: the first script, to confirm Python and the setup work before the real builds. | Python | One script |
| [`rag-telecom-customer-care-chatbot/`](rag-telecom-customer-care-chatbot/) | **NovaCell** support chatbot that answers only from retrieved knowledge (FAQ, resolved tickets, a PDF guide, the plan catalogue), with a Sources panel and an interaction log. | LangChain, Chroma (four collections), local MiniLM embeddings, Groq, Streamlit | README, screen recording, interaction log |
| [`shopmate-ai-shopping-agent/`](shopmate-ai-shopping-agent/) | **ShopMate**, a shopping agent that searches products, checks ratings, accepts photos and places a one-item order only after an explicit yes. Vibe-coded in Claude Code with me as product owner. | Claude Code, Groq (Qwen), Streamlit, SQLite | PRD, `GUARDRAILS.md`, `EVALS.md` (15-case eval set with a manual check on every row), tests, demo video |

## What each one taught me

- **Opportunity analysis:** start from how the business makes money and where it hurts, then pick AI that moves a named metric (for example return rate), not AI for its own sake.
- **RAG chatbot:** grounding is a product rule, not a prompt wish. The plan catalogue is retrieved in full because similarity search ranks by wording, not price, and a top-3 slice answered "cheapest unlimited plan" confidently and wrongly.
- **ShopMate agent:** guardrails belong in code (an off-topic check before the agent runs, no order without a clear yes) and every behaviour needs an eval row.

## Credit

The business brief, the PRD and problem statement for the RAG chatbot (authored by Dhaval Patel, Codebasics), the sample data and the starter files for ShopMate were provided by Codebasics as the assignment specification. The implementation, tests, evals and write-ups are mine.

Each project has its own README with setup steps. Recreate the virtual environment first (`python -m venv .venv`, then install `requirements.txt`).
