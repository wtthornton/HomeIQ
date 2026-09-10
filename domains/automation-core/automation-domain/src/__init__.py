"""automation-domain: the agent, authoring and proactive slices in one process.

TAP-7275 folded `ha-ai-agent-service`, `ai-automation-service-new` and
`proactive-agent-service` into this package. Each keeps its own subpackage
(`agent`, `authoring`, `proactive`) with its own settings, database manager and
routers; `main` mounts all three on one FastAPI app on port 8030.

The three slices persist to three different Postgres schemas, and each reads its
own environment variable for it -- `AGENT_DB_SCHEMA`, `AUTOMATION_DB_SCHEMA`,
`ENERGY_DB_SCHEMA`. They deliberately do NOT share `DATABASE_SCHEMA`: one
variable for three slices in one process would bind all three to whichever value
was set last, and the two that lost would read and write the wrong schema
without erroring.
"""
