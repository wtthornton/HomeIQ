# LLM and ML Models — What Each Does and Value Rank (1–100)

**Generated:** February 18, 2026  
**Purpose:** For each model (or model-backed capability), summarize what it does, who benefits, and rank its value from 1 (low) to 100 (critical differentiator).

**Value scale:**
- **90–100:** Core product; user-facing; hard to replace; central to “ask AI for automation.”
- **70–89:** Critical for main flows; high user impact; clear differentiator.
- **50–69:** Important for quality or key features; visible or strongly enabling.
- **30–49:** Useful backend or niche feature; lower traffic or optional.
- **1–29:** Experimental, dev-only, or not yet integrated.

---

## 1. HA AI Agent (OpenAI: gpt-5-mini / gpt-5.2-codex)

**What it does:** Conversational AI for Home Assistant. User talks in plain English; the agent uses Tier 1 context (entities, areas, services, capabilities), calls the single tool `create_automation_from_prompt`, and produces/validates automations. Handles chat history, token budget, and YAML creation.

**Who benefits:** End users creating automations via the main “talk to AI” experience.

**Value rank: 95**  
Primary product surface. Directly delivers “describe what you want → get an automation.” Without it, there is no conversational automation creation.

---

## 2. AI Automation Service — YAML / HomeIQ JSON generation (OpenAI: gpt-5.2-codex)

**What it does:** Takes a chosen intent/template and compiles it into Home Assistant automation YAML (and HomeIQ JSON). Handles structure, entity IDs, conditions, and actions. Used by the hybrid flow and by the HA AI Agent’s tool.

**Who benefits:** Every flow that ends in “create this automation in HA” (agent-driven and template-driven).

**Value rank: 92**  
Turns high-level intent into deployable automation. Core to the “automation out” path; quality here directly affects whether automations work.

---

## 3. AI Query Service — entity extraction (OpenAI: gpt-5-mini)

**What it does:** Natural-language → structured extraction: devices, rooms, actions, and related slots from phrases like “turn on the office light when I get home.” Feeds clarification detection and suggestion generation. Target P95 &lt;500 ms.

**Who benefits:** AI Automation (intent/template selection and YAML), HA AI Agent (implicit via automation flow), and any NL-driven automation UX.

**Value rank: 88**  
Correct entity/room/action mapping is essential for automation accuracy. Directly prevents wrong device/room and improves “first try works” experience.

---

## 4. AI Automation Service — intent planning / template selection (OpenAI: gpt-4o-mini)

**What it does:** Interprets user request and selects (or proposes) automation templates/intents (e.g. “turn on light when motion”) and feeds the YAML/JSON generation step.

**Who benefits:** Template-based and hybrid automation flows; drives what gets sent to the YAML model.

**Value rank: 85**  
Central to the “plan then compile” path. Good intent selection means correct template and fewer failed automations.

---

## 5. Proactive Agent — prompt generation (OpenAI: gpt-5-mini)

**What it does:** Analyzes weather, sports, energy, and patterns; calls OpenAI to generate a small set of proactive automation suggestions (e.g. “turn off AC when solar is high”); stores and serves them. Can trigger HA AI Agent to realize them.

**Who benefits:** Users who want “AI suggests what to automate” without having to phrase it themselves.

**Value rank: 78**  
Strong perceived value and differentiator. Depends on context pipelines and HA Agent; not the single point of failure for core “create automation” path.

---

## 6. OpenVINO — embeddings (BAAI/bge-large-en-v1.5)

**What it does:** Converts text to 1024-dim vectors. Used by RAG service for semantic store/retrieve and by ai-pattern-service (e.g. pattern learner) for similarity.

**Who benefits:** RAG semantic search (when consumed); pattern/synergy and blueprint matching; future retrieval-augmented features.

**Value rank: 65**  
Enables semantic search and pattern similarity. Value is shared across RAG and pattern/blueprint features; RAG HTTP API is not yet widely consumed.

---

## 7. Energy forecasting (Darts: N-HiTS, TFT, Prophet, etc.)

**What it does:** Time-series forecasting of energy consumption; peak prediction; “best hours for high-power activities” type recommendations.

**Who benefits:** Energy-conscious users and automations that optimize for cost or grid.

**Value rank: 62**  
Clear value for a defined segment; not required for core “create an automation” flow.

---

## 8. RAG context injection — keyword + static corpus (RAGContextService)

**What it does:** Keyword-based domain detection (sports, energy, comfort, security, scene/script) and injection of prewritten corpus snippets into the HA AI Agent prompt. No embedding API; local files + registry.

**Who benefits:** Users whose prompts match those domains; improves agent answers with curated patterns.

**Value rank: 60**  
Improves answer quality for specific domains without extra API calls. Bounded by keyword coverage and corpus quality.

---

## 9. OpenVINO — pattern classifier (google/flan-t5-small)

**What it does:** Classifies pattern descriptions into category (energy/comfort/security/convenience) and priority (high/medium/low). Used in the pattern pipeline.

**Who benefits:** Pattern analysis, prioritization, and any feature that depends on pattern categories.

**Value rank: 58**  
Useful for organization and prioritization of patterns; not the main user-facing “create automation” path.

---

## 10. Device Intelligence — AI name suggestions (OpenAI: gpt-4o-mini; optional Ollama: llama3.2:3b)

**What it does:** Suggests friendly names for devices/entities (e.g. “Living Room Ceiling Light”) from raw entity/device data. Optional local LLM via Ollama.

**Who benefits:** Users during setup and device discovery; improves readability of dashboards and automation UIs.

**Value rank: 55**  
Quality-of-life improvement; naming can be done manually or with simple rules.

---

## 11. Rule Recommendation ML (implicit + ONNX)

**What it does:** Collaborative filtering (e.g. ALS) on Wyze-style rule data; recommends “rules” (automation patterns) by user or device domain; similar rules and popular rules. Optional ONNX deployment.

**Who benefits:** Users looking for “automations others like” or “what to add next.”

**Value rank: 55**  
Useful discovery feature; depends on dataset and adoption; not required for core creation flow.

---

## 12. OpenVINO — reranker (BAAI/bge-reranker-base)

**What it does:** Re-ranks candidate passages/documents (e.g. search results) by relevance to a query. Used with embedding search for better ordering.

**Who benefits:** Any flow that uses “retrieve then rerank” (e.g. RAG, pattern search) when integrated.

**Value rank: 52**  
Improves retrieval quality when used; currently secondary to embedding search.

---

## 13. ML Service (scikit-learn: clustering, anomaly detection)

**What it does:** Classical ML: clustering (e.g. KMeans, DBSCAN), anomaly detection (e.g. Isolation Forest). Stateless, no pre-trained models; used for analytics and pattern grouping.

**Who benefits:** Analytics and pattern-discovery features that consume this API.

**Value rank: 50**  
Useful for analytics and grouping; not the primary automation-creation path.

---

## 14. Evaluation — LLM Judge (OpenAI: gpt-4o-mini or Anthropic: Claude)

**What it does:** In the shared evaluation framework, scores agent sessions (e.g. tool choice, sequence, outcome) using rubrics and an LLM when rule-based checks are insufficient. Used in integration/eval tests and pipeline evaluations.

**Who benefits:** Developers and QA; product quality indirectly.

**Value rank: 45**  
Important for quality assurance and regression; not end-user facing.

---

## 15. Activity recognition (custom LSTM → ONNX)

**What it does:** Classifies household activity (sleeping, waking, leaving, arriving, cooking, eating, working, etc.) from sequences of sensor readings (motion, door, temp, humidity, power). Exposes a predict API.

**Who benefits:** Automations or analytics that would adapt to “what is the user doing.” Currently no other services found calling this API in the repo.

**Value rank: 42**  
High potential for context-aware automation; value is limited until integrated into agent or automation flows.

---

## 16. RAG Service — semantic store/retrieve (OpenVINO embeddings)

**What it does:** Stores text with embeddings; retrieves by similarity (cosine); optional rerank. Provides HTTP API for store/retrieve/search. HA AI Agent today uses RAGContextService (keyword + corpus), not this HTTP RAG API.

**Who benefits:** Future consumers of semantic retrieval (e.g. agent context, pattern search). Today: infrastructure for when those flows are wired.

**Value rank: 40**  
Enables future semantic-augmented features; current value is lower because no major consumer is wired in codebase.

---

## Summary table (by value rank)

| Rank | Component | Model / stack | Value | One-line role |
|------|-----------|----------------|-------|----------------|
| 1 | HA AI Agent | OpenAI gpt-5-mini / 5.2-codex | **95** | Main conversational “create automation” experience. |
| 2 | AI Automation (YAML) | gpt-5.2-codex | **92** | Compiles intent → HA YAML/HomeIQ JSON. |
| 3 | AI Query Service | gpt-5-mini | **88** | Entity/room/action extraction from natural language. |
| 4 | AI Automation (intent) | gpt-4o-mini | **85** | Intent/template selection for automation. |
| 5 | Proactive Agent | gpt-5-mini | **78** | Generates proactive automation suggestions. |
| 6 | OpenVINO embeddings | BGE-large-en-v1.5 | **65** | Text → vectors for RAG and pattern similarity. |
| 7 | Energy forecasting | Darts (N-HiTS, TFT, etc.) | **62** | Energy forecasts and peak/optimization tips. |
| 8 | RAG context (keyword) | RAGContextService | **60** | Injects domain corpus into HA Agent prompt. |
| 9 | OpenVINO classifier | flan-t5-small | **58** | Pattern category and priority. |
| 10 | Device Intelligence names | gpt-4o-mini / Ollama | **55** | AI-suggested device/entity names. |
| 11 | Rule Recommendation ML | implicit + ONNX | **55** | Personalized rule/pattern recommendations. |
| 12 | OpenVINO reranker | bge-reranker-base | **52** | Re-ranks retrieval candidates. |
| 13 | ML Service | scikit-learn | **50** | Clustering and anomaly detection. |
| 14 | Evaluation LLM Judge | gpt-4o-mini / Claude | **45** | Eval scoring when rules are insufficient. |
| 15 | Activity recognition | LSTM ONNX | **42** | Activity from sensor sequences (not yet wired). |
| 16 | RAG Service (HTTP) | OpenVINO embeddings | **40** | Semantic store/retrieve (no major consumer yet). |

---

## Takeaways

- **Top 4 (85–95)** are the core “create automation” stack: HA AI Agent → intent/entity → YAML. Prioritize reliability, latency, and model quality here.
- **Proactive Agent (78)** is a strong differentiator; keep it stable and visible.
- **OpenVINO (52–65)** supports RAG and pattern/blueprint features; upgrading embeddings/reranker/classifier helps once those flows are more used.
- **RAG HTTP (40)** and **activity recognition (42)** are high-potential but underused; value will rise when integrated into agent or automation flows.
- **Evaluation Judge (45)** is dev/QA-only; keep cost-controlled (e.g. gpt-4o-mini) unless you need higher judge consistency.
