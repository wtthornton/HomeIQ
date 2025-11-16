# AI Code Executor Service

Secure Python code execution sandbox for MCP (Model Context Protocol) workflows. Hardened for a single-home Intel NUC deployment with zero lateral-movement tolerance.

## Overview

- **Purpose:** allow trusted HomeIQ tooling to execute short Python snippets without exposing the rest of the stack  
- **Scope:** local-only execution – network MCP tools are **disabled by default** until a redesigned trust model ships  
- **Architecture (2025 pattern):** FastAPI → async controller → subprocess-based sandbox → result serialization  
- **Key change:** multiple CVEs were closed in Nov-2025 by removing sys.path injection, adding offline-only context, and enforcing strict auth/validation.

```
Client (X-Executor-Token auth)
    ↓ POST /execute
FastAPI controller (code validation)
    ↓ safe AST + size checks
MCPSandbox (semaphore guard)
    ↓ subprocess fork
PythonSandbox worker
    ↓ RestrictedPython + import whitelist + resource limits
Result serialized back to client
```

## Security Controls

1. **Header auth:** every `/execute` call must include `X-Executor-Token` matching `EXECUTOR_API_TOKEN`.  
2. **CORS allow‑list:** origins default to `http://localhost:8030`; no wildcard.  
3. **Static code validator:** byte-size + AST-node limits, import allowlist, and forbidden attribute detection before compilation.  
4. **Context sanitizer:** request `context` must be JSON-serializable primitives (no objects, callables, or dunder keys).  
5. **Import enforcement:** custom `__import__` only loads modules declared in `SandboxConfig.allowed_imports`.  
6. **Process isolation:** each execution runs in a `spawn`ed subprocess with RLIMIT_{AS,DATA,STACK,FSIZE,NPROC,CPU}. If it exceeds `EXECUTION_TIMEOUT`, we tear it down.  
7. **Concurrency guard:** `MAX_CONCURRENT_EXECUTIONS` (default 2) prevents CPU exhaustion on the NUC.  
8. **Network isolation:** MCP tool registry now returns an empty context unless `ENABLE_MCP_NETWORK_TOOLS=true`, and even then raises until a hardened design is complete.  
9. **Linux-only enforcement:** the service refuses to execute on non-Linux hosts because resource limits cannot be applied reliably elsewhere.

## API Surface

### Authentication

All mutating calls require:

```
X-Executor-Token: <value of EXECUTOR_API_TOKEN>
Content-Type: application/json
```

### POST `/execute`

```bash
curl -X POST http://localhost:8030/execute \
  -H "X-Executor-Token: local-dev-token" \
  -H "Content-Type: application/json" \
  -d '{
        "code": "result = [n*n for n in range(5)]\n_ = result"
      }'
```

Response:

```json
{
  "success": true,
  "stdout": "",
  "stderr": "",
  "return_value": [0, 1, 4, 9, 16],
  "execution_time": 0.12,
  "memory_used_mb": 3.4,
  "error": null
}
```

### GET `/health`

Returns service metadata plus whether the sandbox finished initialization.

## Configuration (ENV)

| Variable | Default | Description |
|----------|---------|-------------|
| `EXECUTION_TIMEOUT` | `30` | Max wall clock seconds per run |
| `MAX_MEMORY_MB` | `128` | Memory ceiling enforced via RLIMIT |
| `MAX_CPU_PERCENT` | `50.0` | CPU time budget (applied to RLIMIT_CPU) |
| `MAX_CONCURRENT_EXECUTIONS` | `2` | Semaphore limit (protects the NUC) |
| `MAX_CODE_BYTES` | `10000` | Reject larger payloads before compilation |
| `MAX_AST_NODES` | `5000` | Complexity guardrail |
| `ALLOWED_ORIGINS` | `http://localhost:8030` | Comma-separated list for CORS |
| `EXECUTOR_API_TOKEN` | `local-dev-token` | Shared secret for all callers |
| `ENABLE_MCP_NETWORK_TOOLS` | `false` | Must stay `false` until network hardening ships |
| `MCP_WORKSPACE_DIR` | `/tmp/mcp_workspace` | Reserved for future local tools |
| `LOG_LEVEL` | `INFO` | Python logging level |

## Development

```bash
cd services/ai-code-executor
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8030

# Smoke test (requires EXECUTOR_API_TOKEN)
curl -H "X-Executor-Token: local-dev-token" \
     -H "Content-Type: application/json" \
     -d '{"code": "_ = 42"}' \
     http://localhost:8030/execute
```

Docker (single-node deployment):

```bash
docker build -t homeiq-code-executor -f services/ai-code-executor/Dockerfile .
docker run --rm -p 8030:8030 \
  -e EXECUTOR_API_TOKEN=change-me \
  homeiq-code-executor
```

## File Structure (2025-11-16)

```
services/ai-code-executor/
├── Dockerfile
├── README.md
├── requirements.txt
└── src/
    ├── config.py
    ├── main.py
    ├── executor/
    │   ├── sandbox.py
    │   └── mcp_sandbox.py
    ├── mcp/
    │   └── homeiq_tools.py
    └── security/
        └── code_validator.py
```

## Current Limitations

- No network MCP tools are exposed; turning them on raises intentionally until a signed-request design is complete.  
- Service only supports Linux because RLIMIT and multiprocessing isolation rely on kernel features.  
- There is no public metrics endpoint yet; rely on FastAPI logs for audit trails.  
- `return_value` reflects whatever users assign to `_` – this keeps the API simple but requires convention discipline.

## Change Log (critical fixes – Nov 2025)

- Removed `type`/`isinstance` from safe builtins and implemented a guarded importer.  
- Added request-level code validation + JSON-only context ingestion.  
- Added subprocess isolation, Linux enforcement, and semaphore-based concurrency limits.  
- Locked down CORS + introduced `X-Executor-Token` authentication.  
- Disabled sys.path injection + removed automatic HTTP tool generation to block lateral movement.  
- Updated documentation and configuration defaults to reflect the hardened posture.
