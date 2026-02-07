# Automation Linter Service - Deep Code Review

**Service**: automation-linter (Tier 7)
**Port**: 8016 (external) -> 8020 (internal)
**Date**: 2026-02-06
**Reviewer**: Claude Code (Automated Deep Review)

---

## Service Overview

The automation-linter service is a FastAPI-based microservice that lints and auto-fixes Home Assistant automation YAML. It provides:

- **POST /lint** - Lint automation YAML and return findings
- **POST /fix** - Lint and auto-fix automation YAML
- **GET /rules** - List all available lint rules
- **GET /health** - Health check
- **GET /** - Serves a web UI or API info

The service uses a shared library (`shared/ha_automation_lint/`) that contains the lint engine, parser, rules (15 MVP rules), auto-fixer, and YAML renderer.

### Files Reviewed

| File | Lines | Purpose |
|------|-------|---------|
| `src/main.py` | 308 | FastAPI service wrapper |
| `src/__init__.py` | 1 | Empty init |
| `Dockerfile` | 29 | Container build |
| `requirements.txt` | 9 | Python dependencies |
| `.dockerignore` | 17 | Docker ignore rules |
| `ui/index.html` | 404 | Web UI |
| `shared/ha_automation_lint/engine.py` | 123 | Lint engine |
| `shared/ha_automation_lint/models.py` | 101 | Data models |
| `shared/ha_automation_lint/constants.py` | 62 | Constants |
| `shared/ha_automation_lint/parsers/yaml_parser.py` | 190 | YAML parser |
| `shared/ha_automation_lint/renderers/yaml_renderer.py` | 121 | YAML renderer |
| `shared/ha_automation_lint/fixers/auto_fixer.py` | 120 | Auto-fixer |
| `shared/ha_automation_lint/rules/base.py` | 46 | Rule base class |
| `shared/ha_automation_lint/rules/mvp_rules.py` | 492 | 15 MVP rules |

---

## Findings

### Critical Severity

#### C1: Port Mismatch Between Documentation and Code

**File**: `src/main.py:307`, `docker-compose.yml:2273`

The service is documented as Tier 7, Port 8016, but the internal code runs on port 8020. While docker-compose maps 8016->8020, this creates confusion.

```python
# src/main.py:307
uvicorn.run(app, host="0.0.0.0", port=8020)
```

```yaml
# docker-compose.yml:2273
ports:
  - "8016:8020"
```

**Impact**: Not a runtime bug since docker handles port mapping, but any documentation or service-discovery referencing port 8020 externally will fail.

**Recommendation**: Either standardize on one port throughout, or add a comment in main.py explaining the port mapping.

---

#### C2: Environment Variables Defined in docker-compose But Never Read by Code

**File**: `src/main.py`, `docker-compose.yml:2274-2277`

The docker-compose defines environment variables `LOG_LEVEL`, `MAX_YAML_SIZE_BYTES`, and `PROCESSING_TIMEOUT_SECONDS`, but the application code **never reads them**. All values are hardcoded in `shared/ha_automation_lint/constants.py`.

```yaml
# docker-compose.yml:2274-2277
environment:
  - LOG_LEVEL=INFO
  - MAX_YAML_SIZE_BYTES=500000
  - PROCESSING_TIMEOUT_SECONDS=30
```

```python
# shared/ha_automation_lint/constants.py:46-48
MAX_YAML_SIZE_BYTES = 500_000  # 500KB  (hardcoded)
MAX_AUTOMATIONS_PER_REQUEST = 100
PROCESSING_TIMEOUT_SECONDS = 30  # (hardcoded, never used)
```

```python
# src/main.py:32-33
logging.basicConfig(
    level=logging.INFO,  # Hardcoded, not from LOG_LEVEL env var
```

**Impact**: Operators changing environment variables will have zero effect on service behavior. This is a **configuration lie** that wastes debugging time.

**Recommendation**:
```python
import os

# In constants.py or main.py
MAX_YAML_SIZE_BYTES = int(os.environ.get("MAX_YAML_SIZE_BYTES", 500_000))
PROCESSING_TIMEOUT_SECONDS = int(os.environ.get("PROCESSING_TIMEOUT_SECONDS", 30))

# In main.py
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO), ...)
```

---

#### C3: PROCESSING_TIMEOUT_SECONDS Is Defined But Never Enforced

**File**: `shared/ha_automation_lint/constants.py:48`, `src/main.py`

The constant `PROCESSING_TIMEOUT_SECONDS = 30` is imported by `main.py` (line 27) but **never used**. There is no timeout enforcement on the `/lint` or `/fix` endpoints. A maliciously crafted YAML could cause the service to hang indefinitely.

```python
# src/main.py:27 - imported but unused
from ha_automation_lint.constants import (
    ENGINE_VERSION,
    RULESET_VERSION,
    FixMode,
    MAX_YAML_SIZE_BYTES,
    PROCESSING_TIMEOUT_SECONDS  # Imported but never used
)
```

**Impact**: Denial-of-service risk. A deeply nested or pathologically constructed YAML could consume CPU indefinitely.

**Recommendation**:
```python
import asyncio

@app.post("/lint", response_model=LintResponse)
async def lint_automation(request: LintRequest):
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(lint_engine.lint, request.yaml, strict=strict),
            timeout=PROCESSING_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        raise HTTPException(408, "Linting timed out")
```

---

#### C4: No Tests Exist

**File**: `tests/` (empty directory)

The `tests/` directory is completely empty. There are **zero tests** for the service wrapper (`main.py`) or the shared library.

**Impact**: No regression protection. Any change could break the service silently.

**Recommendation**: Add tests covering at minimum:
- Health check endpoint
- Lint endpoint with valid YAML
- Lint endpoint with invalid YAML
- Fix endpoint with fixable issues
- Request size limit enforcement
- Error handling for malformed requests

---

### High Severity

#### H1: CORS Wildcard in Production

**File**: `src/main.py:46-52`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Impact**: `allow_origins=["*"]` combined with `allow_credentials=True` is a security anti-pattern. While FastAPI/Starlette will refuse to set `Access-Control-Allow-Origin: *` when credentials are true (it will reject the request), the intent is clearly wrong. Any origin can make credentialed requests.

**Recommendation**:
```python
ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
```

---

#### H2: Duplicate Findings Conversion Code (DRY Violation)

**File**: `src/main.py:161-174` and `src/main.py:244-257`

The findings-to-dict conversion is copy-pasted between `/lint` and `/fix` endpoints:

```python
# Appears identically in both lint_automation() and fix_automation()
findings_dicts = [
    {
        "rule_id": f.rule_id,
        "severity": f.severity,
        "message": f.message,
        "why_it_matters": f.why_it_matters,
        "path": f.path,
        "suggested_fix": {
            "type": f.suggested_fix.type,
            "summary": f.suggested_fix.summary
        } if f.suggested_fix else None
    }
    for f in report.findings
]
```

**Impact**: If the serialization logic needs to change, it must be updated in two places. Bugs from inconsistent updates.

**Recommendation**: Extract to a helper function:
```python
def _serialize_findings(findings: List[Finding]) -> List[Dict]:
    return [
        {
            "rule_id": f.rule_id,
            "severity": f.severity,
            "message": f.message,
            "why_it_matters": f.why_it_matters,
            "path": f.path,
            "suggested_fix": {
                "type": f.suggested_fix.type,
                "summary": f.suggested_fix.summary
            } if f.suggested_fix else None
        }
        for f in findings
    ]
```

---

#### H3: `sys.path` Manipulation Throughout Shared Module

**Files**: `shared/ha_automation_lint/engine.py:10`, `parsers/yaml_parser.py:12`, `renderers/yaml_renderer.py:11`, `fixers/auto_fixer.py:10`, `rules/base.py:11`, `rules/mvp_rules.py:12`, `src/main.py:9`

Every single file in the shared module does `sys.path.insert(0, ...)` to resolve imports:

```python
# engine.py:10
sys.path.insert(0, str(Path(__file__).parent))

# yaml_parser.py:12
sys.path.insert(0, str(Path(__file__).parent.parent))

# main.py:9
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))
```

**Impact**:
- Pollutes `sys.path` with duplicate entries on every import
- Fragile path calculations that break with directory restructuring
- Makes the module non-installable via standard pip
- Causes confusing import errors if paths resolve incorrectly

**Recommendation**: Create a proper `pyproject.toml` or `setup.py` for the shared module and install it with `pip install -e .` in development. In Docker, install it as a proper package. Use relative imports within the package:

```python
# engine.py - use relative imports
from .models import AutomationIR, Finding, LintReport
from .parsers.yaml_parser import AutomationParser
from .rules.mvp_rules import get_all_rules
from .constants import ENGINE_VERSION, RULESET_VERSION, Severity
```

---

#### H4: Shallow Copy in AutoFixer Does Not Isolate Mutations

**File**: `shared/ha_automation_lint/fixers/auto_fixer.py:47`

```python
fixed_automations = [auto for auto in automations]  # Shallow copy for now
```

The "fix" operations mutate the original `AutomationIR` objects in-place:

```python
# auto_fixer.py:86-88
automation.description = ""
automation.raw_source["description"] = ""  # Mutates original!
```

**Impact**: The shallow copy provides zero protection. The original automation objects passed by the caller are mutated. In `main.py`, `parser.parse()` returns automations that are then passed to both the fixer and used to build the response. The mutations leak back.

**Recommendation**: Use `copy.deepcopy` or reconstruct the IR:
```python
import copy
fixed_automations = copy.deepcopy(automations)
```

---

#### H5: UI Uses Deprecated `document.execCommand('copy')`

**File**: `ui/index.html:362`

```javascript
function copyFixed() {
    const textarea = document.getElementById('fixed-yaml');
    textarea.select();
    document.execCommand('copy');  // Deprecated API
```

**Impact**: `document.execCommand('copy')` is deprecated and may be removed from browsers. Also, the `event` variable on line 365 is an implicit global, which fails in strict mode.

**Recommendation**:
```javascript
async function copyFixed() {
    const text = document.getElementById('fixed-yaml').value;
    await navigator.clipboard.writeText(text);
    // Visual feedback...
}
```

---

#### H6: `fix_mode` Not Validated Against Allowed Values

**File**: `src/main.py:78`

```python
class FixRequest(BaseModel):
    fix_mode: str = Field(default=FixMode.SAFE, description="Fix mode: safe or none")
```

The `fix_mode` field accepts any string. If a user sends `fix_mode: "aggressive"`, it silently passes through without error. The `FixMode` class is just plain string constants, not an enum.

**Impact**: No input validation on fix mode. Unexpected modes silently skip fixing without informing the user.

**Recommendation**: Use a Pydantic `Literal` or Python `Enum`:
```python
from typing import Literal

class FixRequest(BaseModel):
    fix_mode: Literal["safe", "none"] = Field(default="safe", description="Fix mode: safe or none")
```

---

### Medium Severity

#### M1: Redundant Duplicate Rules (SCHEMA001/LOGIC004, SCHEMA002/LOGIC005)

**File**: `shared/ha_automation_lint/rules/mvp_rules.py:269-310`

Rules LOGIC004 (`EmptyTriggerListRule`) and LOGIC005 (`EmptyActionListRule`) duplicate SCHEMA001 and SCHEMA002 respectively. The code even acknowledges this:

```python
class EmptyTriggerListRule(Rule):
    """Check for empty trigger list."""
    rule_id = "LOGIC004"
    # ...
    def check(self, automation: AutomationIR) -> List[Finding]:
        # This is redundant with SCHEMA001 but kept for completeness
```

**Impact**: Users see duplicate findings for the same issue, reducing trust in the linter.

**Recommendation**: Remove the redundant rules or make SCHEMA001/002 handle both cases (missing key vs empty list) with distinct messages.

---

#### M2: `MAX_AUTOMATIONS_PER_REQUEST` Limit Defined But Never Enforced

**File**: `shared/ha_automation_lint/constants.py:47`

```python
MAX_AUTOMATIONS_PER_REQUEST = 100
```

This constant is never imported or used anywhere. There is no limit on the number of automations in a single request.

**Impact**: A request with thousands of automations would be processed without limit, potentially causing memory exhaustion or timeout.

**Recommendation**: Add enforcement in the lint/fix endpoints after parsing:
```python
if len(automations) > MAX_AUTOMATIONS_PER_REQUEST:
    raise HTTPException(413, f"Too many automations ({len(automations)}). Max: {MAX_AUTOMATIONS_PER_REQUEST}")
```

---

#### M3: Content-Length Check Can Be Bypassed

**File**: `src/main.py:94-103`

```python
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_YAML_SIZE_BYTES:
        return JSONResponse(...)
    return await call_next(request)
```

**Issues**:
1. `content-length` header is optional and can be omitted (e.g., chunked transfer encoding)
2. `int(content_length)` can raise `ValueError` on malformed input, returning a 500
3. There is a duplicate check in the endpoint body (`len(request.yaml.encode('utf-8')) > MAX_YAML_SIZE_BYTES`) which makes the middleware redundant for valid requests

**Recommendation**:
```python
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_YAML_SIZE_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={"error": f"Request too large. Max size: {MAX_YAML_SIZE_BYTES} bytes"}
                )
        except ValueError:
            return JSONResponse(status_code=400, content={"error": "Invalid Content-Length header"})
    return await call_next(request)
```

---

#### M4: No Rate Limiting

**File**: `src/main.py`

There is no rate limiting on any endpoint. The `/lint` and `/fix` endpoints perform CPU-intensive YAML parsing and rule checking.

**Impact**: Service can be overwhelmed by rapid requests, especially since there is no timeout enforcement (see C3).

**Recommendation**: Add basic rate limiting via middleware or use `slowapi`:
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

---

#### M5: Diff Summary Is Trivially Inaccurate

**File**: `shared/ha_automation_lint/renderers/yaml_renderer.py:101-120`

```python
def create_diff_summary(self, original: str, fixed: str) -> str:
    original_lines = original.strip().split('\n')
    fixed_lines = fixed.strip().split('\n')
    if original_lines == fixed_lines:
        return "No changes"
    changes = abs(len(fixed_lines) - len(original_lines))
    return f"Modified {changes} lines"
```

If a fix changes 10 lines but the total line count stays the same, this reports "Modified 0 lines". Additionally, this method is never called anywhere -- the `/fix` endpoint creates its own diff summary inline:

```python
# main.py:239
diff_summary = f"Applied {len(applied_fixes)} fixes"
```

**Impact**: Dead code that is also incorrect.

**Recommendation**: Remove `create_diff_summary` or use a proper diff library like `difflib`.

---

#### M6: Inline Import Inside Request Handler

**File**: `src/main.py:229`

```python
@app.post("/fix", response_model=FixResponse)
async def fix_automation(request: FixRequest):
    # ...
    if request.fix_mode != FixMode.NONE:
        from ha_automation_lint.parsers.yaml_parser import AutomationParser  # Inline import
        parser = AutomationParser()
```

**Impact**: Import inside a request handler adds latency on first call. The module is already available at module scope. More importantly, this re-parses the YAML when `lint_engine.lint()` already parsed it internally -- the work is done twice.

**Recommendation**: Import at module level and restructure to avoid double-parsing:
```python
# At top of file (already available via engine)
from ha_automation_lint.parsers.yaml_parser import AutomationParser

# Better: modify engine.lint() to return the parsed automations alongside the report
```

---

#### M7: UI Has XSS Vulnerability via `innerHTML`

**File**: `ui/index.html:343-347`

```javascript
div.innerHTML = `
    <strong>${icon} <span class="rule-badge">${finding.rule_id}</span>${finding.message}</strong>
    <small><strong>Why it matters:</strong> ${finding.why_it_matters}</small>
    <small><strong>Location:</strong> ${finding.path}</small>
`;
```

The `finding.message`, `finding.why_it_matters`, and `finding.path` fields are inserted directly into HTML via template literals without escaping. If a crafted YAML file produces a finding message containing HTML/script tags, it would execute in the user's browser.

**Impact**: Stored XSS if the lint engine echoes user-provided YAML content in finding messages (which it does -- e.g., service names, entity IDs).

**Recommendation**: Use `textContent` or escape HTML:
```javascript
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

div.innerHTML = `
    <strong>${icon} <span class="rule-badge">${escapeHtml(finding.rule_id)}</span>${escapeHtml(finding.message)}</strong>
    ...
`;
```

---

#### M8: Healthcheck Uses `httpx` but It May Not Be Available

**File**: `Dockerfile:25-26`

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8020/health', timeout=5.0)"
```

The healthcheck imports `httpx` in a one-off Python command. While `httpx` is in `requirements.txt`, using `curl` or `wget` would be more standard and lighter.

**Impact**: Minor -- it works but spawns a full Python interpreter for each health check, which is heavy on resources.

**Recommendation**:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8020/health || exit 1
```

Or use a lighter Python approach:
```dockerfile
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8020/health', timeout=5)"
```

---

### Low Severity

#### L1: Dockerfile Does Not Pin Base Image

**File**: `Dockerfile:1`

```dockerfile
FROM python:3.11-slim
```

**Impact**: Builds are not reproducible. A new `python:3.11-slim` image could introduce unexpected changes.

**Recommendation**: Pin to a specific digest:
```dockerfile
FROM python:3.11-slim@sha256:<specific-hash>
```

---

#### L2: No Non-Root User in Dockerfile

**File**: `Dockerfile`

The container runs as root by default.

**Impact**: If the container is compromised, the attacker has root access within the container.

**Recommendation**:
```dockerfile
RUN useradd -r -s /bin/false appuser
USER appuser
```

---

#### L3: Implicit `event` Global in UI JavaScript

**File**: `ui/index.html:365`

```javascript
function copyFixed() {
    // ...
    const btn = event.target;  // 'event' is implicit global, not a parameter
```

**Impact**: Works in most browsers but is fragile. Will break with `"use strict"` or in certain browsers.

**Recommendation**:
```javascript
function copyFixed(event) {
    const btn = event.target;
```
And update the HTML:
```html
<button class="btn-success" onclick="copyFixed(event)">Copy Fixed YAML</button>
```

---

#### L4: Logging Uses f-strings Instead of Lazy Formatting

**File**: `src/main.py:157, 176-178, 195, 219, 241, 277`

```python
logger.info(f"Linting automation YAML (strict={strict})")
logger.error(f"Lint error: {e}", exc_info=True)
```

**Impact**: The f-string is evaluated even when logging at a level that suppresses the message. Minor performance impact.

**Recommendation**:
```python
logger.info("Linting automation YAML (strict=%s)", strict)
logger.error("Lint error: %s", e, exc_info=True)
```

---

#### L5: `options` Field in LintRequest Should Have Typed Schema

**File**: `src/main.py:63`

```python
class LintRequest(BaseModel):
    yaml: str = Field(..., description="Automation YAML to lint")
    options: Optional[Dict] = Field(default_factory=dict, description="Optional lint options")
```

**Impact**: The `options` dict is untyped -- callers have no API documentation on valid options. The only option used is `strict`.

**Recommendation**:
```python
class LintOptions(BaseModel):
    strict: bool = Field(default=False, description="Treat warnings as errors")

class LintRequest(BaseModel):
    yaml: str = Field(..., description="Automation YAML to lint")
    options: Optional[LintOptions] = None
```

---

#### L6: `yaml.safe_load` Is Fine But Single-Document Only

**File**: `shared/ha_automation_lint/parsers/yaml_parser.py:40`

```python
data = yaml.safe_load(yaml_content)
```

**Impact**: `safe_load` only loads the first YAML document. Multi-document YAML (separated by `---`) silently drops all but the first document.

**Recommendation**: Document this limitation or use `yaml.safe_load_all()` if multi-document support is desired.

---

#### L7: URL Object Leak in Download Function

**File**: `ui/index.html:375-385`

```javascript
function downloadFixed() {
    const yaml = document.getElementById('fixed-yaml').value;
    const blob = new Blob([yaml], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'automation_fixed.yaml';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
```

This is actually correctly implemented with `revokeObjectURL`. No issue -- included for completeness of review.

---

## Enhancement Suggestions

### E1: Add Structured Logging with Correlation IDs
Use the shared `correlation_middleware.py` to add request correlation IDs to all log entries. This enables tracing requests across services.

### E2: Add Prometheus Metrics
Expose basic metrics (lint requests, fix requests, error counts, latency histograms) at a `/metrics` endpoint for observability.

### E3: Add OpenAPI Response Examples
Add example responses to the Pydantic models for better `/docs` page usability:
```python
class LintResponse(BaseModel):
    class Config:
        json_schema_extra = {"example": {...}}
```

### E4: Support Rule Configuration Per Request
The `LintEngine` supports `rule_config` at init time, but there is no way for API callers to enable/disable rules per-request. Add this to the `options` field.

### E5: Add Caching for Repeated YAML
If users lint the same YAML repeatedly (e.g., during development), results could be cached by YAML hash.

### E6: Move Double-Parse Fix
The `/fix` endpoint parses YAML twice -- once via `lint_engine.lint()` and once explicitly. Refactor the engine to expose parsed automations alongside the report.

---

## Prioritized Action Plan

### Immediate (Before Next Deployment)

| # | Finding | Severity | Effort |
|---|---------|----------|--------|
| 1 | C2: Wire up environment variables to code | Critical | Low |
| 2 | C3: Enforce PROCESSING_TIMEOUT_SECONDS | Critical | Medium |
| 3 | H6: Validate fix_mode against allowed values | High | Low |
| 4 | M7: Fix XSS vulnerability in UI innerHTML | Medium | Low |
| 5 | M3: Handle malformed Content-Length header | Medium | Low |

### Short-Term (Within 1-2 Sprints)

| # | Finding | Severity | Effort |
|---|---------|----------|--------|
| 6 | C4: Add test suite | Critical | High |
| 7 | H1: Restrict CORS origins | High | Low |
| 8 | H2: Extract findings serialization helper | High | Low |
| 9 | H4: Deep copy automations before fixing | High | Low |
| 10 | M2: Enforce MAX_AUTOMATIONS_PER_REQUEST | Medium | Low |
| 11 | M6: Eliminate double-parse in /fix endpoint | Medium | Medium |

### Medium-Term (Next Quarter)

| # | Finding | Severity | Effort |
|---|---------|----------|--------|
| 12 | H3: Replace sys.path hacks with proper packaging | High | Medium |
| 13 | H5: Replace deprecated execCommand | High | Low |
| 14 | M1: Remove redundant LOGIC004/LOGIC005 rules | Medium | Low |
| 15 | M4: Add rate limiting | Medium | Medium |
| 16 | M5: Remove dead create_diff_summary method | Medium | Low |
| 17 | L1-L6: Low-severity items | Low | Low-Med |

---

## Summary Statistics

| Severity | Count |
|----------|-------|
| Critical | 4 |
| High | 6 |
| Medium | 8 |
| Low | 7 |
| **Total** | **25** |

The automation-linter service has a clean, well-structured codebase with good separation of concerns (parser, engine, rules, fixer, renderer). The main risks are: (1) configuration that appears functional but is disconnected from code, (2) missing timeout enforcement enabling DoS, (3) zero test coverage, and (4) XSS in the UI. The shared `ha_automation_lint` module is well-designed architecturally but suffers from fragile `sys.path` manipulation that should be replaced with proper Python packaging.
