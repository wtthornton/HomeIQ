# LangChain & PDL Research Summary (Nov 2025)

## LangChain

- Latest funding (Oct 2025) indicates continued investment and community support, keeping the framework active for long-term maintenance. Source: [The AI Insider](https://theaiinsider.tech/2025/10/24/langchain-closes-125m-at-1-25b-valuation-to-expand-its-open-source-ai-agent-platform/?utm_source=openai).
- Core building blocks relevant to HomeIQ:
  - `LLMChain` and prompt templates for deterministic prompt construction.
  - Tool abstractions that wrap REST calls (e.g., HomeIQ `data-api`) enabling agent-style workflows without bespoke glue code.
  - Memory components to track conversational context for Ask-AI refinements.
- Deployment considerations: Install `langchain` base package only; avoid vector store extras to keep footprint minimal for a single-home setup.
- Suggested references for developers:
  - LangChain Agents documentation (Context7 access attempted; fallback to https://python.langchain.com/docs/how_to) for tool execution workflows.
  - LangChain Expression Language (LCEL) for composing sequential chains with retry policies.

## Procedure Description Language (PDL)

- Recent arXiv preprint (Feb 2025) outlines PDL for controlled workflow execution in LLM agents. Source: [arXiv:2502.14345](https://arxiv.org/abs/2502.14345?utm_source=openai).
- Key attributes:
  - Combines natural-language descriptions with structured directives so workflows remain auditable.
  - Includes constructs for handling out-of-workflow (OOW) queries, enabling safe fallbacks.
  - Designed to be lightweight enough for single-node environments when interpreted locally.
- Implementation approach for HomeIQ:
  - Define a minimal subset (sequence, condition, fallback) reflecting the paper’s semantics.
  - Execute PDL scripts inside the existing scheduler, emitting run logs to current logging framework.

## Context7 MCP Notes

- `*context7-resolve` attempts for both “LangChain” and “Procedure Description Language” returned unauthorized responses (`ctx7sk-…` key rejected). Investigated during research on 2025-11-10. Until credentials are updated, rely on public docs and cached internal notes.


