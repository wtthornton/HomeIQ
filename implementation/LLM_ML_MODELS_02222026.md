# LLM and ML Models — Verified Inventory, Value Rankings & Recommendations

**Date:** February 22, 2026
**Source:** Verified against source code, config.py files, and docker-compose.yml
**Replaces:** `LLM_ML_MODELS_REVIEW_AND_RECOMMENDATIONS.md` (Feb 18), `LLM_ML_MODELS_VALUE_RANKING.md` (Feb 18)

---

## Value Scale

- **90–100:** Core product; user-facing; central to "ask AI for automation."
- **70–89:** Critical for main flows; high user impact; clear differentiator.
- **50–69:** Important for quality or key features; visible or strongly enabling.
- **30–49:** Useful backend or niche feature; lower traffic or optional.
- **1–29:** Experimental, dev-only, or not yet integrated.

---

## 1. Cloud LLMs (OpenAI) — Currently Deployed

| Rank | Service | Model in Code | Env Override | Purpose | Value |
|------|---------|--------------|--------------|---------|-------|
| 1 | **ha-ai-agent-service** | `gpt-5.2-codex` | `OPENAI_MODEL` | Main conversational "describe → automate" experience | **95** |
| 2 | **ai-automation-service-new** (YAML) | `gpt-5.2-codex` | `OPENAI_YAML_MODEL` | Compiles intent into HA automation YAML / HomeIQ JSON | **92** |
| 3 | **ai-query-service** | `gpt-5-mini` | `OPENAI_MODEL` | Entity / room / action extraction from natural language | **88** |
| 4 | **ai-automation-service-new** (plan) | `gpt-5-mini` | `OPENAI_MODEL` | Intent planning & template selection | **85** |
| 5 | **proactive-agent-service** | `gpt-5-mini` | `OPENAI_MODEL` | Generates proactive automation suggestions | **78** |
| 6 | **device-intelligence-service** | `gpt-4o-mini` | via `OPENAI_API_KEY` | AI device / entity name suggestions | **55** |
| 7 | **Evaluation (LLM Judge)** | `gpt-4o-mini` | constructor param | Eval scoring for QA (dev-only) | **45** |

### Config file locations

| Service | Config File | Line |
|---------|-------------|------|
| ha-ai-agent-service | `domains/automation-core/ha-ai-agent-service/src/config.py` | ~81 |
| ai-automation-service-new | `domains/automation-core/ai-automation-service-new/src/config.py` | ~26–28 |
| ai-query-service | `domains/automation-core/ai-query-service/src/config.py` | ~28 |
| proactive-agent-service | `domains/energy-analytics/proactive-agent-service/src/config.py` | ~59 |
| device-intelligence-service | `domains/ml-engine/device-intelligence-service/src/services/name_enhancement/ai_suggester.py` | ~36 |
| Evaluation | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/llm_judge.py` | ~92 |

### Docker-compose defaults (runtime authority)

```yaml
# docker-compose.yml
OPENAI_MODEL=${OPENAI_MODEL:-gpt-5.2-codex}     # ha-ai-agent-service (line ~1116)
OPENAI_MODEL=${OPENAI_MODEL:-gpt-5-mini}        # proactive-agent-service (line ~1168)
OPENAI_MODEL=${OPENAI_MODEL:-gpt-5-mini}        # ai-automation-service-new (line ~1639)
OPENAI_YAML_MODEL=${OPENAI_YAML_MODEL:-gpt-5.2-codex}  # ai-automation-service-new (line ~1640)
```

---

## 2. Local Embedding / NLP (OpenVINO Service)

| Rank | Model ID | Type | Purpose | Value |
|------|----------|------|---------|-------|
| 8 | `BAAI/bge-large-en-v1.5` | Embedding (1024-dim) | Semantic search, RAG, pattern similarity | **65** |
| 9 | `google/flan-t5-small` | Seq2seq classifier | Pattern category & priority classification | **58** |
| 10 | `BAAI/bge-reranker-base` | Cross-encoder | Re-rank retrieval candidates | **52** |

All 3 run 100% local on CPU. ~485 MB combined (INT8 optimized).
INT8 variant: `OpenVINO/bge-reranker-base-int8-ov` (~280 MB).

**Config:** `domains/ml-engine/openvino-service/src/models/openvino_manager.py`

---

## 3. Non-Model AI Components

| Rank | Component | Approach | Purpose | Value |
|------|-----------|----------|---------|-------|
| 11 | **RAGContextService** | Keyword intent detection + static corpus files | Injects domain context (8 domains) into agent prompt | **60** |
| 12 | **RAG Service** (HTTP) | Calls openvino-service for embeddings | Semantic store / retrieve API (no major consumer yet) | **40** |

---

## 4. Predictive ML Models

| Rank | Service | Model(s) | Framework | Purpose | Value |
|------|---------|----------|-----------|---------|-------|
| 13 | **energy-forecasting** | N-HiTS (default), TFT, Prophet, ARIMA, Naive | Darts `>=0.40.0,<0.41.0` | Energy consumption forecasting | **62** |
| 14 | **device-intelligence** | RandomForest (default), LightGBM, TabPFN v2.5 | scikit-learn, lightgbm, tabpfn | Device failure prediction (nightly training 2 AM) | **55** |
| 15 | **rule-recommendation-ml** | ALS collaborative filtering (64 factors, 50 iter) | implicit `>=0.7.0` | Automation rule recommendations | **55** |
| 16 | **ml-service** | KMeans, DBSCAN, Isolation Forest | scikit-learn `>=1.5.0` | Clustering & anomaly detection | **50** |
| 17 | **activity-recognition** | Custom LSTM (2-layer, 64-unit, 10 classes) → ONNX | PyTorch → onnxruntime | Household activity classification (not yet wired into agent) | **42** |

### ML config details

| Service | Config | Key Settings |
|---------|--------|-------------|
| energy-forecasting | `domains/energy-analytics/energy-forecasting/src/models/energy_forecaster.py` | `model_type` param; input_chunk=168, output_chunk=48 |
| device-intelligence | `domains/ml-engine/device-intelligence-service/src/config.py` | `ML_FAILURE_MODEL` (randomforest/lightgbm/tabpfn), `ML_TRAINING_SCHEDULE=0 2 * * *` |
| rule-recommendation-ml | `domains/blueprints/rule-recommendation-ml/src/models/rule_recommender.py` | 64 factors, 50 iterations, regularization=0.01 |
| activity-recognition | `domains/device-management/activity-recognition/src/models/activity_classifier.py` | 5 input features, 64 hidden, 2 LSTM layers, dropout=0.2, ONNX opset 14 |

---

## 5. Optional / Alternative Models (Available but Not Default)

| # | Model | Service | Activation | Purpose |
|---|-------|---------|------------|---------|
| 18 | `llama3.2:3b` (Ollama) | device-intelligence-service | `ENABLE_LOCAL_LLM=true` | Local LLM fallback for device naming |
| 19 | `claude-sonnet-4-5-20250929` | shared evaluation | Select Anthropic provider | Alternative LLM judge |
| 20 | Fine-tuned `ft:gpt-4o-mini-*` | ai-automation-service-new | Set `OPENAI_FINE_TUNED_MODEL` | Custom HA commands (via nlp-fine-tuning service) |

### Fine-tuning base models (nlp-fine-tuning service)

| Base Model | Version ID | Purpose |
|------------|-----------|---------|
| gpt-4o-mini | `gpt-4o-mini-2024-07-18` | Cost-optimized fine-tuning |
| gpt-4o | `gpt-4o-2024-08-06` | High-quality fine-tuning |
| gpt-3.5-turbo | `gpt-3.5-turbo-0125` | Legacy option |

Also supports local PEFT via `domains/ml-engine/nlp-fine-tuning/src/training/fine_tune_peft.py`.

---

## 6. SDK & Library Versions — Status After Feb 22 Upgrades

| Library | Previous | Updated To | Status | Files Changed |
|---------|----------|-----------|--------|---------------|
| `openai` (ha-ai-agent) | `>=1.54.0,<2.0.0` | **`>=2.21.0,<3.0.0`** | DONE | `domains/automation-core/ha-ai-agent-service/requirements.txt` |
| `openai` (ai-automation) | `>=1.54.0,<2.0.0` | **`>=2.21.0,<3.0.0`** | DONE | `domains/automation-core/ai-automation-service-new/requirements.txt` |
| `openai` (ai-query) | `>=1.0.0` | **`>=2.21.0,<3.0.0`** | DONE | `domains/automation-core/ai-query-service/requirements.txt` |
| `openai` (proactive-agent) | `>=1.54.0,<2.0.0` | **`>=2.21.0,<3.0.0`** | DONE | `domains/energy-analytics/proactive-agent-service/requirements.txt` |
| `openai` (nlp-fine-tuning) | `>=1.0.0` | **`>=2.21.0,<3.0.0`** | DONE | `domains/ml-engine/nlp-fine-tuning/requirements.txt` |
| `darts` (energy-forecasting) | `>=0.30.0` | **`>=0.40.0,<0.41.0`** | DONE | `domains/energy-analytics/energy-forecasting/requirements.txt` |
| `onnxruntime` (activity-rec) | `>=1.19.0` | **`>=1.20.0,<2.0.0`** | DONE | `domains/device-management/activity-recognition/requirements.txt` |
| `onnxruntime` (rule-rec-ml) | `>=1.19.0` | **`>=1.20.0,<2.0.0`** | DONE | `domains/blueprints/rule-recommendation-ml/requirements.txt` |
| `scikit-learn` (rule-rec-ml) | `>=1.4.0` | **`>=1.5.0,<1.6.0`** | DONE | `domains/blueprints/rule-recommendation-ml/requirements.txt` |
| `torch` (openvino-service) | `>=2.4.0,<3.0.0` | **`>=2.5.0,<3.0.0`** | DONE | `domains/ml-engine/openvino-service/requirements.txt` |
| `anthropic` (eval datasets) | `==0.79.0` | `>=0.39.x` | TODO | `services/tests/datasets/home-assistant-datasets/requirements_dev.txt` |
| `sentence-transformers` (openvino) | `==3.3.1` | Keep 3.3.x or plan 5.x | DEFERRED | Needs regression testing before upgrade |
| `transformers` (openvino) | `==4.46.1` | Keep 4.46.x | DEFERRED | Stable; 5.x available but breaking |

---

## 7. Recommendations — Execution Status

### 7.1 Model changes

| Priority | Change | From | To | Status | Notes |
|----------|--------|------|----|--------|-------|
| **High** | ha-ai-agent default model | `gpt-4.1` | `gpt-5.2-codex` | **DONE** | Updated `config.py` + `docker-compose.yml` |
| **Medium** | LLM Judge model | `gpt-4o-mini` | `gpt-5-mini` | TODO | Evaluate cost/consistency trade-off |
| **Low** | Embedding model | `bge-large-en-v1.5` | `bge-m3` | DEFERRED | Only needed for multilingual support |
| **Low** | Classifier model | `flan-t5-small` | `flan-t5-small-for-classification` | DEFERRED | Marginal gain; not prioritized |

### 7.2 SDK upgrades

| Priority | Change | Status |
|----------|--------|--------|
| **High** | OpenAI SDK `1.x → 2.21.0+` (5 services) | **DONE** — All 5 requirements.txt files updated |
| **Medium** | Darts `0.30 → 0.40` (energy-forecasting) | **DONE** |
| **Low** | onnxruntime `1.19 → 1.20` (2 services) | **DONE** |
| **Low** | scikit-learn `1.4 → 1.5` (rule-recommendation-ml) | **DONE** |
| **Low** | torch `2.4 → 2.5` (openvino-service) | **DONE** |

### 7.3 Integration gaps to close

| Gap | Current State | Action | Value Unlock | Status |
|-----|--------------|--------|-------------|--------|
| Activity recognition | LSTM model works, no consumers | Wire into ha-ai-agent or proactive-agent | Context-aware automations (42 → 70+) | TODO |
| RAG Service (HTTP) | API works, no consumers | Connect to ha-ai-agent for semantic retrieval | Better context quality (40 → 65+) | TODO |
| Fine-tuned models | Infrastructure exists | Train on real HA command data, set `OPENAI_FINE_TUNED_MODEL` | Improved automation accuracy | TODO |

---

## 8. Summary by Value Tier

| Tier | Components | Count |
|------|-----------|-------|
| **90–100** (Core product) | HA AI Agent, AI Automation YAML | 2 |
| **70–89** (Critical flows) | AI Query, AI Automation plan, Proactive Agent | 3 |
| **50–69** (Quality / features) | Embeddings, Energy forecasting, RAGContext, Classifier, Device names, Rule rec, Reranker, ML Service | 8 |
| **40–49** (Backend / niche) | Evaluation Judge, Activity recognition, RAG HTTP | 3 |
| **Optional** | Ollama, Claude eval, Fine-tuned models | 3 |
| **Total** | | **19 capabilities, ~15 distinct models** |

---

## 9. Changelog

### Feb 22, 2026 — Recommendations Executed

**10 of 13 library/model upgrades completed:**

| # | Change | Files Modified |
|---|--------|---------------|
| 1 | OpenAI SDK `1.x → 2.21.0+` | 5 requirements.txt (ha-ai-agent, ai-automation, ai-query, proactive-agent, nlp-fine-tuning) |
| 2 | ha-ai-agent model `gpt-4.1 → gpt-5.2-codex` | `domains/automation-core/ha-ai-agent-service/src/config.py`, `docker-compose.yml` |
| 3 | Darts `0.30 → 0.40` | `domains/energy-analytics/energy-forecasting/requirements.txt` |
| 4 | onnxruntime `1.19 → 1.20` | `domains/device-management/activity-recognition/requirements.txt`, `domains/blueprints/rule-recommendation-ml/requirements.txt` |
| 5 | scikit-learn `1.4 → 1.5` | `domains/blueprints/rule-recommendation-ml/requirements.txt` |
| 6 | torch `2.4 → 2.5` | `domains/ml-engine/openvino-service/requirements.txt` |

**3 items deferred:**
- `anthropic` SDK upgrade (eval datasets) — TODO
- `sentence-transformers` 5.x upgrade — needs regression testing
- `transformers` 5.x upgrade — breaking changes, not yet needed

**3 integration gaps remain (future work):**
- Activity recognition → agent wiring
- RAG HTTP → agent wiring
- Fine-tuned model training

---

## References

- Model selection rationale: `implementation/OPENAI_MODEL_RESEARCH_2026.md`
- Reusable pattern framework: `libs/homeiq-patterns/README.md`
- Service architecture: `services/SERVICES_RANKED_BY_IMPORTANCE.md`
