# VAL-001 — working-tree keep/revert decision record

**Decided:** 2026-08-19 (SG0, homeiq-dna-rewrite loop, iteration 1)
**Preserved copy:** session scratchpad `sg0-worktree-preserve/` (full diff + all 5 untracked files). Nothing unrecoverable.

## Ground truth established first

Identity read from `config/device_registry/list` over the HA websocket — ieee, not name:

| ieee | area | slug | role |
|---|---|---|---|
| `90:35:ea:ff:fe:c9:0e:8f` | Office | unsuffixed `inovelli_vzm31_sn` | Office Light Dimmer |
| `90:35:ea:ff:fe:c9:11:ef` | Bar | `_2`-suffixed | Bar Light Dimmer |

Live now: `switch.inovelli_vzm31_sn_smart_bulb_mode` (Office) = **on**; `..._2` (Bar) = off.

## Decision per file

| File | Decision | Why |
|---|---|---|
| `.claude/skills/orchestration-prompt/learnings.md` | **KEEP** | Five learnings, each checked against verified facts. The dimmer learning matches ieee ground truth. |
| `docs/operations/smart-bulb-mode-evaluation.md` | **REVERT**, then fix pre-existing defect | The added 175 lines attributed ieee `...11:ef` to the Office role — inverted. Reverting exposed that the *committed* base had the same inversion ("verified by friendly-name mapping") and an apply instruction naming the `_2` slug, i.e. the **Bar** dimmer. Added an ieee-anchored correction header and corrected the apply line. |
| `docs/operations/init-gateway.md` | **REVERT** | Its added paragraph directed readers into the inverted correction sections. |
| `docs/architecture/adr-device-knowledge-provenance.md` | **KEEP**, one clause corrected | Decision (ordered evidence classes) is load-bearing for VAL-004/011/012/014. Its Context repeated the retracted "neither switch feeds the downlights" claim; replaced with the actual three-failure chain, including the friendly-name identity failure. |
| `infrastructure/postgres/init-schemas.sql` | **KEEP** | `device_knowledge_claims` — ordered evidence-class CHECK, supersession FK. Sound. |
| `.../src/models/device_knowledge.py`, `services/device_knowledge_service.py`, `api/device_knowledge_router.py`, `tests/test_device_knowledge_service.py` | **KEEP** | 26/26 tests pass. Grep confirms zero LLM-calling cognition — respects "intelligence belongs in AgentForge". |
| `.../src/main.py`, `.../src/models/__init__.py` | **KEEP** | Wiring for the above. |
| `prompts/homeiq-dna-rewrite.md` | **KEEP** | This loop's prompt. |

## Deployment state — recorded, not hidden

The device-knowledge subsystem is **reviewed code that is NOT deployed**:
- `homeiq-device-intelligence` (up 20 h) serves no `/knowledge` route — container is stale vs the tree.
- `select to_regclass('public.device_knowledge_claims')` returns empty — table does not exist (`init-schemas.sql` runs only on fresh init).

Deploy + apply the schema under the sub-goal that first needs persisted evidence classes (SG4/SG5), not speculatively.
