export const meta = {
  name: 'device-kb-enrich',
  description: 'Research a per-integration device-enrichment spec, then adversarially verify each one against live HA + Postgres',
  phases: [
    { title: 'Research', detail: 'one agent per integration family — read-only' },
    { title: 'Refute', detail: 'fresh-context verifier tries to break each spec' },
  ],
}

// Six families, deliberately capped. The runtime allows 16 concurrent agents on
// this 20-core box, but 56 HomeIQ containers already run here — 6 in flight is
// the ceiling that leaves the live stack responsive. Do not widen this list
// without splitting the run.
const FAMILIES = [
  {
    key: 'hue',
    detail: '50 devices, 40 have capability rows. Signify/Philips lights + the bridge. Largest single family.',
  },
  {
    key: 'zha',
    detail: '6 devices on an SMLIGHT SLZB-06p7 coordinator. Only family with zigbee_ieee populated. lqi/battery live in HA but are NULL in Postgres for all 93.',
  },
  {
    key: 'wled',
    detail: '5 devices, 5/5 already have capability rows — use as the positive control for what "complete" looks like.',
  },
  {
    key: 'hassio',
    detail: '8 devices (Supervisor, Core, Host, OS, Backup, add-ons). Zero capability rows. These are infrastructure pseudo-devices — decide whether device_type should be a real value or an explicit not_applicable rather than NULL.',
  },
  {
    key: 'media',
    detail: 'cast (3), dlna_dmr (4), samsungtv (2), upnp (1), ipp (1) — 11 devices, zero capability rows between them.',
  },
  {
    key: 'platform',
    detail: 'sun, met, bluetooth, google_translate, backup, mobile_app, raspberry_pi, rpi_power, smlight, homeiq, hacs (3) — 13 devices, zero capability rows.',
  },
]

const SPEC = {
  type: 'object',
  required: ['family', 'device_count', 'fields', 'claims', 'risks'],
  properties: {
    family: { type: 'string' },
    device_count: { type: 'integer' },
    fields: {
      type: 'array',
      description: 'One entry per devices.devices column this family can populate.',
      items: {
        type: 'object',
        required: ['column', 'source', 'evidence_class', 'coverage', 'rule'],
        properties: {
          column: { type: 'string' },
          source: {
            type: 'string',
            description: 'Exact origin: an HA websocket command, a REST path, or an entity attribute. Name the field, not the concept.',
          },
          evidence_class: {
            type: 'string',
            enum: ['measured', 'upstream_source', 'vendor_doc', 'community', 'inferred'],
          },
          coverage: {
            type: 'integer',
            description: 'How many of this family devices the rule can actually fill. Never assume all.',
          },
          rule: { type: 'string' },
          name_derived: {
            type: 'boolean',
            description: 'True if the rule reads a friendly name at any hop. Such a rule is inadmissible per .claude/rules/friendly-names.md.',
          },
        },
      },
    },
    claims: {
      type: 'array',
      description: 'device_knowledge_claims rows this family justifies. subject_kind is model or instance.',
      items: {
        type: 'object',
        required: ['subject_kind', 'subject_key', 'fact_key', 'fact_value', 'evidence_class', 'claim_type'],
        properties: {
          subject_kind: { type: 'string', enum: ['model', 'instance'] },
          subject_key: { type: 'string' },
          fact_key: { type: 'string' },
          fact_value: { type: 'string' },
          claim_type: { type: 'string', enum: ['known', 'not_claimed'] },
          evidence_class: {
            type: 'string',
            enum: ['measured', 'upstream_source', 'vendor_doc', 'community', 'inferred'],
          },
          source_ref: { type: 'string' },
          confidence: { type: 'number' },
        },
      },
    },
    risks: { type: 'array', items: { type: 'string' } },
  },
}

const VERDICT = {
  type: 'object',
  required: ['family', 'refuted', 'findings'],
  properties: {
    family: { type: 'string' },
    refuted: {
      type: 'boolean',
      description: 'True if any field rule or claim would not survive contact with live state.',
    },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['severity', 'target', 'why'],
        properties: {
          severity: { type: 'string', enum: ['fatal', 'major', 'minor'] },
          target: { type: 'string', description: 'Which column or claim.' },
          why: { type: 'string' },
          evidence: { type: 'string', description: 'The command run and what it actually returned.' },
        },
      },
    },
    survived: {
      type: 'array',
      description: 'Field rules the verifier could not break, with the check that failed to break them.',
      items: { type: 'string' },
    },
  },
}

const GROUND_TRUTH = `
Live handles (all verified 2026-08-20):
- Postgres: docker exec homeiq-postgres psql -U homeiq -d homeiq -c "<sql>"   (host port 15432)
- device-intelligence: http://localhost:8028 — every non-health route needs
  header X-API-Key: $(docker exec homeiq-device-intelligence printenv API_KEY)
- Home Assistant: http://192.168.1.80:8123 with
  Authorization: Bearer $(docker exec homeiq-device-intelligence printenv HA_TOKEN)
- ha-setup init audit (read-only, never writes): http://localhost:8024/api/v1/init/audit

Hard constraints:
- Zigbee is HA built-in ZHA. There is no MQTT broker and no Zigbee2MQTT on this
  instance and none will be added. Any rule that reads an MQTT topic is invalid.
- devices.device_knowledge_claims.evidence_class CHECK accepts exactly:
  measured | upstream_source | vendor_doc | community | inferred.
  The four-class atlas ordering in .claude/rules/friendly-names.md is a DIFFERENT
  vocabulary and will be rejected by the constraint.
- A friendly name is never identity and never a decision input. A rule that would
  break if a device were renamed is a name match wearing a better job title —
  mark name_derived true and expect it to be rejected.
- This is a read-only run. Do not write to Postgres, HA, or any service.
`

phase('Research')

const results = await pipeline(
  FAMILIES,

  (f) =>
    agent(
      `You are specifying how to populate the empty device-knowledge columns for the "${f.key}" integration family in HomeIQ.

${f.detail}

${GROUND_TRUTH}

Measured starting state for the whole instance (2026-08-20): 93 devices, 768
device_entities, 49 capability rows covering 48 devices. These columns are NULL
for all 93 devices: device_type, power_source, lqi, battery_level,
availability_status, source. device_knowledge_claims has 0 rows.

Your job, for THIS family only:
1. Query the live handles above to see what the family actually looks like —
   both what Postgres holds now and what HA exposes that Postgres is not
   capturing. Read the real payloads; do not reason from the column names.
2. For each column you can fill, state the exact source field, the evidence
   class, the honest coverage count (how many of this family's devices the rule
   fills — not the family size), and the rule itself.
3. Propose the device_knowledge_claims rows this family justifies. Model-level
   claims (subject_kind "model") are reusable across instances; instance-level
   claims are not. Prefer model-level where the fact is about the hardware.
4. List the risks — every place your rule could produce a confidently wrong value.

Honesty beats coverage. A column you cannot fill for this family is a "not
claimed", not a guess. If a rule needs a friendly name at any hop, set
name_derived true rather than hiding it.`,
      { label: `research:${f.key}`, phase: 'Research', schema: SPEC, model: 'sonnet', effort: 'medium' },
    ),

  (spec, f) =>
    spec &&
    agent(
      `Adversarially verify this device-enrichment spec for the "${f.key}" family. Your default is REFUTED.

SPEC UNDER TEST:
${JSON.stringify(spec, null, 2)}

${GROUND_TRUTH}

You did not write this spec and you owe it nothing. Break it:
1. Re-run the queries yourself against the live handles. A source field the spec
   names must actually be present in the payload — check the serialization, not
   the model definition. "The field exists on the config model" is not "the field
   is in the wire response".
2. Check every coverage count by counting. An inflated count is a fatal finding.
3. Hunt name derivation the spec did not declare. Ask of each rule: would a
   rename break this? If yes it is a name match, whatever the variable is called.
   Hue room-group membership is the known trap — the group entity lists member
   NAMES, so it looks like independent corroboration of a device's room and is not.
4. Check every claim against the evidence_class CHECK constraint and against the
   claim's own strength. An "inferred" fact dressed as "measured" is fatal.
5. Check for the MQTT assumption. Any rule that would need a broker is fatal.

Set refuted true if ANY fatal or major finding stands. List what survived, and
name the check that failed to break it — a survivor with no check behind it is
not a survivor.`,
      { label: `refute:${f.key}`, phase: 'Refute', schema: VERDICT, model: 'opus', effort: 'high' },
    ),
)

const verdicts = results.filter(Boolean)
const clean = verdicts.filter((v) => !v.refuted).map((v) => v.family)
const broken = verdicts.filter((v) => v.refuted)

log(`${clean.length}/${FAMILIES.length} families survived refutation: ${clean.join(', ') || 'none'}`)

if (verdicts.length < FAMILIES.length) {
  log(`WARNING: ${FAMILIES.length - verdicts.length} family(ies) produced no verdict — treat as unverified, not as clean.`)
}

return {
  families_total: FAMILIES.length,
  families_verdicted: verdicts.length,
  survived: clean,
  refuted: broken.map((v) => ({
    family: v.family,
    fatal: v.findings.filter((f) => f.severity === 'fatal'),
    major: v.findings.filter((f) => f.severity === 'major'),
  })),
  verdicts,
}
