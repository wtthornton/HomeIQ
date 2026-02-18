# LLM and ML Models Review — Versions and Recommendations

**Generated:** February 18, 2026  
**Scope:** All LLM (OpenAI, Anthropic, Ollama), embedding/rerank/classifier models (OpenVINO service), activity recognition (ONNX), energy forecasting (Darts), rule-recommendation-ml, evaluation LLM-as-Judge, and related SDK/libraries.

---

## 1. LLM usage summary

| Service / Component | Provider | Model (current) | Config / env |
|--------------------|----------|-----------------|--------------|
| **ha-ai-agent-service** | OpenAI | `gpt-5-mini` (default in config) | `OPENAI_MODEL` |
| **ai-automation-service-new** | OpenAI | Plan/chat: `gpt-4o-mini`; YAML: `gpt-5.2-codex` | `openai_model`, `openai_yaml_model` |
| **ai-query-service** | OpenAI | `gpt-5-mini` | `openai_model` |
| **proactive-agent-service** | OpenAI | `gpt-5-mini` | `openai_model` |
| **device-intelligence-service** | OpenAI (+ optional Ollama) | `gpt-4o-mini`; local: `llama3.2:3b` | `OPENAI_API_KEY`, `ENABLE_LOCAL_LLM` |
| **Evaluation (LLM Judge)** | OpenAI or Anthropic | Default: `gpt-4o-mini`; Anthropic: `claude-sonnet-4-5-20250929` | Provider constructor |
| **home-assistant-datasets (eval)** | OpenAI, Anthropic | Pinned in requirements_dev.txt | — |

See [implementation/OPENAI_MODEL_RESEARCH_2026.md](OPENAI_MODEL_RESEARCH_2026.md) for cost/quality rationale and recommended model per service.

---

## 2. LLM — version and model recommendations

### 2.1 OpenAI Python SDK

| Location | Current | Recommended | Notes |
|----------|---------|-------------|--------|
| ai-automation-service-new | openai>=1.54.0,<2.0.0 | **openai>=2.21.0** (or >=2.x,<3.0) | Latest stable 2.21.0; supports GPT-5.2, Responses API, reasoning params. |
| ha-ai-agent-service | openai>=1.54.0,<2.0.0 | **openai>=2.21.0** | Same. |
| proactive-agent-service | openai>=1.54.0,<2.0.0 | **openai>=2.21.0** | Same. |
| ai-query-service | openai>=1.0.0 | **openai>=2.21.0** | Align with other services. |
| device-intelligence-service | (inherits) | **openai>=2.21.0** | If it uses OpenAI SDK directly. |
| shared/patterns/evaluation | (lazy import openai) | Ensure **openai>=2.x** where evaluation runs | LLMJudge uses AsyncOpenAI. |
| tests/datasets/home-assistant-datasets | openai==2.20.0, anthropic==0.79.0 | **openai>=2.21.0**, **anthropic>=0.39.x** (latest stable) | Unpin exact 2.20.0 for patches. |

**Action:** Upgrade all `openai` pins to `>=2.21.0,<3.0.0` (or equivalent 2.x range). Test gpt-5-mini / gpt-5.2-codex with the new SDK (reasoning_effort, temperature behavior).

### 2.2 Model defaults (align with OPENAI_MODEL_RESEARCH_2026.md)

| Service | Current default | Recommended | Rationale |
|---------|-----------------|-------------|-----------|
| ha-ai-agent-service | gpt-5-mini | **gpt-5.2-codex** (or gpt-5.2) | Best for agentic, code/YAML-heavy chat; research recommends 5.2-codex. |
| ai-automation-service-new (plan) | gpt-4o-mini | **gpt-5-mini** | Better intent/template quality. |
| ai-automation-service-new (YAML) | gpt-5.2-codex | Keep | Already optimal. |
| ai-query-service | gpt-5-mini | Keep | Already recommended. |
| proactive-agent-service | gpt-5-mini | Keep | Already recommended. |
| device-intelligence-service | gpt-4o-mini | **gpt-4o-mini** or gpt-5-mini | Keep 4o-mini for cost; 5-mini if name quality is priority. |
| LLM Judge (evaluation) | gpt-4o-mini | **gpt-4o-mini** or gpt-5-mini | 5-mini for better judge consistency if cost acceptable. |

### 2.3 Alternative / local LLMs

- **Ollama (device-intelligence-service):** Already supported; model `llama3.2:3b`. Consider **llama3.3** or **llama3.2:1b** for lower resource, or **mistral** / **phi3** for quality/size trade-off.
- **Evaluation:** Anthropic provider exists (`claude-sonnet-4-5-20250929`). Update to a current Claude model ID if needed (e.g. latest claude-3.5-sonnet or claude-3-opus per [Anthropic docs](https://docs.anthropic.com)).
- **Other backends:** No Gemini, Cohere, or Azure OpenAI in codebase; add via provider abstraction in `shared/patterns/evaluation` if required.

---

## 3. ML / embedding / classification (OpenVINO service)

### 3.1 Models in use

| Role | Model ID | Dimension / type | Notes |
|------|----------|------------------|--------|
| Embeddings | **BAAI/bge-large-en-v1.5** | 1024-dim | sentence-transformers; Epic 47. |
| Reranker | **BAAI/bge-reranker-base** | Cross-encoder | Rerank search candidates. |
| Classifier | **google/flan-t5-small** | Gen (category + priority) | Pattern category/priority. |

### 3.2 Library versions (openvino-service)

| Package | Current | Recommended | Notes |
|---------|---------|-------------|--------|
| sentence-transformers | ==3.3.1 | **>=3.3.1,<4.0** or **>=5.2.0** (major upgrade) | 5.2.x is current; 3.x is still valid. Moving to 5.x needs compatibility testing (API may differ). |
| transformers | ==4.46.1 | **>=4.46.1,<5.0** or **>=5.2.0** with sentence-transformers 5.x | 5.2.0 is latest; stay on 4.x for minimal change. |
| torch | >=2.4.0,<3.0.0 | **>=2.5.0,<3.0.0** (align with activity-recognition) | Keep CPU-only index. |

**Recommendation:** For production stability, keep sentence-transformers 3.3.x and transformers 4.46.x; optionally bump to latest 4.x patch. Plan a separate upgrade to sentence-transformers 5.x + transformers 5.x with full regression tests.

### 3.3 Alternative models

| Current | Alternative | Use case |
|---------|------------|----------|
| **BAAI/bge-large-en-v1.5** | **BAAI/bge-m3** | Multilingual, longer context (e.g. 8192 tokens); requires auth for some variants. |
| **BAAI/bge-large-en-v1.5** | **BAAI/bge-base-en-v1.5** or **bge-small-en-v1.5** | Lower memory/latency. |
| **BAAI/bge-reranker-base** | **BAAI/bge-reranker-large** | Higher rerank quality at higher cost. |
| **google/flan-t5-small** | **knowledgator/flan-t5-small-for-classification** | Classification-specific fine-tune. |
| **google/flan-t5-small** | **google/t5-efficient-small-dm768** | More efficient small T5. |

---

## 4. Activity recognition (ONNX)

| Item | Current | Recommended |
|------|---------|-------------|
| Runtime | onnxruntime>=1.19.0 | **onnxruntime>=1.20.x** (latest stable 1.x) |
| Model | Custom LSTM exported to ONNX (`activity_lstm.onnx`) | No change unless you retrain; keep ONNX opset and I/O contract stable. |
| Training stack | torch>=2.5.0 | **torch>=2.5.0** (keep; align with other services). |

---

## 5. Energy forecasting (Darts)

| Item | Current | Recommended |
|------|---------|-------------|
| darts | >=0.30.0 | **>=0.40.0,<0.41.0** (0.40.0 stable Dec 2025; Chronos2Model, config system). |
| Models in use | N-HiTS, TFT, Prophet, ARIMA, naive | Keep; consider Chronos2Model (Darts 0.40+) for zero-shot if needed. |
| torch / pytorch-lightning | >=2.5.0, >=2.2.0 | Keep. |

---

## 6. Rule-recommendation-ml

| Item | Current | Recommended |
|------|---------|-------------|
| onnxruntime | >=1.19.0 | **>=1.20.x** (align with activity-recognition). |
| implicit | >=0.7.0 | Keep; lightfm disabled (Python 3.12 compat). |
| scikit-learn | >=1.4.0 | **>=1.5.0,<1.6.0** (align with ml-service). |

---

## 7. ML service (scikit-learn)

| Item | Current | Recommended |
|------|---------|-------------|
| scikit-learn | >=1.5.0,<1.6.0 | Keep. |
| numpy | >=1.26.0,<1.27.0 | Keep. |

No model IDs in code (service uses sklearn for in-process ML); version alignment only.

---

## 8. RAG service

- No direct LLM or embedding dependencies in its own requirements; it calls **openvino-service** for embeddings.
- Keep RAG’s FastAPI/httpx stack aligned with `requirements-base.txt`; no separate model/SDK recommendations.

---

## 9. NLP fine-tuning and model-prep

| Service | Packages | Recommended |
|---------|----------|-------------|
| nlp-fine-tuning | transformers>=4.45.0, torch>=2.5.0, openai>=1.0.0 | **transformers>=4.46.1**, **openai>=2.21.0**. |
| model-prep | transformers>=4.46.0, sentence-transformers>=3.3.0, torch>=2.5.0 | **sentence-transformers>=3.3.1**, **transformers>=4.46.1** (match openvino-service). |

---

## 10. Summary table — production-stable upgrades

| Area | Current | Upgrade |
|------|---------|--------|
| **OpenAI SDK** (all services using OpenAI) | 1.54.x or 1.0 / 2.20 | **openai>=2.21.0,<3.0.0** |
| **Anthropic** (eval datasets) | 0.79.0 | **anthropic>=0.39.x** (latest stable) |
| **ha-ai-agent default model** | gpt-5-mini | **gpt-5.2-codex** (per research doc) |
| **ai-automation-service-new plan model** | gpt-4o-mini | **gpt-5-mini** |
| **sentence-transformers** (openvino) | 3.3.1 | Keep 3.3.x or plan 5.x upgrade |
| **transformers** (openvino) | 4.46.1 | Keep 4.46.x or latest 4.x patch |
| **darts** (energy-forecasting) | >=0.30.0 | **>=0.40.0,<0.41.0** |
| **onnxruntime** (activity, rule-recommendation-ml) | >=1.19.0 | **>=1.20.x** |
| **Embedding model** (optional) | bge-large-en-v1.5 | **bge-m3** for multilingual/long context |
| **Classifier** (optional) | flan-t5-small | **flan-t5-small-for-classification** for classification-only |

---

## 11. Files to touch

- **LLM / SDK:**  
  - `services/ai-automation-service-new/requirements.txt`  
  - `services/ha-ai-agent-service/requirements.txt`  
  - `services/proactive-agent-service/requirements.txt`  
  - `services/ai-query-service/requirements.txt`  
  - `services/device-intelligence-service/requirements*.txt` (if OpenAI used)  
  - `services/tests/datasets/home-assistant-datasets/requirements_dev.txt`, `requirements_eval.txt`
- **Model defaults:**  
  - `services/ha-ai-agent-service/src/config.py` (openai_model default)  
  - `services/ai-automation-service-new/src/config.py` (openai_model default)
- **ML / embedding:**  
  - `services/openvino-service/requirements.txt` (sentence-transformers, transformers, torch)  
  - `services/activity-recognition/requirements.txt` (onnxruntime)  
  - `services/energy-forecasting/requirements.txt` (darts)  
  - `services/rule-recommendation-ml/requirements.txt` (onnxruntime, scikit-learn)  
  - `services/nlp-fine-tuning/requirements.txt`  
  - `services/model-prep/requirements.txt`
- **Evaluation:**  
  - `shared/patterns/evaluation/llm_judge.py` (ensure openai/anthropic versions where used).

After changes: run service health checks, integration tests that call OpenAI/Anthropic, embedding/rerank/classify tests for openvino-service, and activity/energy/rule-recommendation pipelines.
