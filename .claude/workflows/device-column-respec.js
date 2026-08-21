export const meta = {
  name: 'device-column-respec',
  description: 'Re-spec the six NULL device columns per integration family against the four known vocabularies, then adversarially refute each spec against live HA + Postgres',
  phases: [
    { title: 'Research', detail: 'one agent per integration family — read-only, live-queried', model: 'sonnet' },
    { title: 'Refute', detail: 'fresh-context verifier tries to break each spec', model: 'opus' },
  ],
}

// Six families, deliberately capped. The runtime would allow 16 concurrent agents
// on this 20-core box, but 56 HomeIQ containers already run here — 6 in flight is
// the ceiling that leaves the live stack responsive. Do not widen this list without
// splitting the run, and do not rebuild a container while this is in flight.
const FAMILIES = [
  {
    key: 'hue',
    detail: '50 devices (largest family). Signify lights, the Bridge, plus Room/Zone/Service Group grouping pseudo-devices that are NOT physical. 40 have capability rows.',
    trap: 'Hue room-group membership lists member NAMES, not ids — it looks like independent corroboration of a room and is a name match one hop removed.',
  },
  {
    key: 'zha',
    detail: '6 devices on an SMLIGHT SLZB-06p7 coordinator. The only family with zigbee_ieee populated. lqi/battery are live in HA but NULL in Postgres for all 93.',
    trap: 'The last run put 20 of 24 claims outside REQUIRED_PROVENANCE and used space-joined title-case subject_keys that are unreachable by the read path.',
  },
  {
    key: 'wled',
    detail: '5 devices, 5/5 already carry capability rows — use as the positive control for what "complete" looks like.',
    trap: 'The last run claimed availability_status="enabled" for all 5 without checking the column vocabulary against its existing producer.',
  },
  {
    key: 'hassio',
    detail: '8 devices (Supervisor, Core, Host, OS, Backup, add-ons). Zero capability rows. Infrastructure pseudo-devices.',
    trap: 'is_battery_powered=false was cited as positive evidence for power_source; absence of a battery flag is not evidence of mains power.',
  },
  {
    key: 'media',
    detail: 'cast (3), dlna_dmr (4), samsungtv (2), upnp (1), ipp (1) — 11 devices, zero capability rows between them.',
    trap: 'The same physical TV appears under two or three integrations; a per-row claim double-counts one device.',
  },
  {
    key: 'platform',
    detail: 'sun, met, bluetooth, google_translate, backup, mobile_app, raspberry_pi, rpi_power, smlight, homeiq, hacs (3) — 13 devices, zero capability rows.',
    trap: 'rpi_power is a power-monitoring integration, not evidence of the host device power source; the last run conflated them.',
  },
]

const SPEC = {
  type: 'object',
  additionalProperties: false,
  required: ['family', 'device_count', 'fields', 'risks'],
  properties: {
    family: { type: 'string' },
    device_count: { type: 'integer' },
    fields: {
      type: 'array',
      description: 'One entry per devices.devices column this family can populate.',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['column', 'source', 'value_vocabulary', 'coverage', 'rule', 'name_derived'],
        properties: {
          column: {
            type: 'string',
            enum: ['device_type', 'power_source', 'lqi', 'battery_level', 'availability_status', 'source'],
          },
          source: {
            type: 'string',
            description: 'Exact origin: an HA websocket command, a REST path, or a named entity attribute. Name the field, not the concept.',
          },
          value_vocabulary: {
            type: 'string',
            description: 'The exact set of values this rule can emit, and where that set is defined in the repo.',
          },
          coverage: {
            type: 'integer',
            description: 'How many of THIS family devices the rule actually fills. Never assume all.',
          },
          rule: { type: 'string' },
          conflicts_with_existing_producer: {
            type: 'string',
            description: 'Name any code already writing this column, and say how this rule avoids fighting it. Empty string if none exists.',
          },
          name_derived: {
            type: 'boolean',
            description: 'True if the rule reads a friendly name, entity_id slug or area label at ANY hop. Such a rule is inadmissible.',
          },
        },
      },
    },
    risks: { type: 'array', items: { type: 'string' } },
  },
}

const VERDICT = {
  type: 'object',
  additionalProperties: false,
  required: ['family', 'refuted', 'findings', 'survived'],
  properties: {
    family: { type: 'string' },
    refuted: {
      type: 'boolean',
      description: 'True if any field rule would not survive contact with live state.',
    },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['severity', 'target', 'why', 'evidence'],
        properties: {
          severity: { type: 'string', enum: ['fatal', 'major', 'minor'] },
          target: { type: 'string' },
          why: { type: 'string' },
          evidence: { type: 'string', description: 'The command run and what it ACTUALLY returned.' },
        },
      },
    },
    survived: {
      type: 'array',
      description: 'Field rules the verifier could not break, each with the check that failed to break it. A survivor with no check behind it is not a survivor.',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['column', 'check_that_failed_to_break_it'],
        properties: {
          column: { type: 'string' },
          check_that_failed_to_break_it: { type: 'string' },
        },
      },
    },
  },
}

const GROUND_TRUTH = `
Live handles (verified 2026-08-20):
- Postgres: docker exec -i homeiq-postgres psql -U homeiq -d homeiq -c "<sql>"
  The -i is REQUIRED. Without it a heredoc is silently discarded and psql exits 0
  having done nothing. Host port is 15432; 5432 belongs to a different project.
- device-intelligence: http://localhost:8028 — every non-health route needs
  X-API-Key: $(docker exec homeiq-device-intelligence printenv API_KEY)
- Home Assistant: http://192.168.1.80:8123 with
  Authorization: Bearer $(docker exec homeiq-device-intelligence printenv HA_TOKEN)
  NOTE: /api/config/config_entries is NOT a route (404). The list is at
  /api/config/config_entries/entry.
- ha-setup init audit (read-only): http://localhost:8024/api/v1/init/audit

THE FOUR VOCABULARIES THAT REFUTED EVERY SPEC LAST TIME. These are established
contract, not hypothesis — but spot-check each against the source once:

1. availability_status accepts ONLY enabled | disabled | unavailable
   (device-intelligence src/models/database.py:51-66) and ALREADY HAS A PRODUCER:
   discovery_service._mark_absent_devices_unavailable writes 'unavailable' guarded
   by IS DISTINCT FROM. Proposing online/offline/available means (a) consumers
   filtering ='unavailable' miss your rows and (b) the next discovery pass
   overwrites you. The column is indexed.

2. device_type values must come from the shared taxonomy, which MOVED on
   2026-08-21: it is now libs/homeiq-device-taxonomy (import
   'from homeiq_device_taxonomy import device_type_vocabulary'), not
   device-context-classifier/src/patterns.py, which no longer exists. The set is
   light, switch, sensor, thermostat, fan, lock, camera, alarm, cover,
   media_player, vacuum, valve, button, remote, fridge, car, 3d_printer.
   Invented values (motion_sensor, hub, light_group, zigbee_dimmer,
   occupancy_sensor, infrastructure_service) are outside it. Call
   device_type_vocabulary() rather than trusting this list.

3. devices.source is NULL for all 93 — NOT empty-string. Three write sites bind
   the column (repository.py:241,285; device_service.py:206) but
   discovery_service.py hardcodes "source": None, which is why it is empty. "No
   producer exists" is false; "the producer hardcodes None" is true.

4. THE TWO-TABLE FACT — the most confusing thing here, and the previous
   round's premise about it was WRONG. There are two 'devices' tables with 93 rows
   each:
     - 'devices.devices'  <- written by device-intelligence-service. THIS IS YOUR
                             TARGET. All six columns are NULL for all 93.
     - 'core.devices'     <- written by data-api (DATABASE_SCHEMA=core). Its
                             device_type was backfilled on 2026-08-21 and is now
                             84/93 populated.
   They are DIFFERENT TABLES. data-api's POST classify-all therefore CANNOT
   overwrite anything you write to devices.devices — the earlier claim that it
   would was false. Do not design around a conflict that does not exist, and do
   not confuse the two when you run a count: always qualify the schema.

   For completeness: that data-api classifier WAS name-derived and was fixed on
   2026-08-21 (TAP-6392). It now classifies from entity domains, falling back to
   the device MODEL only; the name and manufacturer are no longer parameters. If
   you cite it, cite the fixed behaviour.

Hard constraints:
- Zigbee is HA built-in ZHA. There is no MQTT broker and no Zigbee2MQTT on this
  instance and none will be added. Any rule reading an MQTT topic is invalid.
- A friendly name is never identity and never a decision input. A rule that would
  break if a device were renamed is a name match wearing a better job title —
  set name_derived true and expect it to be rejected.
- is_battery_powered is NOT reliable evidence for power_source; three separate
  refuters flagged it last run.
- This is a READ-ONLY run. Do not write to Postgres, HA, or any service, and do
  not rebuild a container.
`

// Budget guard. The family list is fixed at 6 (12 agents), so this run is
// inherently bounded — but if the caller set a token target, respect it rather
// than discovering the ceiling by hitting it mid-refutation.
const MIN_TOKENS_FOR_A_FULL_RUN = 400_000
if (budget.total && budget.remaining() < MIN_TOKENS_FOR_A_FULL_RUN) {
  log(`ABORT: ${Math.round(budget.remaining() / 1000)}k tokens remaining, below the ${MIN_TOKENS_FOR_A_FULL_RUN / 1000}k a 6-family research+refute run needs. Re-run with more budget rather than half-refuting.`)
  return { aborted: 'insufficient_budget', families_total: FAMILIES.length, families_verdicted: 0 }
}

phase('Research')

const results = await pipeline(
  FAMILIES,

  (f) =>
    agent(
      `You are specifying how to populate the six empty device-knowledge columns for the "${f.key}" integration family in HomeIQ.

${f.detail}

A previous attempt at this exact spec was REFUTED on every family. The specific
trap that killed this family last time:
  ${f.trap}

${GROUND_TRUTH}

Measured starting state, re-confirmed live 2026-08-21 against
devices.devices: 93 devices, 49 capability rows over 48 devices, and device_type,
power_source, lqi, battery_level, availability_status and source NULL for all 93.
Integration mix: hue 50, hassio 8, zha 6, wled 5, dlna_dmr 4, hacs 3, cast 3,
samsungtv 2, and 12 singletons. Re-measure rather than trusting these.

Your job, for THIS family only:
1. Query the live handles to see what the family actually looks like — both what
   Postgres holds now and what HA exposes that Postgres is not capturing. Read the
   real payloads; do not reason from column names. Check the SERIALIZATION, not
   just the model definition: "the field exists on the config model" is not "the
   field is in the wire response".
2. For each column you can fill, state the exact source field, the value
   vocabulary AND where that vocabulary is defined in the repo, the honest
   coverage count for this family, and the rule.
3. Name any existing producer of that column and say how your rule avoids fighting
   it. If none exists, say so explicitly with the grep that proves it.
4. List the risks — every place your rule could produce a confidently WRONG value.

Honesty beats coverage. A column you cannot fill for this family is a coverage of
0 with a stated reason, not a guess. If a rule needs a friendly name at any hop,
set name_derived true rather than hiding it.`,
      { label: `research:${f.key}`, phase: 'Research', schema: SPEC, model: 'sonnet', effort: 'medium' },
    ),

  (spec, f) =>
    spec &&
    agent(
      `Adversarially verify this device-column spec for the "${f.key}" family. Your default is REFUTED.

SPEC UNDER TEST:
${JSON.stringify(spec, null, 2)}

${GROUND_TRUTH}

You did not write this spec and you owe it nothing. Break it:
1. Re-run every query yourself. A source field the spec names must actually be
   present in the wire payload — check the serialization site, not the model.
2. Check every coverage count by counting. An inflated count is FATAL.
3. Check every emitted value against its column's real vocabulary (constraint 1
   and 2 above). A value outside the set is FATAL — it either violates a CHECK or
   silently breaks a consumer that branches on the raw string.
4. Check for a conflicting existing producer the spec did not declare. A rule that
   gets overwritten on the next discovery pass is FATAL, not minor.
5. Hunt undeclared name derivation. Ask of each rule: would a rename break this?
   If yes it is a name match whatever the variable is called.
   ATTACK THIS HARDEST for the hue family, where room-group membership lists member
   NAMES and reads as independent corroboration of a device's room.
6. Check for the MQTT assumption. Any rule needing a broker is FATAL.

Set refuted true if ANY fatal or major finding stands. For anything you could NOT
break, name the specific check that failed to break it — a survivor with no check
behind it is not a survivor, and I will treat it as unverified.`,
      { label: `refute:${f.key}`, phase: 'Refute', schema: VERDICT, model: 'opus', effort: 'high' },
    ),
)

const verdicts = results.filter(Boolean)
const clean = verdicts.filter((v) => !v.refuted)
const broken = verdicts.filter((v) => v.refuted)

log(`${clean.length}/${FAMILIES.length} families survived refutation: ${clean.map((v) => v.family).join(', ') || 'none'}`)

if (verdicts.length < FAMILIES.length) {
  log(`WARNING: ${FAMILIES.length - verdicts.length} family(ies) produced no verdict — treat as UNVERIFIED, not as clean.`)
}

// Surviving field rules are the only thing that may be implemented. Collect them
// explicitly so the caller cannot accidentally build from a refuted spec.
const implementable = verdicts.flatMap((v) =>
  (v.survived || []).map((s) => ({ family: v.family, column: s.column, check: s.check_that_failed_to_break_it })),
)

log(`${implementable.length} individual field rule(s) survived with a named check behind them`)

return {
  families_total: FAMILIES.length,
  families_verdicted: verdicts.length,
  survived_families: clean.map((v) => v.family),
  implementable_field_rules: implementable,
  refuted: broken.map((v) => ({
    family: v.family,
    fatal: v.findings.filter((f) => f.severity === 'fatal'),
    major: v.findings.filter((f) => f.severity === 'major'),
  })),
  verdicts,
}
