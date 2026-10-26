# Capstone deliverables: ContractGuard (AtliQ Contract Risk Analyzer)

The documents behind the prototype, in the order the capstone asked for them. The working code is in [`../capstone project - atliq contract risk analyzer/`](../capstone%20project%20-%20atliq%20contract%20risk%20analyzer/).

| # | Deliverable | File | What it shows |
|---|---|---|---|
| 1 | Problem discovery and user research | [1_Problem_Discovery_and_User_Research.xlsx](1_Problem_Discovery_and_User_Research.xlsx) | The discovery worksheet and the seller-side view: who is affected, where it hurts, and the five-whys that led to "missing memory" rather than "slow reading" |
| 2 | Opportunity map | [2a_Boundary_and_Capability_Map.xlsx](2a_Boundary_and_Capability_Map.xlsx), [2b_Feasibility_Impact_Analysis.xlsx](2b_Feasibility_Impact_Analysis.xlsx), [2c_Impact_vs_Feasibility.png](2c_Impact_vs_Feasibility.png), [2d_Opportunity_Map_Miro_export.pdf](2d_Opportunity_Map_Miro_export.pdf) | What AI should and should not do, its capabilities and guardrails, and the options ranked by impact against feasibility |
| 3 | AI PRD | [3_AI_PRD.docx](3_AI_PRD.docx) | Problem and jobs-to-be-done, personas and user stories, model strategy (rules first, AI only where text is unstructured), functional and non-functional requirements, context and data pipeline, guardrails and failure modes, eval criteria |
| 4 | Cost estimation | [4_Cost_Estimation.xlsx](4_Cost_Estimation.xlsx) | Inference and embedding costs per review (about 5 cents on the recommended two-tier setup), the cost savings case, and the assumptions and sources behind each number |
| 5 | Prototype | [Capstone code and README](../capstone%20project%20-%20atliq%20contract%20risk%20analyzer/README.md) | Live app on Vercel, 100 offline tests, gold-set, red-team and precision evals |
| 6 | Presentation | [6_Demo_Day_Presentation.pptx](6_Demo_Day_Presentation.pptx) | The Demo Day story: pain, five-whys, product, trust, money, the ask |
| 7 | Demo video | [7_Demo_Video_Story_2min.mp4](7_Demo_Video_Story_2min.mp4) | A two-minute story walkthrough in my own voice: the pain, the five-whys, the product, the evidence, the ask |

Live app: <https://atliq-contract-risk-analyzer-contra.vercel.app/>

## How the pieces connect

1. **Discovery** found the root cause: the process ends at signature, so nobody records what was promised.
2. **Opportunity mapping** kept AI to reading and left decisions to a person.
3. **The PRD** turned that into rules: code does exact checks, the model only reads, every quote is verified, the tool never signs.
4. **The cost model** showed the review is affordable at about 5 cents, so the pilot question is value, not cost.
5. **The prototype and evals** tested the rules: gold set, precision, red team, offline tests.
6. **The presentation** told the story to a decision maker and asked for an 8-week pilot with a kill switch.
