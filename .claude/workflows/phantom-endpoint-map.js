export const meta = {
  name: 'phantom-endpoint-map',
  description: 'Resolve the 9 phantom dashboard endpoints against real OpenAPI routes, then adversarially verify each mapping',
  whenToUse: 'Sub-goal 4 of prompts/close-ha-and-dashboard-epics.md — mapping frontend paths that exist on no backend',
  phases: [
    { title: 'Resolve', detail: 'match each phantom path to a real route from openapi.json' },
    { title: 'Verify', detail: 'refute each proposed mapping by calling the candidate route' },
  ],
}

// The 9 paths the shipped bundle calls that return 404 on BOTH backends.
// Source: docs/operations/dashboard-triage-2026-08-01.md
const PHANTOMS = [
  '/api/v1/services',
  '/api/v1/configuration',
  '/api/v1/memory/status',
  '/api/v1/integrations',
  '/api/v1/health/integrations',
  '/api/statistics',
  '/api/v1/rag/status',
  '/api/v1/sports',
  '/api/v1/data-sources',
  '/api/v1/ha/status',
]

const MAPPING = {
  type: 'object',
  required: ['phantom_path', 'verdict'],
  properties: {
    phantom_path: { type: 'string' },
    verdict: { enum: ['MAPPED', 'NO_MATCH_BUILD', 'NO_MATCH_DROP_PANEL'] },
    real_path: { type: 'string', description: 'exact path from openapi.json, empty if no match' },
    owning_service: { type: 'string' },
    owning_port: { type: 'string' },
    evidence: { type: 'string', description: 'how it was confirmed present in openapi.json' },
    caller_files: { type: 'array', items: { type: 'string' }, description: 'frontend file:line calling the phantom path' },
  },
}

const VERDICT = {
  type: 'object',
  required: ['phantom_path', 'confirmed', 'reason'],
  properties: {
    phantom_path: { type: 'string' },
    confirmed: { type: 'boolean' },
    observed_status: { type: 'string' },
    reason: { type: 'string' },
  },
}

const PORTS = 'admin-api is published on host port 18004, data-api on 8006, dashboard on 13000 (host-port overrides are in effect on this box; do NOT assume 8004/3000). admin-api rate-limits at 60 req/min burst 20 — pace any sweep.'

log(`Resolving ${PHANTOMS.length} phantom endpoints`)

const results = await pipeline(
  PHANTOMS,

  // Stage 1 — cheap, read-only: find the real route in the authoritative OpenAPI docs.
  (path) =>
    agent(
      `Repo /home/wtthornton/code/HomeIQ. READ-ONLY: make no edits.

The health-dashboard frontend calls "${path}". It returns 404 through nginx AND 404 when
called directly against both backends, so the route does not exist under that name.

Find what it SHOULD call. ${PORTS}

1. Fetch both authoritative route lists:
   curl -s -H "Authorization: Bearer $DATA_API_KEY" http://localhost:18004/openapi.json | jq -r '.paths | keys[]'
   curl -s -H "Authorization: Bearer $DATA_API_KEY" http://localhost:8006/openapi.json  | jq -r '.paths | keys[]'
   (read the key from the repo .env — it is gitignored; never print it)
2. Find the best real match for "${path}". Match on the RESPONSE SHAPE the frontend consumes,
   not just a similar-looking path — grep the frontend for the call site and read what fields
   it destructures.
3. Report caller file:line from domains/core-platform/health-dashboard/src/.

Do NOT guess. If nothing in either openapi.json plausibly serves the same data, say so and
choose NO_MATCH_BUILD (the data exists elsewhere and an endpoint should be built) or
NO_MATCH_DROP_PANEL (the data does not exist anywhere; the panel should be removed).`,
      { label: `resolve:${path}`, phase: 'Resolve', schema: MAPPING, effort: 'low' }
    ),

  // Stage 2 — frontier: adversarially verify the proposed mapping by actually calling it.
  (mapping, path) => {
    if (!mapping) return null
    if (mapping.verdict !== 'MAPPED') return { mapping, verdict: null }
    return agent(
      `Repo /home/wtthornton/code/HomeIQ. READ-ONLY: make no edits.

A prior agent claims the frontend path "${mapping.phantom_path}" should map to
"${mapping.real_path}" on ${mapping.owning_service}.

Your job is to REFUTE this. Default to confirmed=false on any doubt.

${PORTS}

1. Actually call the candidate route with a Bearer token from the repo .env and record the status.
2. Confirm the response shape genuinely contains the fields the frontend consumes — read the
   caller at ${(mapping.caller_files || []).join(', ')} and check every destructured field exists.
3. A 200 with the wrong shape is a FAILED mapping — the panel would render blank or crash.
4. Consider whether a different route is a better match.

Only confirm if the route returns non-error AND the shape actually satisfies the caller.`,
      { label: `verify:${path}`, phase: 'Verify', schema: VERDICT, effort: 'high' }
    ).then((v) => ({ mapping, verdict: v }))
  }
)

const clean = results.filter(Boolean)
const confirmed = clean.filter((r) => r.verdict?.confirmed)
const refuted = clean.filter((r) => r.mapping?.verdict === 'MAPPED' && r.verdict && !r.verdict.confirmed)
const unmatched = clean.filter((r) => r.mapping && r.mapping.verdict !== 'MAPPED')

log(`confirmed ${confirmed.length} · refuted ${refuted.length} · unmatched ${unmatched.length}`)

return {
  confirmed: confirmed.map((r) => ({
    phantom: r.mapping.phantom_path,
    real: r.mapping.real_path,
    service: r.mapping.owning_service,
    callers: r.mapping.caller_files,
    observed: r.verdict.observed_status,
  })),
  refuted: refuted.map((r) => ({
    phantom: r.mapping.phantom_path,
    rejected_candidate: r.mapping.real_path,
    why: r.verdict.reason,
  })),
  needs_decision: unmatched.map((r) => ({
    phantom: r.mapping.phantom_path,
    verdict: r.mapping.verdict,
    evidence: r.mapping.evidence,
  })),
  note: 'refuted entries must be re-resolved before any caller is repointed; needs_decision entries are build-or-drop product calls',
}
