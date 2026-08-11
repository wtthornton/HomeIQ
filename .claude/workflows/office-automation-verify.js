export const meta = {
  name: 'office-automation-verify',
  description: 'Behavioral verification of the Office presence-lighting automation, each assertion independently refuted',
  whenToUse: 'Runs SG7 of prompts/ha-office-presence-lighting.md, after SG6 deploys the automation through HomeIQ. This is the one multi-stage parallel chunk in that prompt, and the only place per-stage effort can be set.',
  phases: [
    { title: 'Observe', detail: 'drive the presence entity and record real state transitions' },
    { title: 'Refute', detail: 'fresh-context adversary tries to break each claim', model: 'opus' },
    { title: 'Synthesize', detail: 'VAL coverage verdict' },
  ],
}

// Behavioral assertions from the prompt's validation contract. Each is observed
// once against the LIVE instance, then handed to an adversary that did not make
// the observation. Creator != verifier is the whole point; an observer that
// grades its own transcript will rationalize a near-miss into a pass.
const ASSERTIONS = [
  {
    id: 'VAL-018',
    title: 'entry turns lights on',
    observe:
      'Record every `light.*` state first. Drive one `role:presence` entity to `on`. ' +
      'Poll `light.office` every second for 15 s. Report the exact `last_changed` before ' +
      'and after, and the elapsed seconds to reach state `on`. PASS requires on within 5 s.',
  },
  {
    id: 'VAL-019',
    title: 'exit turns lights off at 300s',
    observe:
      'With lights on, drive ALL `role:presence` entities to `off` and record that instant. ' +
      'Poll `light.office` every 10 s for up to 400 s. Report the elapsed seconds to reach ' +
      '`off`. PASS requires 300 s +/- 30 s. Do NOT shorten the automation `for:` delay to ' +
      'speed this up — a timing assertion proven against a shortened delay proves nothing, ' +
      'and editing the artifact under test is green-by-suppression. Wait the real time.',
  },
  {
    id: 'VAL-020',
    title: 'one occupied sensor holds lights on',
    observe:
      'Requires two `role:presence` entities. Drive both `on`, then clear only ONE. Poll ' +
      '`light.office` every 15 s for 330 s. PASS requires the light to remain `on` for the ' +
      'entire window. Any transition to `off` is a FAIL — it proves first-sensor-wins ' +
      'rather than genuine all-clear fusion.',
  },
  {
    id: 'VAL-021',
    title: 'no collateral light changes',
    observe:
      'Compare before/after states for all 7 `light.*` entities across the tests above. ' +
      'PASS requires every light except `light.office` to have an unchanged `last_changed`.',
  },
]

const HOW_TO_REACH_HA = `
Home Assistant: http://192.168.1.80:8123
Token (never print it, pipe it):
  TOK=$(docker inspect homeiq-websocket --format '{{range .Config.Env}}{{println .}}{{end}}' | grep '^HOME_ASSISTANT_TOKEN=' | cut -d= -f2-)
  curl -s -H "Authorization: Bearer $TOK" http://192.168.1.80:8123/api/states
Drive a proxy presence entity with the input_boolean.turn_on / turn_off services;
drive a real binary_sensor by its own means (do not fake its state via the API if it
is a real device — say so and mark the assertion BLOCKED instead).
`

const OBSERVATION = {
  type: 'object',
  required: ['id', 'verdict', 'evidence'],
  properties: {
    id: { type: 'string' },
    verdict: { enum: ['PASS', 'FAIL', 'BLOCKED'] },
    elapsed_seconds: { type: ['number', 'null'] },
    evidence: { type: 'string', description: 'Raw timestamped states observed. Not a summary.' },
    notes: { type: 'string' },
  },
}

const REFUTATION = {
  type: 'object',
  required: ['id', 'refuted', 'reason'],
  properties: {
    id: { type: 'string' },
    refuted: { type: 'boolean', description: 'true = the original PASS does not hold' },
    reason: { type: 'string' },
    recheck_evidence: { type: 'string', description: 'What the refuter re-ran itself' },
  },
}

phase('Observe')
log(`Verifying ${ASSERTIONS.length} behavioral assertions against the live instance`)

// Pipeline, not a barrier: VAL-019 alone burns ~5 real minutes of wall clock, so a
// fast assertion must not sit waiting on it. Each assertion flows straight from its
// own observation into its own refutation.
const results = await pipeline(
  ASSERTIONS,
  (a) =>
    agent(
      `Observe this assertion against the LIVE Home Assistant instance and report what actually happened.\n\n` +
        `Assertion ${a.id} — ${a.title}\n\n${a.observe}\n${HOW_TO_REACH_HA}\n` +
        `Report raw timestamped observations, not conclusions. If you cannot run the test ` +
        `(entity missing, service unreachable), return BLOCKED with the reason — do not guess.`,
      { label: `observe:${a.id}`, phase: 'Observe', schema: OBSERVATION, model: 'sonnet', effort: 'medium' },
    ),

  // Two adversaries per assertion, different angles. A single refuter agrees with a
  // plausible-looking transcript too often.
  (obs, a) =>
    obs == null
      ? null
      : parallel(
          [
            {
              lens: 'timing',
              ask: 'Re-run the timing measurement yourself. Was the threshold actually met, or was it rounded, estimated, or inferred from a poll interval too coarse to prove it?',
            },
            {
              lens: 'causation',
              ask: 'Did the automation cause this transition, or did something else (a manual call, another automation, a WLED preset, a coincidental state push)? Prove the automation fired — check its `last_triggered`.',
            },
          ].map(
            (l) => () =>
              agent(
                `You are refuting a claim about a live system. Default to refuted=true if uncertain.\n\n` +
                  `Assertion ${a.id} — ${a.title}\n` +
                  `Claimed verdict: ${obs.verdict}${obs.elapsed_seconds != null ? ` (${obs.elapsed_seconds}s)` : ''}\n` +
                  `Evidence offered:\n${obs.evidence}\n\n` +
                  `Your lens: ${l.lens}. ${l.ask}\n${HOW_TO_REACH_HA}\n` +
                  `Re-run the check yourself. Do not trust the transcript above.`,
                {
                  label: `refute:${a.id}:${l.lens}`,
                  phase: 'Refute',
                  schema: REFUTATION,
                  model: 'opus',
                  effort: 'xhigh',
                },
              ),
          ),
        ).then((votes) => {
          const live = votes.filter(Boolean)
          const refuted = live.filter((v) => v.refuted)
          return {
            ...obs,
            // A claimed PASS survives only if NO adversary refuted it. This is
            // deliberately stricter than majority: these assertions gate a change to
            // a live home, where a false PASS is worse than a re-run.
            final: obs.verdict === 'PASS' && refuted.length === 0 ? 'PASS' : obs.verdict === 'PASS' ? 'REFUTED' : obs.verdict,
            refutations: refuted.map((v) => `[${v.reason}]`),
            adversaries_run: live.length,
          }
        }),
)

phase('Synthesize')

const settled = results.filter(Boolean)
const green = settled.filter((r) => r.final === 'PASS')
const bad = settled.filter((r) => r.final !== 'PASS')

// Surface anything the pipeline dropped rather than letting a silent null read as
// coverage. An assertion that never ran is not an assertion that passed.
const missing = ASSERTIONS.filter((a) => !settled.some((r) => r.id === a.id)).map((a) => a.id)
if (missing.length) log(`WARNING — no result returned for: ${missing.join(', ')}`)

log(`VAL coverage: ${green.length}/${ASSERTIONS.length} green | not green: ${bad.map((r) => `${r.id}:${r.final}`).join(', ') || 'none'}`)

return {
  coverage: `${green.length}/${ASSERTIONS.length}`,
  green: green.map((r) => r.id),
  not_green: bad.map((r) => ({ id: r.id, final: r.final, why: r.refutations?.join(' ') || r.notes })),
  no_result: missing,
  all_green: green.length === ASSERTIONS.length && missing.length === 0,
}
