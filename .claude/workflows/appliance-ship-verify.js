export const meta = {
  name: 'appliance-ship-verify',
  description: 'Tier-matched independent verification of appliance-transformation VAL IDs',
  whenToUse: 'After any sub-goal of prompts/appliance-transformation-execute.md lands, to refute its VAL IDs with fresh-context verifiers tiered by proof shape.',
  phases: [{ title: 'Verify', detail: 'one fresh-context refuting verifier per VAL id' }],
}

// args: {
//   sha: string,                  // pinned commit — verifiers read via `git show <sha>:<path>`, never the working tree
//   sub_goal: string,             // label only, e.g. "SG8"
//   vals: [{
//     id: string,                 // "VAL-060"
//     shape: 'deterministic' | 'comparative' | 'semantic',
//     assertion: string,          // the contract row's claim
//     proof_cmd: string,          // the exact command(s) to run — never a narrative
//     expected: string,           // what the output must show
//     anchors: string,            // file:line hints + environment quirks (ports, container names, auth source)
//     correct_negative: string,   // '' or why an empty/negative result is a PASS (caps must not fire on correct behavior)
//   }]
// }
if (!args || !args.sha || !Array.isArray(args.vals) || args.vals.length === 0) {
  throw new Error('args must carry {sha, sub_goal, vals: [...]} — see the header comment')
}

const VERDICT = {
  type: 'object',
  required: ['id', 'verdict', 'observed_output', 'green_by_suppression', 'gaps'],
  properties: {
    id: { type: 'string' },
    verdict: { enum: ['PASS', 'FAIL', 'BLOCKED'] },
    observed_output: { type: 'string', minLength: 1 }, // empty = schema reject = FAIL by construction
    green_by_suppression: { type: 'boolean' },         // true when the proof passed because what it measures was removed/weakened
    gaps: { type: 'array', items: { type: 'string' } },
    commands_run: { type: 'array', items: { type: 'string' } },
  },
}

const TIER = {
  deterministic: { model: 'haiku', effort: 'low' },
  comparative: { model: 'sonnet', effort: 'medium' },
  semantic: { model: 'opus', effort: 'high' },
}

phase('Verify')
// Sized to the box (56 live containers): the per-workflow concurrency cap governs,
// and no verifier may rebuild or restart a container outside the throwaway
// test/appliance-profile fixtures its proof_cmd names.
const results = await parallel(args.vals.map(v => () => {
  const t = TIER[v.shape] || TIER.semantic
  return agent(
    `You are an independent verifier with a fresh context. REFUTE this claim; default to FAIL on any doubt.\n` +
    `Sub-goal: ${args.sub_goal} · VAL id: ${v.id} · pinned SHA: ${args.sha}\n` +
    `CLAIM: ${v.assertion}\n` +
    `PROOF COMMAND(S) — run these yourself, do not trust any prior narration:\n${v.proof_cmd}\n` +
    `EXPECTED: ${v.expected}\n` +
    `ANCHORS / ENVIRONMENT: ${v.anchors}\n` +
    (v.correct_negative ? `CORRECT-NEGATIVE RULE (a negative/empty result that matches this IS a PASS): ${v.correct_negative}\n` : '') +
    `Rules: read repo files via \`git show ${args.sha}:<path>\` or \`git grep <pattern> ${args.sha}\` — the working tree may be on another branch. ` +
    `Quote the output you actually observed into observed_output (verbatim, trimmed to the decisive lines). ` +
    `Grade the artifact, not the run: "the step completed" is not evidence. ` +
    `Set green_by_suppression=true if the proof passes only because the measured thing was deleted, skipped, or weakened (removed test, lowered severity, exit-code swallowed). ` +
    `You report gaps; you do not implement fixes. Never restart or rebuild containers except the throwaway fixtures your proof command names.`,
    { label: `verify:${v.id}`, phase: 'Verify', schema: VERDICT, model: t.model, effort: t.effort },
  )
}))

const verdicts = results.filter(Boolean)
const missing = args.vals.filter(v => !verdicts.some(r => r.id === v.id)).map(v => v.id)
const failed = verdicts.filter(r => r.verdict !== 'PASS' || r.green_by_suppression)
log(`${verdicts.length}/${args.vals.length} verdicts returned · ${failed.length} not green` +
    (missing.length ? ` · MISSING (agent died/skipped — treat as FAIL): ${missing.join(', ')}` : ''))

return {
  sub_goal: args.sub_goal,
  sha: args.sha,
  all_green: failed.length === 0 && missing.length === 0,
  verdicts,
  missing_treated_as_fail: missing,
}
