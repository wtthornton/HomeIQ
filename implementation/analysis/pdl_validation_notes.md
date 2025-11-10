# PDL Workflow Validation Notes

Date: 2025-11-10  
Service: `ai-automation-service`

## Nightly Batch Script (`pdl/scripts/nightly_batch.yaml`)

- Guards:
  - `mqtt_ready`: `mqtt_connected` flag is populated from `DailyAnalysisScheduler.mqtt_client.is_connected`. Failure downgrades to warning and skips aborting the run.
  - `incremental_mode_ack`: Warns when incremental processing is disabled so operators know detectors will perform a full scan.
- Execution Path:
  1. Script runs at the start of `DailyAnalysisScheduler.run_daily_analysis`.
  2. Context is passed with keys `mqtt_connected` and `incremental_enabled`.
  3. Any `PDLExecutionError` would abort the job; current guards are warnings only.
- Logging verified manually (`logger.warning`, `logger.info`) to ensure audit trail appears alongside existing scheduler logs.

## Synergy Guardrails (`pdl/scripts/synergy_guardrails.yaml`)

- Guards:
  - `depth_cap`: Hard failure if requested chain depth exceeds supported depth (currently 4).
  - `device_limit`: Warns when number of candidate devices surpasses threshold (150) to highlight latency risks.
- Execution Path:
  1. Runs inside `DeviceSynergyDetector.detect_synergies` after device/entity load.
  2. Context includes requested depth, supported depth, candidate count, and capacity threshold.
  3. Failure raises `PDLExecutionError`, causing synergy detection to stop early with log message.

## Manual Checklist

- ✅ Scripts load through `PDLInterpreter.from_file`.
- ✅ Guards evaluated against scheduler/detector context without mutation.
- ✅ Warning and error behaviours align with plan (warnings continue, errors abort specific workflow).
- ✅ No file system writes beyond log output; safe for single-home deployment.

This satisfies the plan requirement to draft and validate PDL workflows for nightly batch and synergy guardrails.


