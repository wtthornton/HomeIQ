# tapps-mcp defects observed from a long HomeIQ session (2026-08-02)

Paste this into a session in the **tapps-mcp** repo.

---

Four defects and one docs mismatch, all observed while driving tapps-mcp hard for
~8 hours from a consuming project (HomeIQ). Each has a reproduction. Please fix
in priority order; #1 is the one that can silently corrupt a quality decision.

## 1. `tapps_quick_check` cache is keyed on content only, but the score depends on path

**Severity: high.** The cache returns another file's score, and the score is
genuinely different for the requested file.

Reproduction, run from a project root that has `AGENTS.md`:

```bash
printf 'def f(x):\n    """Doc."""\n    return x + 1\n' > probe_a.py
mkdir -p domains/core-platform/admin-api/src/_probe
cp probe_a.py domains/core-platform/admin-api/src/_probe/probe_b.py
# identical content, different depth
```

Then:

```
tapps_quick_check(file_path="probe_a.py")
  -> file_path: ".../probe_a.py"   devex: 10   overall: 82.97   cache_hit: false

tapps_quick_check(file_path="domains/core-platform/admin-api/src/_probe/probe_b.py")
  -> file_path: ".../probe_a.py"   devex: 10   overall: 82.97   cache_hit: true
```

The second call returns the **first file's path** in its own response, and
inherits its `devex: 10`.

That value is wrong for `probe_b.py`. `devex` (and `structure`) are computed from
directory context — proximity to `AGENTS.md`, `pyproject.toml`, `tests/`. A file
five levels down in `domains/<domain>/<service>/src/` scores `devex: 0`. Verified
independently: `domains/device-management/device-setup-assistant/src/main.py`,
untouched, scores `devex: 0, overall 69.56, gate FAILED`.

So the same content is legitimately 82.97/pass at the root and ~69/fail inside a
service, and the cache hands out whichever was computed first.

**Why this matters beyond a wrong number.** The natural way to check "did my edit
regress this file?" is to score a pristine copy and compare. That is exactly what
triggers this: same content, two paths. I hit it doing precisely that, and it
silently gave me a baseline that was ~4 points too high because the copy sat at
the repo root next to `AGENTS.md`. I nearly reported a regression that did not
exist.

**Fix:** include the resolved absolute path (or at least the directory) in the
cache key. Returning a `file_path` that differs from the requested one should
probably also be an assertion failure in tests.

## 2. `tapps_quick_check` and `tapps_validate_changed` disagree on gate outcome for the same file

**Severity: high** — two tools in the same pipeline give opposite pass/fail
verdicts for one unmodified file, in the same session, minutes apart.

```
tapps_quick_check(file_path="domains/core-platform/admin-api/src/memory_endpoints.py")
  -> overall_score: 66.52   gate_passed: false
     categories_scored: [complexity, security, maintainability, test_coverage,
                         performance, structure, devex, linting]

tapps_validate_changed(file_paths="...same file...")
  -> score: 85   gate_passed: true
     categories_scored: ["linting"]
```

`validate_changed` in quick mode scores **linting only** and then reports a
number on the same 0-100 scale, with a `gate_passed` boolean, as if it were
comparable. It is not.

This is worse than a cosmetic inconsistency, because `validate_changed` is the
documented pre-completion gate. An agent that runs only the documented final step
gets `all_gates_passed: true` for a file that `quick_check` fails.

**Fix options, any of which resolves it:** have `validate_changed` score the same
category set; or namespace the score (`lint_score`) so it cannot be mistaken for
`overall_score`; or make `gate_passed` in a reduced-category run report
`gate_passed: null` / `"partial"` rather than `true`.

## 3. `-32000 Connection closed` on larger tool payloads

**Severity: medium**, intermittent, recovers on retry.

Three occurrences, all on calls carrying a large-ish string argument:

- `tapps_lookup_docs(library="fastapi", topic="path operation ordering fixed paths before path parameters")` -> `MCP error -32000: Connection closed`. Immediate retry with a shorter topic succeeded.
- `tapps_memory(action="save", value=<~1500 chars>)` -> same error, twice, on two different keys. Both succeeded on retry with the value shortened by roughly a third.

No pattern other than payload size. Worth checking for a stdio frame-size or
write-timeout limit in the transport.

## 4. `path_denied` blocks the standard baseline-comparison workflow

**Severity: low, but it forces a worse workaround.**

```
tapps_quick_check(file_path="/tmp/claude-.../base/issue_detector.py")
  -> path_denied: "Path outside project root"
```

Refusing arbitrary filesystem reads is right. But the common, legitimate use is
"score the HEAD version of this file to compare against my edit," and the natural
place for that copy is a temp dir.

Because it is refused, the workaround is to write the baseline copy **inside the
repo** — which is both dirtier and, thanks to defect #1, silently wrong if placed
at a different depth than the original.

**Fix suggestions:** allow reads under the session temp dir; or add a
`tapps_score_ref(file_path, ref="HEAD")` that resolves the blob from git itself,
which sidesteps both the path restriction and the cache-key bug.

## 5. Docs mismatch: `tapps_memory` advertises 44 actions, the deployed profile exposes 5

`CLAUDE.md` (generated by `tapps_init`/`tapps_upgrade`) says:

> `tapps_memory` provides persistent cross-session knowledge with **44 actions**
> (save, search, consolidate, federation, profiles, hive, health, knowledge
> graph, batch ops, feedback, native session memory, and more).

The actual error from the deployed slim profile:

```
tapps_memory(action="delete", key="...")
  -> action_not_on_nlt_memory:
     "Action 'delete' is not on the nlt-memory slim profile.
      Allowed: get, health, related, save, search"
```

Five actions, not 44. Notably there is **no `delete`**, so an agent that writes a
throwaway or incorrect entry cannot remove it — the only recourse is overwriting
it with a tombstone.

**Fix:** make the generated `CLAUDE.md` describe the profile actually deployed,
and consider adding `delete` to the slim profile since write-without-delete is an
awkward contract.

---

## Note

There is a separate, more serious defect in the memory backend — architectural
and pattern tier writes return success and do not persist. That one is written up
for the **tapps-brain** repo, not here, though the fix may involve the bridge on
this side. It is tracked as TAP-5442 in the HomeIQ project.
