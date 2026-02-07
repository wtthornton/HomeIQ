# NLP Fine-Tuning Service - Deep Code Review

**Service**: `services/nlp-fine-tuning/`
**Tier**: 7 (Specialized Services)
**Review Date**: 2026-02-06
**Reviewer**: Deep Review Agent

---

## Service Overview

The NLP Fine-Tuning service provides tooling for fine-tuning language models on Home Assistant command understanding. It supports two training approaches:

1. **PEFT/LoRA (Local)**: Parameter-efficient fine-tuning using quantized models on consumer hardware
2. **OpenAI Fine-Tuning (Cloud)**: Using OpenAI's API for production model customization

The service includes a data loader for the Home Assistant Requests Hugging Face dataset, training orchestration for both approaches, and an evaluation module with intent classification, entity extraction, exact match, and BLEU metrics.

**Files Reviewed**:
- `pyproject.toml` - Project configuration
- `requirements.txt` - Dependencies
- `README.md` - Documentation
- `src/__init__.py` - Package init
- `src/data/__init__.py` - Data module init
- `src/data/ha_requests_loader.py` (456 lines) - Dataset loader
- `src/training/__init__.py` - Training module init
- `src/training/fine_tune_openai.py` (460 lines) - OpenAI fine-tuning
- `src/training/fine_tune_peft.py` (425 lines) - PEFT/LoRA fine-tuning
- `src/evaluation/__init__.py` - Evaluation module init
- `src/evaluation/metrics.py` (350 lines) - Evaluation metrics

---

## Findings

### CRITICAL Severity

#### C1. No Dockerfile or Docker Compose Configuration
**File**: (missing)
**Impact**: Service cannot be deployed as a container within the HomeIQ microservice architecture.

All other HomeIQ services follow a containerized deployment pattern. This service has no `Dockerfile`, no `docker-compose.yml`, no `.dockerignore`, and no health check endpoint. It is purely a Python library/CLI tool with no service entry point.

**Recommendation**: If this is intentional (offline tooling only), document that clearly. If it should be deployable, create:
- A `Dockerfile` with multi-stage build (build deps vs runtime)
- A simple Flask/FastAPI wrapper for triggering fine-tuning jobs via API
- A `/health` endpoint consistent with other HomeIQ services

---

#### C2. No Tests Whatsoever
**File**: (missing `tests/` directory)
**Impact**: Zero test coverage despite `pyproject.toml` configuring pytest with `testpaths = ["tests"]`.

The project declares dev dependencies for `pytest`, `pytest-asyncio`, `pytest-cov`, but no tests exist. The evaluation metrics, data loading, and format conversion logic are all untested.

**Recommendation**: Create a `tests/` directory with at minimum:
```python
# tests/test_ha_requests_loader.py
def test_find_column_matches_candidates():
    loader = HARequestsLoader()
    assert loader._find_column(["user_request", "response"], ["request"]) == "user_request"

def test_find_column_returns_none_for_no_match():
    loader = HARequestsLoader()
    assert loader._find_column(["foo", "bar"], ["request"]) is None

def test_extract_domain_from_dict():
    loader = HARequestsLoader()
    assert loader._extract_domain('{"domain": "light"}') == "light"

def test_extract_domain_handles_invalid_json():
    loader = HARequestsLoader()
    assert loader._extract_domain("not json") == ""

# tests/test_metrics.py
def test_intent_classification_accuracy():
    evaluator = NLPEvaluator()
    results = evaluator.evaluate_intent_classification(
        ["HassTurnOn", "HassTurnOff"], ["HassTurnOn", "HassTurnOff"]
    )
    assert results["accuracy"] == 1.0

def test_entity_extraction_f1():
    evaluator = NLPEvaluator()
    results = evaluator.evaluate_entity_extraction(
        [{"domain": "light"}], [{"domain": "light"}]
    )
    assert results["f1"] == 1.0

# tests/test_fine_tune_openai.py
def test_validate_training_data_valid():
    tuner = OpenAIFineTuner.__new__(OpenAIFineTuner)  # skip __init__
    examples = [{"messages": [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]}] * 10
    is_valid, errors = tuner.validate_training_data(examples)
    assert is_valid

def test_validate_training_data_too_few():
    tuner = OpenAIFineTuner.__new__(OpenAIFineTuner)
    is_valid, errors = tuner.validate_training_data([{"messages": []}])
    assert not is_valid
```

---

#### C3. OpenAI API Key Potentially Exposed in Logs
**File**: `src/training/fine_tune_openai.py:60-63`
**Impact**: If API key is passed as argument and an error occurs during initialization, stack traces could expose the key.

```python
self.client = OpenAI(
    api_key=api_key or os.getenv("OPENAI_API_KEY"),
    organization=organization or os.getenv("OPENAI_ORGANIZATION"),
)
```

The `api_key` parameter value will appear in tracebacks if `OpenAI()` raises. There is also no validation that the key is actually provided -- the OpenAI client will fail later with a confusing error.

**Recommendation**: Validate early and avoid passing secrets through parameters that may be logged:
```python
resolved_key = api_key or os.getenv("OPENAI_API_KEY")
if not resolved_key:
    raise ValueError(
        "OpenAI API key is required. Set OPENAI_API_KEY environment variable "
        "or pass api_key parameter."
    )
self.client = OpenAI(api_key=resolved_key, organization=organization or os.getenv("OPENAI_ORGANIZATION"))
```

---

### HIGH Severity

#### H1. `trust_remote_code=True` Without User Consent or Sandboxing
**File**: `src/training/fine_tune_peft.py:96-98` and `src/training/fine_tune_peft.py:105-111`
**Impact**: Arbitrary code execution risk when loading models from Hugging Face.

```python
self.tokenizer = AutoTokenizer.from_pretrained(
    model_name,
    trust_remote_code=True,  # line 97
)

self.model = AutoModelForCausalLM.from_pretrained(
    model_name,
    ...
    trust_remote_code=True,  # line 109
)
```

`trust_remote_code=True` allows the Hugging Face model repo to execute arbitrary Python code on the host machine. Since the `base_model` parameter can be any user-provided string (not just keys from `SUPPORTED_MODELS`), a malicious model name could lead to remote code execution.

**Recommendation**: Only enable `trust_remote_code` for known models or add an explicit opt-in parameter:
```python
# Only trust remote code for verified models
needs_trust = any(name in model_name.lower() for name in ["phi", "gemma"])

self.tokenizer = AutoTokenizer.from_pretrained(
    model_name,
    trust_remote_code=needs_trust,
)
```

---

#### H2. Temporary File Not Cleaned Up on Crash During Upload
**File**: `src/training/fine_tune_openai.py:197-222`
**Impact**: Training data (potentially sensitive smart home commands) left on disk.

```python
with tempfile.NamedTemporaryFile(
    mode="w",
    suffix=".jsonl",
    delete=False,  # line 200
    encoding="utf-8",
) as f:
    for example in examples:
        f.write(json.dumps(example) + "\n")
    temp_path = f.name

try:
    # Upload file
    ...
finally:
    Path(temp_path).unlink(missing_ok=True)
```

While the `finally` block handles cleanup, `delete=False` means that if the process is killed (SIGKILL, OOM, power loss) between file creation and the `finally` block, the temp file persists. The training data may contain sensitive smart home configurations.

**Recommendation**: Use `tempfile.TemporaryDirectory()` or write to a known managed directory with periodic cleanup, or use `delete_on_close=False` (Python 3.12+) with a context manager.

---

#### H3. Duplicate Dependency Specifications Between pyproject.toml and requirements.txt
**File**: `pyproject.toml:24-37` and `requirements.txt:1-29`
**Impact**: Dependency drift -- `bitsandbytes>=0.43.0` and `tqdm>=4.66.0` appear only in `requirements.txt`, not in `pyproject.toml`.

| Package | pyproject.toml | requirements.txt |
|---|---|---|
| `bitsandbytes` | Missing | `>=0.43.0` |
| `tqdm` | Missing | `>=4.66.0` |

This means installing via `pip install .` (using pyproject.toml) will miss `bitsandbytes` and `tqdm`, but `pip install -r requirements.txt` will include them. The PEFT fine-tuner imports `BitsAndBytesConfig` from transformers but relies on `bitsandbytes` being installed at runtime.

**Recommendation**: Consolidate to a single source of truth. Either:
- Add `bitsandbytes` and `tqdm` to `pyproject.toml` dependencies
- Or remove `requirements.txt` and use only `pyproject.toml`

```toml
# In pyproject.toml [project] dependencies
"bitsandbytes>=0.43.0",
"tqdm>=4.66.0",
```

---

#### H4. `evaluate_domain_accuracy` Has Incorrect Length Comparison
**File**: `src/evaluation/metrics.py:262`
**Impact**: Chained `!=` comparison does not validate all three lists have the same length.

```python
if len(predictions) != len(ground_truth) != len(domains):
    raise ValueError("All inputs must have same length")
```

This is a chained comparison: `a != b != c` is equivalent to `(a != b) and (b != c)`. It will NOT catch the case where `predictions` and `domains` have the same length but `ground_truth` is different. For example, if `len(predictions) == 5`, `len(ground_truth) == 3`, `len(domains) == 5`, then `5 != 3` is True and `3 != 5` is True, so it does raise. But if `len(predictions) == 5`, `len(ground_truth) == 5`, `len(domains) == 3`, then `5 != 5` is False, so the entire expression is False and the check is skipped.

**Recommendation**:
```python
if not (len(predictions) == len(ground_truth) == len(domains)):
    raise ValueError("All inputs must have same length")
```

---

#### H5. `_find_column` Uses Substring Matching Which Can Match Wrong Columns
**File**: `src/data/ha_requests_loader.py:182-188`
**Impact**: False column matches leading to incorrect data mapping.

```python
def _find_column(self, columns: list[str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        for col in columns:
            if candidate.lower() in col.lower():
                return col
    return None
```

If the dataset has columns like `["input_prompt", "prompt_template", "prompt"]`, searching for `"input"` will match `"input_prompt"` instead of the intended column. The substring-based matching is fragile and order-dependent.

**Recommendation**: Prefer exact match first, then fall back to substring:
```python
def _find_column(self, columns: list[str], candidates: list[str]) -> str | None:
    # Try exact match first
    for candidate in candidates:
        for col in columns:
            if candidate.lower() == col.lower():
                return col
    # Fall back to substring match
    for candidate in candidates:
        for col in columns:
            if candidate.lower() in col.lower():
                return col
    return None
```

---

### MEDIUM Severity

#### M1. Standard `logging` Used Instead of `structlog`
**File**: All source files
**Impact**: Inconsistent with the declared `structlog>=24.1.0` dependency and HomeIQ logging conventions.

Every module uses:
```python
import logging
logger = logging.getLogger(__name__)
```

But `structlog` is listed as a dependency in both `pyproject.toml` and `requirements.txt` and is never imported anywhere.

**Recommendation**: Either use `structlog` consistently:
```python
import structlog
logger = structlog.get_logger(__name__)
```
Or remove `structlog` from dependencies if standard logging is intentional.

---

#### M2. Hardcoded OpenAI Pricing Will Become Stale
**File**: `src/training/fine_tune_openai.py:153-158`
**Impact**: Cost estimates will be inaccurate as OpenAI updates pricing.

```python
# Pricing per 1M tokens (as of 2024)
pricing = {
    "gpt-4o-mini": {"training": 3.00, "input": 0.15, "output": 0.60},
    "gpt-4o": {"training": 25.00, "input": 2.50, "output": 10.00},
    "gpt-3.5-turbo": {"training": 8.00, "input": 0.50, "output": 1.50},
}
```

The comment says "as of 2024" and the values are already outdated. This is a constant maintenance burden.

**Recommendation**: Move pricing to a configuration file or add a prominent warning that these are estimates only. At minimum, log a deprecation notice:
```python
logger.warning("Cost estimate uses hardcoded 2024 pricing. Actual costs may differ.")
```

---

#### M3. Token Count Estimation is Extremely Rough
**File**: `src/training/fine_tune_openai.py:147-148`
**Impact**: Cost estimates could be off by 30-50%.

```python
# Rough estimate: 1 token per 4 characters
total_tokens += len(content) // 4
```

The `1 token per 4 characters` rule is a very rough heuristic for English text. For JSON-structured responses, code, or non-English content, this can be significantly off.

**Recommendation**: Use the `tiktoken` library for accurate token counts:
```python
import tiktoken
encoding = tiktoken.encoding_for_model(base_model)
total_tokens += len(encoding.encode(content))
```

---

#### M4. `map_elements` With Python Lambda is Slow for Large Datasets
**File**: `src/data/ha_requests_loader.py:155-162` and `src/data/ha_requests_loader.py:169-176`
**Impact**: Performance bottleneck when processing large datasets.

```python
pl.col(entities_col)
    .map_elements(
        lambda x: json.dumps(x) if isinstance(x, (dict, list)) else str(x),
        return_dtype=pl.Utf8
    )
    .alias("entities")
```

`map_elements` with a Python lambda disables Polars' native query optimization and falls back to row-by-row Python execution. For a dataset with 100K+ rows, this will be significantly slower than native Polars operations.

**Recommendation**: Use native Polars expressions where possible. For the JSON serialization, consider using `pl.col().cast(pl.Utf8)` or `pl.col().struct.json_encode()` if the data is already structured.

---

#### M5. No Validation Dataset Support in OpenAI Fine-Tuning
**File**: `src/training/fine_tune_openai.py:224-272`
**Impact**: Cannot monitor overfitting during OpenAI fine-tuning.

The `create_fine_tuning_job` method does not support a validation file, even though OpenAI's fine-tuning API supports a `validation_file` parameter. The PEFT trainer supports `eval_dataset`, creating an inconsistency.

**Recommendation**: Add `validation_file_id` parameter:
```python
def create_fine_tuning_job(
    self,
    training_file_id: str | None = None,
    validation_file_id: str | None = None,
    ...
) -> str:
    ...
    job_params = {
        "training_file": file_id,
        "model": model_name,
        "hyperparameters": hyperparameters,
        "suffix": suffix,
    }
    if validation_file_id:
        job_params["validation_file"] = validation_file_id
    response = self.client.fine_tuning.jobs.create(**job_params)
```

---

#### M6. Labels Applied to Full Sequence Including Padding
**File**: `src/training/fine_tune_peft.py:199-202`
**Impact**: Model learns to predict padding tokens, wasting compute and potentially hurting quality.

```python
tokenized["labels"] = tokenized["input_ids"].copy()
```

The labels include all tokens (including padding tokens and the instruction/input portion). For instruction-tuning, loss should only be computed on the response tokens. Additionally, padding tokens should be masked with `-100` to be ignored by the loss function.

**Recommendation**:
```python
# Mask padding tokens in labels
labels = tokenized["input_ids"].copy()
labels = [-100 if token == self.tokenizer.pad_token_id else token for token in labels]
tokenized["labels"] = labels
```

For even better training, mask the instruction and input portions too, only computing loss on the output/response tokens.

---

#### M7. No Stratified Split for Imbalanced Datasets
**File**: `src/data/ha_requests_loader.py:387-422`
**Impact**: Rare intents may be entirely absent from validation/test sets.

```python
def split_dataset(self, df, train_ratio=0.8, val_ratio=0.1, seed=42):
    df = df.sample(fraction=1.0, seed=seed)
    n = len(df)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    ...
```

Random splitting does not account for class distribution. If `HassHelp` represents only 0.5% of data, it may not appear in the 10% validation split at all.

**Recommendation**: Implement stratified splitting by intent:
```python
def split_dataset(self, df, train_ratio=0.8, val_ratio=0.1, seed=42, stratify_col="intent"):
    if stratify_col and stratify_col in df.columns:
        # Use sklearn's StratifiedShuffleSplit or group-by-intent sampling
        from sklearn.model_selection import train_test_split
        # ... stratified split logic
```

---

#### M8. `main()` Functions Contain Hardcoded Paths
**File**: `src/data/ha_requests_loader.py:451`, `src/training/fine_tune_peft.py:412`
**Impact**: Example code writes to working directory with hardcoded paths.

```python
# ha_requests_loader.py:451
loader.save_openai_jsonl(openai_examples, "data/ha_requests_openai.jsonl")

# fine_tune_peft.py:412
fine_tuner.train(
    train_dataset,
    output_dir="./models/ha-lora-test",
    ...
)
```

**Recommendation**: Use `argparse` or environment variables for paths in `main()` functions, or at minimum use `tempfile` for example code.

---

### LOW Severity

#### L1. `pl.count()` Deprecated in Newer Polars Versions
**File**: `src/data/ha_requests_loader.py:367` and `src/data/ha_requests_loader.py:382`
**Impact**: Deprecation warnings or errors with Polars >=1.x.

```python
.agg([
    pl.count().alias("count"),
])
```

In Polars 1.x+, `pl.count()` in aggregation context is deprecated in favor of `pl.len()`.

**Recommendation**:
```python
.agg([
    pl.len().alias("count"),
])
```

---

#### L2. OpenAI Model List is Outdated
**File**: `src/training/fine_tune_openai.py:35-39`
**Impact**: Users cannot use newer models without knowing exact model IDs.

```python
SUPPORTED_MODELS = {
    "gpt-4o-mini": "gpt-4o-mini-2024-07-18",
    "gpt-4o": "gpt-4o-2024-08-06",
    "gpt-3.5-turbo": "gpt-3.5-turbo-0125",
}
```

GPT-3.5-turbo fine-tuning is deprecated. GPT-4o has newer snapshot versions. These model IDs will grow stale.

**Recommendation**: Use the base model names directly (OpenAI resolves them to the latest snapshot) or query available models via the API:
```python
SUPPORTED_MODELS = {
    "gpt-4o-mini": "gpt-4o-mini",
    "gpt-4o": "gpt-4o",
}
```

---

#### L3. PEFT Model List Contains Outdated Versions
**File**: `src/training/fine_tune_peft.py:36-41`
**Impact**: Users are pointed to older model versions.

```python
SUPPORTED_MODELS = {
    "mistral-7b": "mistralai/Mistral-7B-Instruct-v0.3",
    "llama-3-8b": "meta-llama/Meta-Llama-3-8B-Instruct",
    "phi-3-mini": "microsoft/Phi-3-mini-4k-instruct",
    "gemma-2b": "google/gemma-2b-it",
}
```

As of early 2026, newer versions exist for most of these models (Llama 3.3, Mistral models, Phi-4, Gemma 2). Consider updating or using version-agnostic references.

---

#### L4. `save_results` Does Not Create Parent Directories
**File**: `src/evaluation/metrics.py:311-315`
**Impact**: `FileNotFoundError` if the output directory does not exist.

```python
def save_results(self, output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(self.get_summary(), f, indent=2)
```

Unlike `save_openai_jsonl` and `save_processed` in the loader (which both create parent dirs), this method does not.

**Recommendation**:
```python
def save_results(self, output_path: str) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(self.get_summary(), f, indent=2)
```

---

#### L5. No `__all__` Export in `src/__init__.py`
**File**: `src/__init__.py`
**Impact**: Unclear public API surface.

```python
"""NLP Fine-Tuning Service for HomeIQ."""

__version__ = "1.0.0"
```

The sub-packages define `__all__` but the top-level package does not re-export them.

**Recommendation**:
```python
"""NLP Fine-Tuning Service for HomeIQ."""

__version__ = "1.0.0"

from .data import HARequestsLoader
from .training import HAFineTuner, OpenAIFineTuner
from .evaluation import NLPEvaluator

__all__ = ["HARequestsLoader", "HAFineTuner", "OpenAIFineTuner", "NLPEvaluator"]
```

---

#### L6. `evaluation_strategy` Parameter is Deprecated
**File**: `src/training/fine_tune_peft.py:264`
**Impact**: Deprecation warning from transformers library.

```python
evaluation_strategy="steps" if eval_dataset else "no",
```

In `transformers>=4.46.0`, `evaluation_strategy` has been renamed to `eval_strategy`.

**Recommendation**:
```python
eval_strategy="steps" if eval_dataset else "no",
```

---

#### L7. README References Non-Existent Integration Path
**File**: `README.md:141`
**Impact**: Misleading documentation.

```
See `services/ai-automation-service-new/src/clients/openai_client.py` for integration.
```

This references a specific file in another service. If that path changes, the README becomes misleading. Should be verified and kept in sync.

---

## Enhancement Suggestions

### E1. Add a CLI Entry Point
The service has `main()` functions in each module but no unified CLI. Consider adding a CLI using `argparse` or `click`:

```toml
# pyproject.toml
[project.scripts]
nlp-fine-tune = "src.cli:main"
```

This would allow commands like:
```bash
nlp-fine-tune load --output data/training.jsonl
nlp-fine-tune train-peft --model mistral-7b --epochs 3
nlp-fine-tune train-openai --model gpt-4o-mini
nlp-fine-tune evaluate --predictions results.json
```

### E2. Add Model Versioning and Experiment Tracking
There is no mechanism to track which model was trained with what data, hyperparameters, or performance metrics. Consider:
- Saving a `training_config.json` alongside each model with all hyperparameters
- Implementing simple MLflow or Weights & Biases integration
- At minimum, logging the full config at training start

### E3. Add Data Validation Pipeline
The data loader does no validation of the loaded data beyond column detection. Consider adding:
- Schema validation for expected data types
- Data quality checks (empty strings, duplicates, extreme lengths)
- Distribution analysis logging

### E4. Add Progress Bars for Long Operations
`tqdm` is in `requirements.txt` but never imported. Add progress bars for:
- Data preprocessing (`_preprocess`)
- Format conversion (`to_openai_format`, `to_peft_format`)
- Training data upload

### E5. Consider Adding a REST API Wrapper
If this service needs to integrate with the HomeIQ platform at runtime (not just offline tooling), wrap the key functions in a FastAPI service with endpoints for:
- `POST /fine-tune/prepare` - Prepare training data
- `POST /fine-tune/openai` - Start OpenAI fine-tuning
- `POST /fine-tune/peft` - Start PEFT fine-tuning
- `GET /fine-tune/status/{job_id}` - Check job status
- `POST /evaluate` - Evaluate a model

---

## Prioritized Action Plan

### Phase 1: Critical Fixes (Immediate)
| # | Finding | Effort | File |
|---|---------|--------|------|
| C2 | Add basic test suite | Medium | `tests/` |
| C3 | Validate and protect API key | Low | `fine_tune_openai.py` |
| H4 | Fix chained `!=` comparison bug | Low | `metrics.py:262` |
| H3 | Sync dependencies between pyproject.toml and requirements.txt | Low | `pyproject.toml`, `requirements.txt` |

### Phase 2: Security & Correctness (This Sprint)
| # | Finding | Effort | File |
|---|---------|--------|------|
| H1 | Restrict `trust_remote_code=True` to known models | Low | `fine_tune_peft.py` |
| H5 | Fix column matching to prefer exact match | Low | `ha_requests_loader.py` |
| M6 | Mask padding tokens in training labels | Medium | `fine_tune_peft.py` |
| L1 | Replace deprecated `pl.count()` with `pl.len()` | Low | `ha_requests_loader.py` |
| L6 | Replace deprecated `evaluation_strategy` | Low | `fine_tune_peft.py` |

### Phase 3: Quality Improvements (Next Sprint)
| # | Finding | Effort | File |
|---|---------|--------|------|
| M1 | Switch to structlog or remove dependency | Low | All files |
| M3 | Use tiktoken for accurate token counts | Low | `fine_tune_openai.py` |
| M4 | Optimize map_elements for Polars performance | Medium | `ha_requests_loader.py` |
| M5 | Add validation file support to OpenAI fine-tuning | Low | `fine_tune_openai.py` |
| M7 | Implement stratified dataset splitting | Medium | `ha_requests_loader.py` |

### Phase 4: Enhancements (Backlog)
| # | Finding | Effort | File |
|---|---------|--------|------|
| C1 | Add Dockerfile if deployment needed | Medium | New file |
| M2 | Externalize pricing to config | Low | `fine_tune_openai.py` |
| L2/L3 | Update model references | Low | Both training files |
| L4 | Create parent dirs in save_results | Low | `metrics.py` |
| L5 | Add top-level __all__ exports | Low | `src/__init__.py` |
| E1 | Add unified CLI | Medium | New file |
| E2 | Add experiment tracking | Medium | Training files |

---

## Summary Statistics

| Severity | Count |
|----------|-------|
| Critical | 3 |
| High | 5 |
| Medium | 8 |
| Low | 7 |
| Enhancements | 5 |
| **Total** | **28** |

**Overall Assessment**: The service contains well-structured, readable code with clear module separation and good documentation. However, it lacks fundamental production readiness requirements: no tests, no containerization, a security risk with `trust_remote_code`, a subtle bug in the domain accuracy validation, and several dependency/deprecation issues. The ML-specific findings (label masking, stratified splitting, validation support) would directly impact model quality. Priority should be given to the test suite, the comparison bug fix, and the security hardening of model loading.
