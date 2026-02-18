# TappsMCP Improvement Recommendations (Agent Perspective)

**Purpose:** Suggestions so TappsMCP can give AI agents the best support and results.  
**Source:** Experience using TappsMCP in this repo (experts, Context7, doc lookup).  
**Audience:** TappsMCP maintainers / operators.

---

## 1. Expert + Context7: Fallback When RAG Is Empty

**What happened:** The agent called `tapps_consult_expert` (testing-strategies) for “best practices for base URLs in tests.” The expert returned zero RAG chunks and low confidence, and suggested calling `tapps_lookup_docs`. The agent then called `tapps_lookup_docs(library="pytest", ...)` and got the needed guidance (fixtures, monkeypatch) from Context7.

**Improvement:** When an expert has **no RAG hits** (e.g. `chunks_used: 0`, `source_count: 0`), TappsMCP could **automatically** try Context7 (or `tapps_lookup_docs`) for the same question or for a derived query (e.g. “pytest fixtures and configuration”), then merge or append that content into the expert response. That way the agent gets one combined answer instead of having to notice the nudge and call lookup_docs in a second step.

**Why it helps:** Agents often try the expert first for “best practices” and stop there if the answer looks conclusive. If the expert says “no knowledge found” without auto-fallback, the agent may not think to call lookup_docs unless the response text explicitly suggests it—and even then, it’s an extra round-trip and a chance to miss the right library/topic.

---

## 2. Workflow: “Consult Expert” Should Imply “Maybe Look Up Docs”

**What happened:** The recommended workflow says “When in doubt: use tapps_consult_expert for domain-specific questions.” It does not say “for testing questions, also consider tapps_lookup_docs(pytest) first or in parallel.” So the agent consulted the expert only; when the expert had no data, the agent hadn’t considered doc lookup up front.

**Improvement:** In AGENTS.md (or server-side recommended_workflow), make the coupling explicit, for example:

- **For testing / pytest questions:** Prefer or combine: `tapps_lookup_docs(library="pytest", topic="…")` and optionally `tapps_consult_expert(domain="testing-strategies")`. If the expert returns low confidence / no chunks, treat that as a signal to call `tapps_lookup_docs` for the relevant library (e.g. pytest).

- **General rule:** “Domain-specific” questions that mention a library (e.g. pytest, FastAPI) should trigger both expert and doc lookup in the agent’s plan, or the server could expose a single tool that does “expert + Context7” when appropriate.

**Why it helps:** Agents follow the written workflow. If the workflow doesn’t say “for testing, also hit pytest docs,” the agent won’t call lookup_docs proactively; it only did so after the expert’s low-confidence note.

---

## 3. Expert Response When RAG Is Empty: Stronger Cues

**What happened:** The expert returned “No specific knowledge found … Consider also calling tapps_lookup_docs(library='<name>')”. That’s a soft suggestion. The agent might still treat the exchange as “expert answered” and not act on the suggestion.

**Improvement:** When the expert has no RAG data for the query, the response could:

- **Explicitly recommend a tool call:** e.g. “No RAG results. Recommended next step: call tapps_lookup_docs(library='pytest', topic='fixtures and configuration')” (with concrete `library` and `topic` when inferable from the question).
- **Include a machine-parseable hint:** e.g. `suggested_tool: "tapps_lookup_docs"`, `suggested_library: "pytest"`, `suggested_topic: "fixtures and configuration"` so agentic loops can automatically trigger the follow-up call.

**Why it helps:** Agents work better with explicit “do this next” and structured hints than with prose-only suggestions. A clear, parseable recommendation makes it more likely the agent will call lookup_docs and get the right library/topic.

---

## 4. Knowledge Base Coverage for Common “Best Practice” Topics

**What happened:** The testing-strategies expert had no chunks about “base URLs in tests,” “hardcoded localhost,” or “config/fixtures for test URLs.” That’s a common need (test configuration, env, fixtures).

**Improvement:** Curate or ingest into the testing-strategies (and related) expert knowledge base:

- Short articles or snippets on: test configuration, base URLs, env vars in tests, pytest fixtures for config, monkeypatch for env.
- Either from Context7 (e.g. pytest docs on fixtures and monkeypatch) or from internal best-practice docs, so the expert has something to retrieve for these queries.

**Why it helps:** When the expert’s RAG has something, the agent gets one high-quality answer. When it doesn’t, the agent depends on fallback behavior (today: manual lookup_docs), which is easy to miss or do suboptimally.

---

## 5. Single “Research” Entry Point (Optional)

**Idea:** A single tool such as `tapps_research(question=..., domain=..., libraries=[...])` that:

1. Calls the domain expert (RAG).
2. If RAG is empty or confidence is below a threshold, calls Context7 / lookup_docs for the given (or inferred) libraries/topics.
3. Returns one combined answer with clear attribution (expert vs. library docs).

**Why it helps:** The agent makes one call and gets the best of both expert and Context7 without having to decide to call a second tool or guess the right library/topic. This would have avoided the “expert first, then separate lookup_docs” sequence in our case.

---

## Summary Table

| # | Improvement | Effect |
|---|-------------|--------|
| 1 | Auto-fallback to Context7 when expert RAG is empty | One response with expert + docs; fewer missed follow-ups |
| 2 | Workflow: “expert + doc lookup” for testing/library questions | Agents call lookup_docs when it matters |
| 3 | Stronger, structured “call tapps_lookup_docs” when no RAG | Higher chance agents actually perform the follow-up |
| 4 | Broader expert KB coverage (test config, URLs, env) | Expert answers more “best practice” questions directly |
| 5 | Optional single “research” tool (expert + Context7) | One call for the agent; simpler and more reliable |

---

*Document created from agent use in this repository. No tool calls required to read or apply.*
