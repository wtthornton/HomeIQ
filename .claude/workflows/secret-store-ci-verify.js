export const meta = {
  name: 'secret-store-ci-verify',
  description: 'Tier-matched independent verification of the secret-store / CI validation contract',
  whenToUse: 'After any sub-goal of prompts/secret-store-ci-and-harness-drain.md lands, to verify its VAL IDs with a fresh-context verifier per proof shape.',
  phases: [
    { title: 'Preflight', detail: 'four independent closed probes, haiku/low' },
    { title: 'Verify', detail: 'one fresh-context verifier per VAL, model+effort by proof shape' },
    { title: 'Adversarial', detail: 'refute the semantic claims, opus/xhigh' },
    { title: 'Synthesize', detail: 'single pass/fail roll-up' },
  ],
}

// ---------------------------------------------------------------------------
// Schemas — force structured returns so the orchestrator never parses prose.
// ---------------------------------------------------------------------------

const PROBE = {
  type: 'object',
  additionalProperties: false,
  required: ['probe', 'ok', 'observed'],
  properties: {
    probe: { type: 'string' },
    ok: { type: 'boolean' },
    observed: { type: 'string', description: 'Raw command output, verbatim. Not a summary.' },
  },
}

const VERDICT = {
  type: 'object',
  additionalProperties: false,
  required: ['val_id', 'verdict', 'observed_output', 'reasoning'],
  properties: {
    val_id: { type: 'string' },
    verdict: { enum: ['PASS', 'FAIL', 'INCONCLUSIVE'] },
    observed_output: {
      type: 'string',
      description: 'Verbatim output of the proof command actually run. Empty string is a FAIL.',
    },
    reasoning: { type: 'string' },
    green_by_suppression: {
      type: 'boolean',
      description: 'True if the proof appears satisfied by deleting/disabling what it measures.',
    },
  },
}

const REFUTATION = {
  type: 'object',
  additionalProperties: false,
  required: ['claim', 'refuted', 'evidence'],
  properties: {
    claim: { type: 'string' },
    refuted: { type: 'boolean' },
    evidence: { type: 'string' },
    severity: { enum: ['blocking', 'material', 'minor', 'none'] },
  },
}

// ---------------------------------------------------------------------------
// Contract. `sha` is passed in via args so verifiers read a pinned tree with
// `git show <sha>:<path>` instead of a working tree the orchestrator may move
// underneath them.
// ---------------------------------------------------------------------------

const SHA = (args && args.sha) || 'HEAD'
const ONLY = (args && args.only) || null // e.g. ["VAL-001","VAL-002"] to verify one sub-goal

const REPO = '/home/wtthornton/code/HomeIQ'

const PIN = `
You are verifying a PINNED tree at commit ${SHA}. Read files with
\`git show ${SHA}:<path>\` or \`git grep <pattern> ${SHA}\` — do NOT read the working
tree, which may be on a different branch. Working directory: ${REPO}.

Your job is to REFUTE the claim, not confirm it. Default to FAIL on any doubt.
Run the proof command yourself and quote its output verbatim in observed_output.
A verdict with an empty observed_output is itself a FAIL — narration is not evidence.
`

// Proof shape drives model + effort. Deterministic proofs are settled by an exit
// code, so haiku re-running the command is strictly better value than opus
// reasoning about it. Semantic proofs get opus, and MORE effort than a uniform
// pass would have afforded them.
const CONTRACT = [
  {
    id: 'VAL-001',
    shape: 'deterministic',
    model: 'haiku',
    effort: 'low',
    claim: 'With no developer .env present, `docker compose config -q` exits 0 and resolves 39 services.',
    proof: [
      `cd ${REPO}`,
      'mv .env .env.verify-hidden 2>/dev/null || true',
      'docker compose --env-file .env.ci config -q; echo "EXIT=$?"',
      'docker compose --env-file .env.ci config --services | wc -l',
      'mv .env.verify-hidden .env 2>/dev/null || true',
    ].join(' && '),
    expect: 'EXIT=0 and a service count of exactly 39. Restore .env even if the check fails.',
  },
  {
    id: 'VAL-002',
    shape: 'deterministic',
    model: 'haiku',
    effort: 'low',
    claim: 'Security Scan All Services reaches its Trivy step on a workflow_dispatch run.',
    proof:
      'gh run list --workflow=docker-security-scan.yml --branch master --limit 5 --json databaseId,event,conclusion' +
      ' then: gh api repos/wtthornton/HomeIQ/actions/runs/<id>/jobs ' +
      `-q '.jobs[]|select(.name=="Security Scan All Services")|{name,steps:[.steps[]|{name,conclusion}]}'`,
    expect:
      'A run with event=workflow_dispatch whose "Scan all images with Trivy" step has a conclusion that is NOT "skipped". ' +
      'The presence of the "Security Scan All Services" job identifies a cron/dispatch run; its absence means you are looking at a PR run — reject that as wrong evidence.',
  },
  {
    id: 'VAL-003',
    shape: 'deterministic',
    model: 'haiku',
    effort: 'low',
    claim: "scan-all Trivy exit-code is not '0' and the scan-images matrix still lists 11 services.",
    proof:
      `git show ${SHA}:.github/workflows/docker-security-scan.yml | grep -n "exit-code" ; ` +
      `git show ${SHA}:.github/workflows/docker-security-scan.yml | sed -n '/matrix:/,/steps:/p' | grep -c "^ *- "`,
    expect:
      "exit-code is '1' (or absent, which defaults to failing). Matrix service count is exactly 11. " +
      'Set green_by_suppression=true if the count dropped or severity was downgraded.',
  },
  {
    id: 'VAL-004',
    shape: 'deterministic',
    model: 'haiku',
    effort: 'low',
    claim: 'Two AuthManager instances built from the same configuration verify each other tokens.',
    proof: `cd ${REPO} && uv run python -m pytest libs/homeiq-data/tests/test_auth.py -q 2>&1 | tail -20`,
    expect:
      'A test exists that constructs two AuthManager instances and cross-verifies a token, and it passes. ' +
      'If no such test is collected, that is a FAIL regardless of the suite being green.',
  },
  {
    id: 'VAL-005',
    shape: 'semantic',
    model: 'opus',
    effort: 'high',
    claim:
      'Absent signing-key configuration is a NAMED startup failure, not a silent random default.',
    proof:
      `git show ${SHA}:libs/homeiq-data/src/homeiq_data/auth.py | sed -n '55,90p'` +
      ` ; git grep -n "token_urlsafe" ${SHA} -- libs/homeiq-data`,
    expect:
      'The `os.getenv("ADMIN_API_JWT_SECRET") or secrets.token_urlsafe(32)` fallback is GONE, replaced by an ' +
      'explicit named failure. Judge the SEMANTICS: a fallback that merely moved (to a config layer, a default ' +
      'argument, or a helper) is NOT removed. A raised exception with a generic message is weaker than a named ' +
      'state — say so. Set green_by_suppression=true if the check was satisfied by deleting the assertion rather ' +
      'than fixing the behaviour.',
  },
  {
    id: 'VAL-006',
    shape: 'comparative',
    model: 'sonnet',
    effort: 'medium',
    claim:
      'env.required documents the variable the code actually reads, and its description matches compose enforcement.',
    proof:
      `git show ${SHA}:env.required | grep -n -i "jwt" ; ` +
      `git show ${SHA}:domains/core-platform/compose.yml | grep -n "JWT" ; ` +
      `git grep -n "ADMIN_API_JWT_SECRET" ${SHA}`,
    expect:
      'Hold three states side by side: what env.required claims, what compose enforces, and what Python actually ' +
      'reads. They must agree. The prior defect was env.required:46 describing a conditional requirement and a ' +
      '"committed placeholder" — both false. If either half is still wrong, FAIL.',
  },
  {
    id: 'VAL-007',
    shape: 'deterministic',
    model: 'haiku',
    effort: 'low',
    claim: 'No regression: the homeiq-ha suite still reports at least 431 passed.',
    proof: `cd ${REPO} && uv run python -m pytest libs/homeiq-ha/tests/ -q 2>&1 | tail -5`,
    expect:
      'A summary line with >= 431 passed. A LOWER number is a FAIL even if nothing errors — that is the ' +
      'no-green-by-deletion clause. Report the exact number you saw.',
  },
]

// ---------------------------------------------------------------------------

const selected = ONLY ? CONTRACT.filter((c) => ONLY.includes(c.id)) : CONTRACT

log(`Verifying ${selected.length} VAL ids at ${SHA} — tiers: ` +
  selected.map((c) => `${c.id}:${c.model}/${c.effort}`).join(' '))

// --- Phase 1: preflight, four independent closed probes in parallel ---------
phase('Preflight')

const probes = await parallel([
  () => agent(`${PIN}\nProbe: is the GitHub CLI authenticated? Run \`gh auth status\` and report verbatim.`,
    { label: 'probe:gh-auth', phase: 'Preflight', schema: PROBE, agentType: 'Explore', model: 'haiku', effort: 'low' }),
  () => agent(`${PIN}\nProbe: what Docker Compose version is installed? Run \`docker compose version\`. This matters because env_file schema support differs by version.`,
    { label: 'probe:compose-version', phase: 'Preflight', schema: PROBE, agentType: 'Explore', model: 'haiku', effort: 'low' }),
  () => agent(`${PIN}\nProbe: is ${SHA} an ancestor of origin/master? Run \`git merge-base --is-ancestor ${SHA} origin/master; echo "EXIT=$?"\`.`,
    { label: 'probe:git-base', phase: 'Preflight', schema: PROBE, agentType: 'Explore', model: 'haiku', effort: 'low' }),
  () => agent(`${PIN}\nProbe: does a committed .env.ci exist at ${SHA}, and which variable names does it define? Run \`git show ${SHA}:.env.ci | grep -oE '^[A-Z_]+' | sort\`. Compare against the 7 names carrying :?required.`,
    { label: 'probe:env-ci', phase: 'Preflight', schema: PROBE, agentType: 'Explore', model: 'haiku', effort: 'low' }),
])

const probeFails = probes.filter(Boolean).filter((p) => !p.ok)
if (probeFails.length) {
  log(`Preflight probes failed: ${probeFails.map((p) => p.probe).join(', ')} — verifying anyway, but treat results as suspect.`)
}

// --- Phase 2: one fresh-context verifier per VAL, tiered by proof shape -----
phase('Verify')

const verdicts = await parallel(
  selected.map((c) => () =>
    agent(
      `${PIN}

CLAIM UNDER TEST (${c.id}, proof shape: ${c.shape}):
${c.claim}

PROOF COMMAND — run this, do not reason about it:
${c.proof}

WHAT WOULD MAKE THIS PASS:
${c.expect}

Return the verdict with observed_output containing the VERBATIM command output.`,
      {
        label: `verify:${c.id}`,
        phase: 'Verify',
        schema: VERDICT,
        agentType: 'general-purpose',
        model: c.model,
        effort: c.effort,
      },
    ),
  ),
)

const clean = verdicts.filter(Boolean)

// --- Phase 3: adversarial pass on the semantic claims only ------------------
// Named targets, because "refute this specific claim" investigates where
// "check this" merely agrees.
phase('Adversarial')

const adversarial = await parallel([
  () => agent(
    `${PIN}

Refute this specific claim, hard:

  "Removing the \`or secrets.token_urlsafe(32)\` fallback from auth.py:69 cannot break
   a running deployment."

Look for: callers that construct AuthManager without the env var set; test fixtures
that relied on the implicit random key; any container in domains/core-platform that
would now fail startup where it previously ran. Read
\`git show ${SHA}:libs/homeiq-data/src/homeiq_data/auth.py\` and
\`git grep -n "AuthManager" ${SHA}\`.

If it CAN break something, that is a real finding — say so with the file:line.`,
    { label: 'refute:fallback-safety', phase: 'Adversarial', schema: REFUTATION, agentType: 'general-purpose', model: 'opus', effort: 'xhigh' }),

  () => agent(
    `${PIN}

Refute this specific claim, hard:

  "The committed .env.ci placeholder resolves compose on the RUNNER, not merely on the
   developer machine."

The local Compose is v5.1.1; the GitHub runner's version was NOT verified. Check whether
the workflow echoes \`docker compose version\`, whether \`--env-file\` composes correctly
with \`include:\` entries that each declare their own env_file, and whether .env.ci's
variable set still matches the current \`:?required\` set (it was 7 names on 2026-08-26,
including JWT_SECRET_KEY — which sub-goal 3 may have removed).

A drifted .env.ci fails SILENTLY: green locally, dead on the runner. That is the
failure mode to hunt.`,
    { label: 'refute:runner-parity', phase: 'Adversarial', schema: REFUTATION, agentType: 'general-purpose', model: 'opus', effort: 'xhigh' }),
])

// --- Phase 4: roll-up -------------------------------------------------------
phase('Synthesize')

const failed = clean.filter((v) => v.verdict !== 'PASS')
const suppressed = clean.filter((v) => v.green_by_suppression)
const refutations = adversarial.filter(Boolean).filter((r) => r.refuted)

log(`RESULT — ${clean.filter((v) => v.verdict === 'PASS').length}/${selected.length} PASS · ` +
  `${failed.length} not-pass · ${suppressed.length} suppression-flagged · ${refutations.length} refuted`)

return {
  sha: SHA,
  probes: probes.filter(Boolean),
  verdicts: clean,
  adversarial: adversarial.filter(Boolean),
  all_pass: failed.length === 0 && suppressed.length === 0 && refutations.length === 0,
  blocking: [
    ...failed.map((v) => `${v.val_id}: ${v.verdict}`),
    ...suppressed.map((v) => `${v.val_id}: green-by-suppression flagged`),
    ...refutations.map((r) => `refuted: ${r.claim} (${r.severity})`),
  ],
  tokens_spent: budget.spent(),
}
