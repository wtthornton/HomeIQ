# Why tapps_validate_changed Hung (Aborted) – Analysis

**Date:** 2026-02-25  
**Context:** User reported `tapps_validate_changed` hanging; run returned "Error: Aborted." No re-run requested.

---

## What the tool does

- **Detects** changed Python files via `git diff` against `base_ref` (default `HEAD`).
- **For each** changed `.py` file: runs **score** + **quality gate** + **security scan** (Bandit, etc.).
- All work is done in a **single MCP request**; the tool returns only when every file has been processed.

---

## Observed runtimes (this repo)

From successful runs in the same session:

| Run   | Files validated | Elapsed (ms) | Elapsed (human) |
|-------|-----------------|--------------|------------------|
| 1     | 0               | 43,528       | ~44 s            |
| 2     | 0               | 115,929      | ~1 min 56 s      |
| 3     | 0               | 220,480      | ~3 min 40 s      |

So even with **no** changed Python files, the tool took **44 s to 3 m 40 s**. With **10** changed Python files (as of the analysis run), per-file work would add roughly **10 × (score + gate + security)** (often 20–40+ s per file), i.e. **several more minutes** total.

---

## Why it “hung” / was aborted

1. **Client or MCP timeout**
   - Many MCP clients use a **~60 s** request timeout.
   - `tapps_validate_changed` often exceeds 60 s (even with 0 files), so the client can abort with "Error: Aborted" or a timeout error (-32001).
   - TypeScript-based clients are documented to have a hard ~60 s limit that may not reset with progress.

2. **No progress updates**
   - If the TappsMCP server does **not** send progress notifications during the long run, the client has no signal that work is still ongoing and may treat the request as hung and abort.

3. **Inherently long-running**
   - Git diff + project discovery + N × (score + quality gate + security) is CPU- and I/O-heavy. On a repo with many or large Python files, total time can easily reach **3–7+ minutes**.

4. **User or IDE cancel**
   - "Aborted" can also mean the user or the IDE (e.g. Cursor) cancelled the tool call after waiting.

---

## Recommendations

- **Increase MCP timeout** for the TappsMCP server in Cursor/IDE config (e.g. 300000 ms / 5 minutes) so long validate runs can complete.
- **Prefer per-file checks when possible:** use `tapps_quick_check(file_path)` on individual changed files instead of `tapps_validate_changed()` when the batch call is unreliable or times out.
- **CI for batch validation:** use the existing GitHub Actions workflow (e.g. `tapps-mcp validate-changed --preset staging`) for full batch validation on PRs, where timeout limits are easier to tune.
- **Server-side:** if TappsMCP supports it, progress notifications every 5–10 s during `validate_changed` would help clients avoid treating the request as hung.

---

## References

- MCP timeout guide: [Fix MCP Error -32001: Request Timeout](https://mcpcat.io/guides/fixing-mcp-error-32001-request-timeout/)
- Project: `CLAUDE.md` (fallback: `tapps_quick_check` when `tapps_validate_changed` is unavailable)
- CI: `.github/workflows/tapps-quality.yml` (`tapps-mcp validate-changed --preset staging`)
