# Learning Journey: Codebasics AI Product Management Live Bootcamp (Cohort 2)

What the programme taught, how I applied it in the capstone, and why it matters for the product work I do. I kept running summaries of the sessions (the AI PM briefing, the frameworks and metrics notes, the Session 18 interview-readiness notes, and a presentation-design briefing). This page connects those ideas to the work in this repo.

**Outcome:** 9 weeks, 60+ hours of live training with client and expert sessions. **Certified AI Product Manager** (Hands-on Professional Program, certificate ID CB-176-20844) and first prize at the capstone Demo Day.

**How to read this.** Part 1 is the programme at a glance. Part 2 lists the ideas that shaped the capstone, one row each: what the programme said, what I did with it, and where to see it. Part 3 goes week by week with Covered, Delivered, Skills and Value.

## 1. Programme at a glance

| Week | Theme | Where it shows up in this repo |
|---|---|---|
| 1 | AI PM foundations | [AI opportunity assignment](../Coursework/ai-opportunity-assignment-amazon/), [hello-ai](../Coursework/hello-ai/) |
| 2 | Problem discovery | [Deliverable 1](../Capstone-Deliverables/1_Problem_Discovery_and_User_Research.xlsx) |
| 3 | Opportunity mapping | [Deliverable 2](../Capstone-Deliverables/) |
| 4 | Product metrics and cost | [Deliverable 4](../Capstone-Deliverables/4_Cost_Estimation.xlsx), capstone evals |
| 5 | Prompting and RAG | [RAG telecom chatbot](../Coursework/rag-telecom-customer-care-chatbot/) |
| 6 | AI toolkit and vibe coding | [ShopMate](../Coursework/shopmate-ai-shopping-agent/), the capstone prototype |
| 7 | AI agents and guardrails | [ShopMate guardrails](../Coursework/shopmate-ai-shopping-agent/GUARDRAILS.md), capstone defences |
| 8 | Executive stakeholder management | [Demo Day deck](../Capstone-Deliverables/6_Demo_Day_Presentation.pptx) |
| 9 | Capstone | [ContractGuard](../capstone%20project%20-%20atliq%20contract%20risk%20analyzer/) |

## 2. Ideas from the programme, and how ContractGuard applied them

| Idea from the programme | What I did with it | Evidence |
|---|---|---|
| **Probabilistic, not deterministic.** The same input can give different outputs, so quality and trust become product metrics. About 95% of GenAI pilots fail to show ROI, and the Air Canada chatbot case showed that a confident wrong answer is a legal risk. | The tool never says "safe to sign" or "no conflict". Zero findings reads "No findings from the checks we ran. This is not a clearance." A model claim that cannot be verified is shown as "Not sure, please cross-check", never as fact. | [Capstone README](../capstone%20project%20-%20atliq%20contract%20risk%20analyzer/README.md) |
| **Model selection ladder.** Try rule-based automation first, then traditional ML, then an LLM, then a hybrid. Once accuracy clears the bar, take the cheaper option. | Code does the exact checks (entity and law, liability cap, payment days, past-commitment matching, date arithmetic). The model only reads unstructured text. No RAG or vector database was needed, because the memory is a small structured register of 14 commitments that rules can match. | PRD section 5, [AI PRD](../Capstone-Deliverables/3_AI_PRD.docx) |
| **Brain and body; RAG; agents.** A plain LLM has a knowledge cutoff, RAG grounds it in private documents, and an agent adds tools, memory and autonomy. | Used RAG for the telecom chatbot, an agent for ShopMate, and a tool-free reader for the capstone. The capstone model has no tools, so it cannot send or sign anything. | [RAG chatbot](../Coursework/rag-telecom-customer-care-chatbot/), [ShopMate](../Coursework/shopmate-ai-shopping-agent/) |
| **Autonomy versus guardrails (the tethered-cow analogy).** An agent needs freedom to act and a rope that keeps it off the road. | ShopMate acts on its own but cannot place an order without a clear yes. ContractGuard has zero autonomy by design: a person decides every finding. Hard rules live in code, not only in the prompt. | [GUARDRAILS.md](../Coursework/shopmate-ai-shopping-agent/GUARDRAILS.md) |
| **Data quality and time.** Conflicting documents give inconsistent answers; tag data with time so current and historical can be told apart. | Every restriction carries a computed end date. Expired ones are still shown, labelled expired. Only person-confirmed restrictions are used in later conflict checks. | Capstone README, "How it works" |
| **Three-floor metrics.** Ground floor (accuracy, hallucination, groundedness, latency, token cost, drift), first floor (north star, activation, retention, NPS and CSAT), top floor (financial return). Check AI quality first, user value second, business viability third. | Ground: every quote verified against the source (a groundedness check), under 20 seconds a review, about 5 cents a review. First: a north-star metric, the trusted-review rate, with a pilot target, and a one-tap rating that never blocks. Top: review time modelled from 25 hours a month to 6, labelled as modelled. | [Cost estimate](../Capstone-Deliverables/4_Cost_Estimation.xlsx), PRD |
| **Golden dataset and evals.** Build the expected answers before launch. Evaluation is most of what AI PM interviews test. | A gold set of 24 known risks, an answer key for 11 synthetic contracts, a precision review of 67 findings, and a 7-attack red team, plus 100 offline tests. I report what the labels are: they are mine, so the client should confirm them. | [tests/](../capstone%20project%20-%20atliq%20contract%20risk%20analyzer/tests/) |
| **Responsible AI pre-launch checks (Session 18).** Privacy, governance and regulation, consent, human in the loop. These are different from product metrics: a product can be accurate and fast and still fail a regulator. | Human in the loop is built in. Privacy and governance are named as pilot prerequisites, not claimed as done: contract text goes to model providers today, and production needs a provider agreement and a retention decision. | Capstone README, "Data and privacy" |
| **A model has no moat (Session 18).** If a better, cheaper model appears, users switch in seconds. | The value sits in the register of past commitments, the checks and the workflow, not in one model. The engine rotates across several models and falls back to a second provider. | Capstone README, "Models, keys and limits" |
| **Prioritise with a framework (RICE) and map impact against feasibility.** | The opportunity map ranked options by impact against feasibility and set a clear "should and should not" boundary, including what AI will never do. | [Opportunity map](../Capstone-Deliverables/) |
| **The product builder and vibe coding.** A PM prototype transfers design intent faster than a text PRD; engineers are free to rewrite the code. | I built working prototypes in Claude Code as the product owner, checked what it added that I had not asked for, and described bugs by what I saw and expected. | [ShopMate](../Coursework/shopmate-ai-shopping-agent/), capstone |
| **Translate for two audiences.** Clients hear outcomes, trade-offs and safety; engineers hear cost levers, retrieval and latency. | The Demo Day story speaks in plain words (pain, memory, who decides, what it costs). The README carries the technical detail. | [Demo Day deck](../Capstone-Deliverables/6_Demo_Day_Presentation.pptx), capstone README |
| **Presentation design (avoid death by slides).** One message per slide, no full sentences while speaking, use size and contrast to direct attention, keep objects to six or fewer. | A dark Demo Day deck with one idea per slide, large numbers and call-outs instead of paragraphs. | [Demo Day deck](../Capstone-Deliverables/6_Demo_Day_Presentation.pptx) |
| **Portfolio over credentials; interview readiness (Session 18).** Interviewers want how you frame a problem, measure success and talk to engineers, not a memorised answer. | This repo: a live product, the documents behind it, tests and evals, and honest limits. | [README](../README.md) |

## 3. Week by week

### Week 1: AI PM foundations
- **Covered:** how an AI PM differs from a traditional PM, product owner, business analyst and program manager (the AI PM owns vision and strategy, the PO owns the backlog); core, applied and forward-deployed roles; probabilistic systems; the model-selection ladder; RAG and agents as a ladder of capability.
- **Delivered:** an [analysis of the Amazon Shopping app](../Coursework/ai-opportunity-assignment-amazon/): how the business earns, where it goes wrong, what data it collects, then AI features each with the problem solved, the type of AI, the data needed and the metric it moves. A small [environment check](../Coursework/hello-ai/).
- **Skills:** turning a business into a short list of AI opportunities with named metrics; choosing between rules, classical ML and an LLM.
- **Value:** I ask "does this need AI at all?" before "which model?", which saves cost and scope in any data or product initiative.

### Week 2: Problem discovery
- **Covered:** user research, empathy profiles, jobs-to-be-done, the five-whys method.
- **Delivered:** [problem discovery and user research](../Capstone-Deliverables/1_Problem_Discovery_and_User_Research.xlsx). The five-whys moved the problem from "he reads too slowly" to "nobody records what the company has already promised".
- **Skills:** separating symptom from cause, and writing a problem so a solution can be tested against it.
- **Value:** better requirements. The right fix (a memory of past commitments) differed from the obvious one (a faster reader).

### Week 3: Opportunity mapping
- **Covered:** where AI helps and where it should not, capability and guardrail boundaries, feasibility against impact, Miro workshops, prioritisation.
- **Delivered:** [boundary and capability map, feasibility and impact analysis, Miro export](../Capstone-Deliverables/).
- **Skills:** deciding what AI will not do (it never signs or approves) and defending that boundary.
- **Value:** a clear scope, and a story for stakeholders about what is in, what is out and why.

### Week 4: Product metrics and cost
- **Covered:** the three-floor metrics model with worked examples (accuracy, hallucination rate, groundedness, latency percentiles, tokens per query, data and concept drift, north star, DAU and MAU, retention, NPS against CSAT, MRR, ARR, ARPU, CAC, LTV), and cost estimation from tokens.
- **Delivered:** the [cost estimate](../Capstone-Deliverables/4_Cost_Estimation.xlsx) (about 5 cents a review) and the capstone's north-star metric and pilot targets, set up for measurement rather than claimed.
- **Skills:** defining success before building, and separating what was measured from what was modelled.
- **Value:** I can say what "working" means in numbers, and I label modelled figures as modelled.

### Week 5: Prompting and RAG
- **Covered:** context windows, chunking, retrieval, grounding, evaluating retrieval pipelines, golden datasets.
- **Delivered:** the [NovaCell RAG customer-care chatbot](../Coursework/rag-telecom-customer-care-chatbot/): four knowledge collections, local embeddings, answers only from what was retrieved, a Sources panel and an interaction log. A lesson from it: similarity search ranks by wording, not price, so the full plan catalogue is retrieved for comparison questions.
- **Skills:** designing retrieval for the questions users really ask, and enforcing grounding in the product rather than hoping for it in the prompt.
- **Value:** I can review a RAG proposal and ask about sources, retrieval depth and failure behaviour.

### Week 6: AI toolkit and vibe coding
- **Covered:** building working prototypes with AI coding tools, with the PM as product owner and the tool as engineer; the wider toolkit (Miro, Canva, workflow tools such as n8n, hosting on Vercel).
- **Delivered:** [ShopMate](../Coursework/shopmate-ai-shopping-agent/), built from a PRD in Claude Code, and the [ContractGuard prototype](../capstone%20project%20-%20atliq%20contract%20risk%20analyzer/): a static web page and a Python serverless API on Vercel.
- **Skills:** specifying clearly, reviewing what the tool adds that was not asked for, and describing a bug by what I saw and what I expected.
- **Value:** I can take an idea from a spec to a working, testable prototype, which makes talks with engineers faster and more concrete.

### Week 7: AI agents and guardrails
- **Covered:** an agent as a model plus tools, knowledge and memory; autonomy against guardrails; input and output guardrails; domain experts in setting risk limits.
- **Delivered:** ShopMate's [guardrails](../Coursework/shopmate-ai-shopping-agent/GUARDRAILS.md) (an off-topic check before the agent runs, no order without a clear yes, both enforced in code) and its [15-case eval set](../Coursework/shopmate-ai-shopping-agent/EVALS.md). In the capstone: screening for instructions hidden in contracts, a filter that blocks "safe to sign", a check that every quote appears in the source, and a [red-team script](../capstone%20project%20-%20atliq%20contract%20risk%20analyzer/tests/redteam.py) (7 of 7 attacks handled).
- **Skills:** putting hard rules in code, giving the model no tools it does not need, testing attacks on purpose.
- **Value:** safer AI features, and a habit of writing the "must never do" list first.

### Week 8: Executive stakeholder management
- **Covered:** working with executives, using strategies drawn from senior leaders' experience, stakeholder-mapping exercises, and (in Session 18) what one slide for a CEO should hold: the state of the business in numbers, with a reference point.
- **Delivered:** the [Demo Day presentation](../Capstone-Deliverables/6_Demo_Day_Presentation.pptx): pain, five-whys, product, evidence with honest limits, and an ask for an 8-week pilot with a kill switch.
- **Skills:** telling the story to a mixed audience and stating limits plainly (the 24 known risks were my own gold set; the time saving is modelled).
- **Value:** decisions get made faster when the ask, the evidence and the limits are on one page.

### Week 9: Capstone, ContractGuard
- **Covered:** end-to-end design, build, evaluation and presentation of an AI product in a competitive setting.
- **Delivered:** [PRD](../Capstone-Deliverables/3_AI_PRD.docx), [cost model](../Capstone-Deliverables/4_Cost_Estimation.xlsx), a [live prototype](https://atliq-contract-risk-analyzer-contra.vercel.app/) with 100 offline tests, 24 of 24 known risks found, 88% of Serious findings valid, 7 of 7 injection attacks handled, stored results so exploring costs nothing, and a daily cap and rate limit on model calls. A [two-minute demo video](../Capstone-Deliverables/7_Demo_Video_Story_2min.mp4). First prize at Demo Day.
- **Skills:** running the whole product loop alone: discover, define, build, test, cost, present.
- **Value:** proof that I can own an AI product from problem to pilot proposal, including the unglamorous parts (cost control, quota limits, honest reporting).

## 4. What stays with me

| Habit | Where it shows |
|---|---|
| Rules first, model second | Capstone engine, ShopMate guardrails |
| Define success before building | Gold set, eval sets, north-star metric |
| Say what was measured, what was modelled and who labelled the data | Demo Day deck, capstone README |
| A human decides | ContractGuard never signs; ShopMate never orders without a yes |
| Treat cost as a requirement | Cost model, rate limit, stored sample results |
| Try to break it on purpose | Red-team script, off-topic checks |

## 5. What I would do next

- Run the 8-week pilot (shadow mode, then a closed beta) and measure the north star and the time saving instead of modelling them.
- Add drift monitoring: new contract types and changing policies are the data and concept drift the programme warned about.
- Complete the privacy and governance work a production launch needs: a provider agreement, a retention decision and an access model.

## Tools I used

Claude Code and Claude (building and writing), Gemini and Groq models (inference), LangChain and ChromaDB (retrieval), Streamlit and SQLite (prototypes), Vercel (hosting), Miro (opportunity mapping), Excel (cost and discovery sheets), VS Code and Git.
