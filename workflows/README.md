# Legacy workflow specs — not AgentForge

The YAML in this directory (`enterprise-development.yaml` and `custom/homeiq-*.yaml`)
predates the AgentForge integration and **is not loadable by AgentForge**.

| | This directory | AgentForge |
|---|---|---|
| Schema | `workflow: {id, steps: [{agent, action, context_tier, creates, next}]}` | `name` / `inputs` / `nodes` / `output` |
| Agents referenced | `analyst`, `planner`, `reviewer` | must be published under the `homeiq` project |
| Status | orphaned — nothing in the repo references these files | active |

The agents these specs name (`analyst`, `planner`, `reviewer`) do not exist in this
project, so the files cannot run as written.

**Real AgentForge workflows live in `agentforge/projects/homeiq/workflows/`.**
See [docs/AF-INTEGRATION.md](../docs/AF-INTEGRATION.md).

Kept for the design intent (the multi-service quality-audit flow in
`custom/homeiq-quality-audit.yaml` is the closest ancestor of the published
`homeiq-service-audit` workflow). Retained deliberately rather than deleted — if
you port one, port it to the AgentForge schema under `agentforge/projects/`, do
not extend the specs here.
