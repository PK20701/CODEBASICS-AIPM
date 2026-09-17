# Product Requirements Document — <Product name>

**Date:** YYYY-MM-DD
**Author:** <Your name>

> Claude Code writes `PRD.md` from this template and `PRODUCT_BRIEF.md`. Lines in *italics* say what each section needs and are removed from the finished PRD. Every requirement gets an ID so you, Claude Code, and your evals can point at it.

---

## 1. Overview

*Three or four sentences. What the product is, who it is for, what it does end to end.*

---

## 2. Problem

*What is painful today, for whom. Three bullets.*

- 
- 
- 

---

## 3. Goals

*Each goal has something you could check. "Works well" is not a goal. "No product shown that breaks a stated price cap" is.*

| Goal | How we know |
|------|-------------|
| | |
| | |
| | |

---

## 4. Non-Goals

*What we are deliberately not building. This list is what stops Claude Code from adding a cart.*

- 
- 
- 

---

## 5. Users

*Who uses it and in what situation. One or two sentences.*

---

## 6. Functional Requirements

*One testable statement per row. Number continuously: FR-01, FR-02, and so on. Add a short example under a table when behaviour is not obvious.*

### 6.1 Search

| ID | Requirement |
|----|-------------|
| FR-01 | |

### 6.2 Ratings

| ID | Requirement |
|----|-------------|
| | |

### 6.3 Output format

*The exact line format for a product list, with a two-item example.*

| ID | Requirement |
|----|-------------|
| | |

```
<example list>
```

### 6.4 Ordering

*What counts as a yes, what does not, where the product ID comes from.*

| ID | Requirement |
|----|-------------|
| | |

### 6.5 Photo search

| ID | Requirement |
|----|-------------|
| | |

### 6.6 Memory and preferences

*What order history returns. Which preferences are remembered, where, and how they are applied.*

| ID | Requirement |
|----|-------------|
| | |

---

## 7. Tools

*One row per tool the agent can call.*

| Tool | What it does | Backed by |
|------|--------------|-----------|
| | | |

---

## 8. Guardrails

*One row per guardrail, and whether the prompt or the code enforces it.*

| ID | Guardrail | Enforced by |
|----|-----------|-------------|
| GR-01 | | |
| GR-02 | | |

---

## 9. Demonstration Scenarios

*Five to eight scenarios. Each one: what the shopper says, what should happen. Cover every flow and each guardrail. These become the eval set.*

### Scenario 1 — <name>

User: `<input>`

Expected:

```text
→ <tool called, with filters>
→ <what the shopper sees>
```

### Scenario 2 — <name>

...

---

## 10. Acceptance Criteria

*A checklist you can tick by using the product.*

- [ ] 
- [ ] 
- [ ] 

---

## 11. Technology and Build Instructions

| Component | Choice |
|-----------|--------|
| Language | Python 3.10+ |
| LLM provider and model | |
| Vision model | |
| UI | |
| Preferences stored in | |

*Rules for Claude Code:*

1. Read `SETUP.md` first. Build on top of `initial_setup/`; do not modify it.
2. Ratings come only from `initial_setup/reviews_api.py`.
3. Keep API keys in `.env`.
4. Do not add anything outside this PRD.
