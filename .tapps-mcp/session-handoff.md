# Session Handoff — appliance-transformation-execute goal loop

Updated: 2026-09-09T06:11:44Z

## Goal
Execute prompts/appliance-transformation-execute.md: land 12 stories (TAP-6623,6622,6485,6486,6467,6468,6570,6573,6572,6620,6619,6621), each PR'd, independently verified, Done in Linear. Contract = 33 VAL IDs (prompt's 30 + VAL-021/042/064 added from Linear boxes).

## State (iteration 3, 2026-09-09)
- Pinned SHA 326f6cf16a91dcc5bc9d6b8f9bd55bbe70caa86e (origin/master).
- VAL-000 round 1 FAILED (3 refuted counts/anchors) — corrected below; round 2 re-verify dispatched. Cumulative: iter 3/36, ~420k-plus/2M tokens (L1 ran 2 rounds, $14.2, on TAP-6622), orch-spend ~4%.

## Baselines
- pytest: libs/homeiq-ha 431 passed; ha-setup-service 69 passed.
- Image homeiq/home-assistant:2026.8.3 present (b1382e453374).
- scan-all 33015707429: 62 HIGH/CRIT (47H/15C), mixed fixable.
- `${VAR:?}` distinct vars: 7 in domains/core-platform/compose.yml (file-scoped); 11 distinct repo-wide. POSTGRES_USER appears inside POSTGRES_URL (core-platform:69). `env.required` has 12 `required` keys incl. `ADMIN_API_JWT_SECRET` — no `JWT_SECRET_KEY` (ADR key-inventory fix landed).
- Budget 42 svc/7406 MiB, check-container-budget.py ratchets both ways.

## VAL-000 premise essentials (corrected after round-1 refutation)
- 6623: **Done** — PR #141 merged `30c55416`. `home-assistant-test` core-platform/compose.yml:742 now pins the shipped image, no longer :stable. `NOT production, deliberately` marks the appliance-only profile at core-platform/compose.yml:719-726. VAL-003 = sim suites >= baseline + VAL-002 healthy boot.
- 6622: **BLOCKED, not Done.** PR #146 (head `654ac255`) supersedes #142; verified green on all 36 first-party images; blocked on TAP-7250 (influxdb/pgvector major-upgrade decision, 41 ids); #142 still open. Sibling: TAP-6431 PR #145 (head `d54f9da0`) blocked on TAP-7241/TAP-7247.
- 6485 (In Progress): `SSHTarget` only, host_files.py:97-132, switch=`HOMEIQ_HA_SSH_HOST` (host_files.py:118-125). VAL-021 added (explicit backend selection, backup-on-overwrite, atomic, absent-vs-unreadable, config_yaml.py:251 + zha_quirks.py:167 raise sites APPLICABLE sans SSH).
- 6486 (In Progress): 3 SSH recipes — `HttpLoginThresholdRecipe` recipes.py:346, `RecorderTuningRecipe` recipes.py:347, `AqaraFP1EQuirkRecipe` recipes.py:385. `supervisor_api` in libs/homeiq-ha/src: 12 occurrences, 10 real call sites (answers.py:90,94,98,99; recipes.py:158,172,217,231; snapshot.py:144,303; plus def at client/ws.py:596 + docstring client/ws.py:8) — acceptance covers answers/snapshot sites too, not just recipes.py. `AqaraFP1EQuirkRecipe` recipes.py:339-404 holds 26 entries: 20 base + 6 manifest-gated.
- 6467/6468: wizard.py is queue builder; order = `PHASE_SAFETY` agent/recipe.py:35-40 phases + `sorted` agent/engine.py:123 sort; NO readiness gate exists today. Resized 2026-08-23 to owned-HA readiness. VAL-042 added (queue/audit/converge not-ready behavior). Anchors on routes_init.py (528 lines): `audit` routes_init.py:219-229, `queue` routes_init.py:384-406, `converge` routes_init.py:511-528.
- 6570: `HAOnboarder` agent/onboarding.py:145, `onboard` onboarding.py:258-284, zero prod callers (PR #131 TAP-6484 MERGED 2026-08-26). /auth/token form-encoded; LLAT websocket-only.
- 6573: tier-1 /var/lib/homeiq/.env root 0600; DEK=HOMEIQ_SECRET_DEK; failure states preflight-failure/SecretStoreUnsealed/SecretStoreUnavailable/`SecretNotProvisioned` (docs/architecture/adr-appliance-secret-store.md:129-134). VAL-064 added (log redaction).
- 6572: tier-2 core.appliance_secret AES-GCM under DEK; 2nd boot detects ALREADY_ONBOARDED but no stored cred.
- 6620: `appliance` profile only at core-platform/compose.yml:719-726; `--profile production` at start-stack.sh:110. CORRECTION: `af_publish.py` (af.sh:50-52) only delegates publish to the EXTERNAL AgentForge repo — genes-before-workflows ordering lives there, NOT in this repo; VAL-082 proof = boot-log publish order, not af.sh content.
- 6619: preflight-env.sh validates env.required (12 required keys); installer+pinned bundle per packaging ADR.
- 6621: NO bundle-upgrade mechanism exists; rollback.sh is service-level only. Upgrade = migration (HA config-key renames).

## SG order → VAL map
SG2 6623(001-003) → SG3 6622(010-012) → SG4 6485(020,021) → SG5 6486(030-032) → SG6 6467+6468 one PR(040-042) → SG7 6570(050-052) → SG8 6573(060-064) → SG9 6572(070) → SG10 6620(080-082) → SG11 6619(090-093) → SG12 6621(100-102) → SG13 lessons.

## Refuted strategies / corrections log
- VAL-000 r1: verifier refuted counts 13→12(10 calls) supervisor_api, 22→26 recipes, af.sh ordering claim; anchors 726→743, 103-135→97-132. Corrected above. Lesson candidate: subagent totals need a count convention stated with the number.

## Resume
Read prompts/appliance-transformation-execute.md in full, run the Prerequisites / Wayfind gate, then execute as goal loop until Done-when. Re-verify first: git rev-parse, gh pr list, per-story get_issue.
