export const meta = {
  name: 'office-automation-verify',
  description: 'Behavioral verification of the Office presence-lighting automation, each assertion independently refuted',
  whenToUse: 'Runs SG7 of prompts/ha-office-presence-lighting.md, after SG6 deploys the automation through HomeIQ. This is the one multi-stage parallel chunk in that prompt, and the only place per-stage effort can be set.',
  phases: [
    { title: 'Observe', detail: 'drive the presence entities and record real state transitions — strictly serial, one shared live system' },
    { title: 'Refute', detail: 'fresh-context adversary re-derives each claim from HA recorder history (read-only)', model: 'opus' },
    { title: 'Synthesize', detail: 'VAL coverage verdict' },
  ],
}

// Behavioral assertions from the prompt's validation contract, extended per the
// expert-testing consultation (af90e222): per-test preconditions, entry proven
// via EACH proxy, a flicker/no-premature-shutoff test, timing anchored to the
// group entity's own last_changed, and isolation asserted across the whole
// suite window via last_changed diffing (state-only diffs miss flickers).
//
// Observations run STRICTLY SERIAL and in this exact order — they share one
// physical light and one set of proxies, and each test's end state is the next
// test's documented starting state. Refuters never toggle anything: they
// re-derive claims from HA's recorder (/api/history/period) and the
// automation's own last_triggered, which is independent evidence that cannot
// contaminate a later observation.
const ASSERTIONS = [
  {
    id: 'VAL-018',
    title: 'entry turns lights on (proxy 1)',
    observe:
      'PRECONDITION (assert before the timed window, fix if violated and re-assert): ' +
      'both input_boolean proxies off, binary_sensor.office_presence_group == "off" (a settled ' +
      'off, not unknown), light.office == "off" with a stable last_changed. Record every ' +
      '`light.*` state AND last_changed first. ' +
      'TEST: turn input_boolean.office_presence_proxy on. Poll light.office every second for ' +
      '15 s. Report the group entity\'s last_changed (the timing anchor), light.office ' +
      'last_changed before and after, and elapsed seconds from the GROUP transition to ' +
      'light.office == "on". PASS requires on within 5 s of the group transition. ' +
      'END STATE (leave it): proxy1 on, light.office on.',
  },
  {
    id: 'VAL-020',
    title: 'one occupied sensor holds lights on',
    observe:
      'PRECONDITION from the previous test: proxy1 on, light.office on. Now turn ' +
      'input_boolean.office_presence_proxy_2 on as well and confirm the group is "on". ' +
      'TEST: clear ONLY input_boolean.office_presence_proxy (proxy1). Confirm the group ' +
      'REMAINS "on" (any-mode fusion). Poll light.office every 15 s for 330 s. PASS requires ' +
      'light.office to remain "on" with an UNMOVED last_changed for the entire window. Any ' +
      'transition is a FAIL — it proves first-sensor-wins rather than genuine all-clear ' +
      'fusion. END STATE (leave it): proxy2 on, proxy1 off, light.office on.',
  },
  {
    id: 'VAL-018F',
    title: 'flicker: re-occupancy within the 5-min window aborts the off-timer',
    observe:
      'PRECONDITION from the previous test: proxy2 on (only), light.office on. ' +
      'TEST: clear input_boolean.office_presence_proxy_2 and record the group\'s off ' +
      'last_changed as T0. At T0+240 s (±5 s), turn input_boolean.office_presence_proxy on ' +
      '(group returns to "on" BEFORE the 300 s for: elapses). Keep polling light.office every ' +
      '15 s through T0+330 s. PASS requires light.office "on" continuously with an UNMOVED ' +
      'last_changed through the whole window — the off-countdown must have been aborted by ' +
      'the re-occupancy. Any off transition (even briefly) is a FAIL. ' +
      'END STATE (leave it): proxy1 on, light.office on.',
  },
  {
    id: 'VAL-019',
    title: 'exit turns lights off at 300s',
    observe:
      'PRECONDITION from the previous test: proxy1 on (only), light.office on. ' +
      'TEST: clear ALL input_boolean proxies. Read back the GROUP entity\'s last_changed for ' +
      'its on→off transition — that timestamp is T0, NOT the moment you issued the API call ' +
      '(HA times the for: from the entity transition). Poll light.office every 10 s for up to ' +
      '400 s. Report elapsed seconds from T0 to light.office == "off". PASS requires ' +
      '300 s ± 30 s. Do NOT shorten the automation `for:` delay to speed this up — a timing ' +
      'assertion proven against a shortened delay proves nothing, and editing the artifact ' +
      'under test is green-by-suppression. Wait the real time. ' +
      'AFTERWARD (still part of this observation, proving entry symmetry per VAL-018): with ' +
      'everything now off and settled, turn input_boolean.office_presence_proxy_2 on and ' +
      'measure light.office reaching "on" within 5 s of the group transition (report as ' +
      'entry_via_proxy2_seconds in notes). Then clear proxy2 again. ' +
      'END STATE: all proxies off, light.office on with the 5-minute off-countdown running — ' +
      'that is expected, leave it.',
  },
  {
    id: 'VAL-021',
    title: 'no collateral light changes',
    observe:
      'This is a whole-suite wrap-up and must NOT toggle anything. Compare the current ' +
      'last_changed of the 6 non-office lights (light.living_room, light.bar, ' +
      'light.kitchen_strip_main, light.kitchen_strip, light.kitchen_strip_segment_1, ' +
      'light.dishes) against the pre-suite snapshot recorded by VAL-018 (its evidence lists ' +
      'every light.* with last_changed). Also pull /api/history/period for those 6 entities ' +
      'across the suite window and confirm zero state changes inside it — last_changed ' +
      'diffing plus recorder history together catch flickers that state-only diffs miss. ' +
      'PASS requires every non-office light unchanged across the ENTIRE suite, including ' +
      'the gaps between tests.',
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
The automation under test is automation.office_presence_lighting; its attributes
carry last_triggered. HA recorder history: GET /api/history/period/<ISO-start>?filter_entity_id=<ids>&end_time=<ISO-end>.
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
    recheck_evidence: { type: 'string', description: 'What the refuter re-derived from recorder history' },
  },
}

phase('Observe')
log(`Verifying ${ASSERTIONS.length} behavioral assertions against the live instance (serial — one shared system)`)

// Observations are strictly serial (shared live system). Each observation's
// refutation pair is launched as soon as that observation lands, and runs
// concurrently with later observations — safe because refuters are read-only.
const refutePromises = []
const observations = []

for (const a of ASSERTIONS) {
  const obs = await agent(
    `Observe this assertion against the LIVE Home Assistant instance and report what actually happened.\n\n` +
      `Assertion ${a.id} — ${a.title}\n\n${a.observe}\n${HOW_TO_REACH_HA}\n` +
      `Report raw timestamped observations, not conclusions. If you cannot run the test ` +
      `(entity missing, service unreachable, precondition unfixable), return BLOCKED with the reason — do not guess.`,
    { label: `observe:${a.id}`, phase: 'Observe', schema: OBSERVATION, model: 'sonnet', effort: 'medium' },
  )
  observations.push({ a, obs })
  if (obs == null) continue

  // Two adversaries per assertion, different angles, READ-ONLY: they verify
  // against HA's recorder — the system of record — never by re-driving the
  // entities (that would contaminate the observations still running).
  refutePromises.push(
    parallel(
      [
        {
          lens: 'timing',
          ask:
            'Re-derive the timing from HA recorder history (/api/history/period for the group, the proxies, and light.office across the claimed window). Was the threshold actually met by the recorded transitions, or was it rounded, estimated, or inferred from a poll interval too coarse to prove it? DO NOT toggle any entity — read-only verification only.',
        },
        {
          lens: 'causation',
          ask:
            'Did the automation cause this transition, or did something else (a manual call, another automation, a WLED preset, a coincidental state push)? Check automation.office_presence_lighting attributes (last_triggered) and the recorder history around the transition. DO NOT toggle any entity — read-only verification only.',
        },
      ].map(
        (l) => () =>
          agent(
            `You are refuting a claim about a live system. Default to refuted=true if uncertain.\n\n` +
              `Assertion ${a.id} — ${a.title}\n` +
              `Claimed verdict: ${obs.verdict}${obs.elapsed_seconds != null ? ` (${obs.elapsed_seconds}s)` : ''}\n` +
              `Evidence offered:\n${obs.evidence}\n\n` +
              `Your lens: ${l.lens}. ${l.ask}\n${HOW_TO_REACH_HA}\n` +
              `Verify independently from the recorder — do not trust the transcript above.`,
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
}

const results = await parallel(refutePromises.map((p) => () => p))

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
