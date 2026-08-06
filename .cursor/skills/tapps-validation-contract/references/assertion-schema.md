# Assertion ID schema

- Format: `VAL-<AREA>-###` where AREA is a short SCREAMING slug (AUTH, API, UI, …)
  and ### is a zero-padded integer starting at 001.
- IDs are stable for the life of the mission/epic. Do not reuse IDs for different
  meaning; add VAL-AREA-002 instead.
- Evidence tools: prefer deterministic commands whose output can be pasted
  (`pytest -q`, `curl -sS`, smoke scripts). LLM narration is not evidence.
