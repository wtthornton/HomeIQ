# Session handoff
**Updated:** 2026-08-18T04:00Z
**Git:** branch feat/wave8-mcp-server (8 commits ahead of master; PR #87 open). PR #83 MERGED 2026-08-18 (owner-approved).
**Plan:** docs/planning/backlog-implementation-plan-2026-08-17.md (owner approved Decisions A–E; A/C are owner actions still open)

## Done this session
- Phase 0: PR #83 rebased+merged; Linear triage — 5302/5300/5298 canceled as dups of 5910 (comments), TAP-6102 (ai-automation-service-new → AF genes, gates 5322) and TAP-6103 (domain CI red) filed; decisions on 5322/6018/5295/5283; drain prompt table synced.
- Wave 8 on branch: TAP-6071 (route un-shadow), TAP-5293 (server), TAP-5294/5295 (15 tools), TAP-5297 (34 contract tests, gene map, CI dev-deps), TAP-5296 (AF project overlay registry v1 active; probe gene published; live invocations 99cf5797/106d4e53 mcp_hosts=[homeiq]).
- Upstream fixes found by live calls: data-api events pivot (states no longer null), ingestion stores bare state, carbon 404, homeiq-data search_path autocommit (device-intelligence 500 fixed), device-intelligence X-API-Key. Redeployed: data-api, websocket-ingestion, device-intelligence, homeiq-mcp (:8050).
- .env additions (values not shown): HOMEIQ_MCP_READ_TOKENS, HOMEIQ_MCP_ALLOWED_HOSTS (incl. AF gateway 172.20.0.1). AF vault: project:homeiq secret HOMEIQ_MCP_AUTHORIZATION.

## Wave 8 CLOSED (2026-08-18)
- 3-round opus refute panel: rounds 1-2 produced ~28 findings, all fixed (commits 13499ca2, bd8b01a0, 5fab8956); round 3 PASS. PR #87 MERGED to master (45645304).
- Linear: TAP-5282 epic + 6071/5293/5294/5295/5296/5297 all Done with evidence comments. TAP-6107 filed (context_parent_id never ingested -> trace chains empty; catalogue v1.2.3 carries the caveat).
- Live: homeiq-mcp :8050 on AF gateway bind (HOMEIQ_MCP_BIND=172.20.0.1), catalogue 1.2.3, read_only rootfs, minimal env; AF registry v1 active with vault auth; probe gene v2 least-privilege ran live.
- AF-side oddity (recorded on 5296): invocation ledger says is_error=true/num_turns=0 while CLI result is success — AF bug, not ours.

## Wave 9a DONE on branch feat/wave9-genome (pushed)
- 5311 fork+drift+CI (genome-kit.yml), 5312 8 base genes rendered, 5318 publish pipeline (af_kit/af_live_diff/af_roundtrip_check/af_preflight/af_suite_run), 5313 injection judge, 5316+5319 five skills (deny list SAFETY001-006), 5314 draft+judge genes, 5315 five analysis genes with least-privilege MCP grants, 5317 four chromosomes published+ACTIVE (home-health, automation-proposal w/ human gate, energy-digest, anomaly-triage event+schedule).
- Kit: 23 agents, 7 workflows, 11 skills publishable; 150 kit tests; drift clean; 30/30 live match; round-trip fields + AF version pin OK.
- Wave 9 Done-when evidence LIVE: deny refusal (8e905a10, rule_id deny.unlock_lock) + budget hold (d376d401, error_max_budget_usd). Probe reverted to v4 (0.3 cap) and re-activated.
- AF platform notes: transform sandbox = no comprehensions/any()/methods; gate payload_from = $refs only; orchestrated runs don't materialize run objects on this deployment (api replica enqueues only) — recorded on 5323.

## Wave 9 shipped (PR #88 open, branch feat/wave9-genome, 5 commits)
- Epic TAP-5285 Done + 5311/5312/5313/5314/5315/5316/5317/5318/5319/5320/5325 Done. 5321 + 5323 left In Progress: both need AF instance env (AF_MONTHLY_BUDGET_USD / plan ceiling) = OWNER action; per-gene budgets + the budget-kill proof are done.
- Live: 23 agents + 7 workflows active on project homeiq; af_live_diff 30/30; deny refusal 8e905a10; budget kill d376d401.

## Next (needs owner input before proceeding)
1. Merge PR #88 (Wave 9) — owner gate on merges.
2. **Wave 11a (TAP-5910) is 15 service DELETIONS — every one an Autonomy hard-stop.** Needs explicit go-ahead; each deletion carries a pasted capability-reachability proof.
3. TAP-6102 cutover (ai-automation-service-new -> AF genes) is now unblocked (5314/5318 done) -> then 5322 credential move; rotation is owner-gated.
4. Wave 10 (5305-5310) installs a custom integration on the LIVE HA instance = apply, gateway path or hard-stop.
5. Owner batch: AF_MONTHLY_BUDGET_USD; SSH write path (5430/6018); credential rotation (6036/5993).
