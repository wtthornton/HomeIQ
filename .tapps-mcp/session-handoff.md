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

## Next
Wave 9a (5311 → 5318 → 5312 → 5313 → 5319/5316 → 5314 → 5315 → 5317) per plan; then 9b (+6102 → 5322), 11a (5910 deletions = hard-stops, then 5303, 6103), 10, 11b (5299, 5301). Human-gated: 5430/6018 need Decision A (SSH write path); TAP-5978/5979 physical. Anytime: 6066.
