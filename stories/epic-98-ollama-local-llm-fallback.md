# Epic 98: Local LLM Fallback via Ollama

**Priority:** P2 — Resilience (demoted from P1: defer until Epic 97 ships)
**Effort:** 1 week (5 stories, 19 points)
**Sprint:** 45
**Depends on:** Epic 97 (Claude Provider — LLMRouter and LLMResponse abstractions)
**Origin:** Sapphire Review — 2026 Research Recommendation #3

## Problem Statement

When OpenAI or Anthropic APIs go down, HomeIQ's automation pipeline is dead. No automation creation, no previews, no suggestions. Cloud API outages happen — OpenAI had 3 significant outages in 2025, each lasting 1–4 hours.

2026 local models are production-viable for focused tasks:
- **Qwen 3 7B**: Best small model for code/YAML generation (LM Arena #1 in small model category, Mar 2026)
- **Llama 3.3 8B**: Best all-around small model (Apache 2.0)
- **Phi-4-mini 3.8B**: Edge deployment on 4GB VRAM

Ollama provides an OpenAI-compatible API at `localhost:11434`, making integration minimal. HomeIQ already has a `CircuitBreaker` pattern in `homeiq-resilience` — the fallback is architecturally natural.

**Trade-off:** Local models produce lower-quality YAML than GPT-5.2 or Claude. But "degraded automation creation" beats "no automation creation." The YAML validation pipeline catches structural errors regardless of which model generated the YAML.

## Approach

1. Deploy Ollama as a Docker container with pre-pulled models
2. Add `OllamaProvider` using existing OpenAI-compatible API format
3. Wire into `LLMRouter` as a third-tier fallback (after cloud primary + cloud fallback)
4. Test YAML quality with local models and adjust prompting if needed
5. Document model recommendations for different hardware

---

## Story 98.1: Deploy Ollama in Docker Stack

**Points:** 3 | **Type:** Infrastructure
**Goal:** Ollama runs as a container with pre-pulled model, accessible to `ha-ai-agent-service`

### Tasks

- [ ] **98.1.1** Add Ollama to `domains/ml-engine/compose.yml`:
  ```yaml
  ollama:
    image: ollama/ollama:latest
    container_name: homeiq-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_models:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - homeiq-network

  volumes:
    ollama_models:
      driver: local
  ```
- [ ] **98.1.2** Create `scripts/ollama-setup.sh` to pre-pull recommended models:
  ```bash
  #!/bin/bash
  # Pre-pull models for HomeIQ automation generation
  echo "Pulling Qwen 3 7B (recommended for YAML generation)..."
  docker exec homeiq-ollama ollama pull qwen3:7b

  echo "Pulling Llama 3.3 8B (general fallback)..."
  docker exec homeiq-ollama ollama pull llama3.3:8b

  echo "Models ready."
  docker exec homeiq-ollama ollama list
  ```
- [ ] **98.1.3** Add CPU-only fallback config (no GPU):
  ```yaml
  # If no GPU available, remove deploy.resources section
  # Models will run on CPU (slower but functional)
  ```
- [ ] **98.1.4** Update `start-stack.sh` and `domain.sh` to include Ollama in ml-engine domain
- [ ] **98.1.5** Document port assignment in TECH_STACK.md (port 11434)
- [ ] **98.1.6** Add health check to health-dashboard

### Acceptance Criteria

- [ ] Ollama container starts with `domain.sh start ml-engine`
- [ ] `curl http://localhost:11434/api/tags` returns model list
- [ ] At least one model is pre-pulled and ready
- [ ] GPU acceleration works if NVIDIA GPU available; CPU fallback works otherwise
- [ ] Health dashboard shows Ollama status

---

## Story 98.2: Ollama LLM Provider

**Points:** 5 | **Type:** Feature
**Goal:** `OllamaProvider` uses Ollama's OpenAI-compatible API with the same `LLMResponse` interface

### Tasks

- [ ] **98.2.1** Add settings to `config.py`:
  ```python
  ollama_url: str = "http://ollama:11434"  # Docker network name
  ollama_model: str = "qwen3:7b"
  ollama_enabled: bool = True
  ollama_timeout: int = 120  # Local models are slower
  ```
- [ ] **98.2.2** Create `src/clients/ollama_client.py`:
  ```python
  class OllamaLLMClient:
      """Local LLM client via Ollama's OpenAI-compatible API."""

      def __init__(self, base_url: str, model: str, timeout: int = 120):
          # Ollama exposes /v1/chat/completions (OpenAI-compatible)
          self.client = httpx.AsyncClient(
              base_url=f"{base_url}/v1",
              timeout=timeout,
          )
          self.model = model

      async def chat_completion(
          self,
          system_prompt: str,
          messages: list[dict],
          tools: list[dict] | None = None,
          max_tokens: int = 4096,
      ) -> LLMResponse:
          """Call Ollama via OpenAI-compatible endpoint."""
          payload = {
              "model": self.model,
              "messages": [
                  {"role": "system", "content": system_prompt},
                  *messages,
              ],
              "max_tokens": max_tokens,
              "temperature": 0.3,  # Lower temp for YAML accuracy
          }
          if tools:
              payload["tools"] = tools
          response = await self.client.post("/chat/completions", json=payload)
          ...
  ```
- [ ] **98.2.3** Handle Ollama-specific quirks:
  - Longer response times (30–120s vs 2–10s for cloud)
  - Tool calling may not be supported by all models — graceful fallback to JSON extraction
  - Streaming support for UI responsiveness during slow generation
- [ ] **98.2.4** Add model capability detection:
  ```python
  async def check_model_capabilities(self) -> dict:
      """Check what the loaded model supports."""
      return {
          "tool_calling": self._supports_tool_calling(),
          "json_mode": True,  # Most models support this
          "max_context": self._get_context_size(),
      }
  ```
- [ ] **98.2.5** Add unit tests with mocked Ollama API

### Acceptance Criteria

- [ ] Ollama chat completion returns `LLMResponse` matching cloud provider format
- [ ] Tool calling works (or gracefully falls back to JSON extraction)
- [ ] Timeout of 120s handles slow local generation
- [ ] Model capability detection reports supported features

---

## Story 98.3: Wire into LLMRouter as Third-Tier Fallback

**Points:** 3 | **Type:** Integration
**Goal:** Ollama activates automatically when both cloud providers are down

### Tasks

- [ ] **98.3.1** Update `LLMRouter` (from Epic 97) to support three tiers:
  ```python
  class LLMRouter:
      def __init__(self, settings: Settings):
          self.primary = self._create_client(settings.llm_provider, settings)
          self.fallback = self._create_client(settings.llm_fallback_provider, settings)
          self.local = OllamaLLMClient(...) if settings.ollama_enabled else None

          self.cloud_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
          self.fallback_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=120)

      async def chat_completion(self, **kwargs) -> LLMResponse:
          # Tier 1: Primary cloud provider
          try:
              return await self.cloud_breaker.call(self.primary.chat_completion, **kwargs)
          except (CircuitBreakerOpen, Exception) as e:
              logger.warning(f"Primary LLM failed: {e}")

          # Tier 2: Fallback cloud provider
          if self.fallback:
              try:
                  return await self.fallback_breaker.call(self.fallback.chat_completion, **kwargs)
              except (CircuitBreakerOpen, Exception) as e:
                  logger.warning(f"Fallback LLM failed: {e}")

          # Tier 3: Local Ollama
          if self.local:
              logger.warning("AI FALLBACK: Using local Ollama model")
              return await self._local_with_simplified_prompt(**kwargs)

          raise LLMUnavailableError("All LLM providers unavailable")
  ```
- [ ] **98.3.2** Simplify prompt for local models:
  ```python
  async def _local_with_simplified_prompt(self, **kwargs) -> LLMResponse:
      """
      Local models have smaller context windows (4K-8K).
      Trim the system prompt to essential sections only:
      - Core Identity (Section 1)
      - Mandatory Workflow (Section 2)
      - YAML Generation (Section 5)
      - Safety (Section 7)
      Skip: sports automations, detailed entity resolution, response formatting
      """
      ...
  ```
- [ ] **98.3.3** Add `X-LLM-Provider` response header so UI can show which provider generated the response
- [ ] **98.3.4** Add metrics: `homeiq_llm_provider_used{provider}` counter
- [ ] **98.3.5** Add unit tests: cloud down → fallback; both clouds down → Ollama; all down → error

### Acceptance Criteria

- [ ] Both cloud providers down → Ollama automatically activates
- [ ] Simplified prompt fits within local model context window (≤4K tokens)
- [ ] Response header shows which provider was used
- [ ] Metrics track provider usage distribution

---

## Story 98.4: Local Model YAML Quality Testing

**Points:** 5 | **Type:** Testing
**Goal:** Validate local models can generate acceptable HA automation YAML

### Tasks

- [ ] **98.4.1** Create `scripts/benchmark_local_models.py`:
  - Test 20 automation prompts against each local model
  - Score: YAML validity, entity resolution accuracy, trigger correctness
  - Compare: Qwen 3 7B vs Llama 3.3 8B vs Phi-4-mini 3.8B
- [ ] **98.4.2** Test with simplified prompt (Section 1 + 2 + 5 + 7 only)
- [ ] **98.4.3** Test categories:
  ```
  | Category                  | Count | Examples |
  |---------------------------|-------|---------|
  | Simple light automation   |   5   | "Turn on office lights at sunset" |
  | Motion-based automation   |   3   | "Lights on when motion in kitchen" |
  | Time-based automation     |   3   | "Set thermostat to 72°F at 6pm" |
  | Multi-action automation   |   3   | "At sunset, turn on lights and close blinds" |
  | Condition-based automation|   3   | "Turn on lights only if nobody home" |
  | Complex automation        |   3   | "Motion in office after sunset, lights on, off after 5 min no motion" |
  ```
- [ ] **98.4.4** Score results:
  ```
  | Model       | YAML Valid | Correct Entities | Correct Triggers | Avg Score |
  |-------------|-----------|------------------|-----------------|-----------|
  | Qwen 3 7B   |    ?/20   |      ?/20        |      ?/20       |    ?%     |
  | Llama 3.3   |    ?/20   |      ?/20        |      ?/20       |    ?%     |
  | Phi-4-mini  |    ?/20   |      ?/20        |      ?/20       |    ?%     |
  ```
- [ ] **98.4.5** If quality is too low (<70% valid YAML), add few-shot examples to the simplified prompt
- [ ] **98.4.6** Write results to `docs/LOCAL_MODEL_BENCHMARK.md`
- [ ] **98.4.7** Set recommended default model based on results

### Acceptance Criteria

- [ ] Best local model achieves ≥80% valid YAML on test set
- [ ] Simple automations (5/5) produce valid YAML
- [ ] Entity resolution works for entities in provided context
- [ ] Recommended model documented with hardware requirements

---

## Story 98.5: Degraded Mode UX

**Points:** 3 | **Type:** Enhancement
**Goal:** Users know when they're on local fallback and what limitations apply

### Tasks

- [ ] **98.5.1** Add `degraded_mode` flag to chat response:
  ```python
  class ChatResponse:
      ...
      provider: str          # "openai", "anthropic", "ollama"
      degraded_mode: bool    # True when using local fallback
      degraded_notice: str | None  # "Using local AI — responses may be simpler"
  ```
- [ ] **98.5.2** UI shows subtle banner when in degraded mode: "Local AI mode — cloud providers temporarily unavailable"
- [ ] **98.5.3** Simplify enhancement suggestions in degraded mode: skip `suggest_automation_enhancements` tool (local models struggle with open-ended generation)
- [ ] **98.5.4** Auto-retry cloud providers: when circuit breaker half-opens, try cloud first on next request
- [ ] **98.5.5** Add health endpoint detail: `/api/v1/health` shows provider status and degraded state

### Acceptance Criteria

- [ ] Chat response includes provider and degraded_mode flag
- [ ] UI shows degraded mode indicator (non-intrusive)
- [ ] Enhancement suggestions disabled in degraded mode
- [ ] Auto-recovery to cloud when providers come back online

---

## Model Recommendations (2026 Benchmarks)

| Model | Parameters | VRAM | Strengths | Weaknesses | Recommended For |
|-------|-----------|------|-----------|------------|----------------|
| **Qwen 3 7B** | 7B | 6GB | Best code/YAML generation, structured output | Weaker at natural language | **Default for HomeIQ** |
| Llama 3.3 8B | 8B | 8GB | Best all-around, Apache 2.0 | Slightly worse at YAML | General fallback |
| Phi-4-mini 3.8B | 3.8B | 4GB | Runs on edge hardware, fast | Lower quality on complex tasks | RPi / NUC deployment |
| Gemma 3 4B | 4B | 4GB | Good instruction following | Limited tool calling | Alternative to Phi-4 |

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Local model YAML quality | Validation pipeline catches errors; few-shot examples in prompt |
| GPU memory not available | CPU-only mode works (slower, 30–120s response time) |
| Context window too small | Simplified prompt (4K tokens) vs full prompt (10K–30K tokens) |
| Tool calling not supported | JSON extraction fallback for models without tool calling |
| Ollama container memory usage | Resource limits in Docker Compose; Qwen 3 7B uses ~6GB |
| Model download size | Pre-pull in setup script; Qwen 3 7B is ~4GB download |

## Architecture (3-Tier Fallback)

```
Request → LLMRouter
            │
            ├── Tier 1: OpenAI GPT-5.2 (primary)
            │     └── CircuitBreaker (3 fails → open)
            │
            ├── Tier 2: Claude Sonnet (fallback)
            │     └── CircuitBreaker (3 fails → open)
            │
            └── Tier 3: Ollama Qwen 3 7B (local)
                  └── Simplified prompt, no enhancements
                  └── Always available (local, no API key)

Recovery: Circuit breakers half-open → auto-retry cloud on next request
```
