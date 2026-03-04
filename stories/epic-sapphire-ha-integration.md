---
epic: sapphire-ha-integration
priority: high
status: pending
estimated_duration: 6-8 weeks
risk_level: medium
source: Sapphire codebase review — gap analysis against HomeIQ HA capabilities
type: feature
---

# Epics 25-28: Sapphire-Inspired HA Integration Enhancements

**Status:** Complete (Mar 4, 2026 — Sprint 5 + Sprint 6 via parallel agent teams)
**Priority:** P1 High (Epics 25-26), P2 Medium (Epics 27-28)
**Duration:** 6-8 weeks across 4 epics
**Risk Level:** Medium — new services, but builds on existing patterns
**Source:** Detailed Sapphire (`ddxfish/sapphire`) codebase review vs HomeIQ gap analysis
**Affects:** `automation-core`, `core-platform`, `frontends`, `libs/homeiq-ha`

## Context

HomeIQ excels at **data ingestion, analytics, and automation lifecycle management** but lacks
capabilities that Sapphire handles well: direct device control, voice interaction, phone
notifications, and scheduled AI tasks. Sapphire is a single-process monolith (~44K lines)
while HomeIQ is 50 microservices — the patterns need adaptation, not direct porting.

### Gap Summary (from detailed comparison)

| Capability | Sapphire | HomeIQ | Gap |
|---|---|---|---|
| Direct device control (lights, switches, thermostat) | 9/10 | 3/10 | **Critical** — users can't say "turn off kitchen lights" |
| Voice interface (wake word + STT + TTS) | 9/10 | 0/10 | **Major** — no hands-free interaction |
| Phone notifications via HA | 7/10 | 0/10 | **Moderate** — simple but high-value |
| Scheduled AI tasks (continuity) | 8/10 | 4/10 | **Moderate** — proactive-agent exists but no user-defined cron |
| House status snapshot | 7/10 | 5/10 | **Minor** — data exists, needs aggregation endpoint |

### Sapphire Reference Code (cloned at `/tmp/sapphire/`)

| File | Lines | Relevance |
|---|---|---|
| `plugins/homeassistant/tools/homeassistant.py` | 1088 | All 12 HA tool implementations — device control, entity resolution, blacklisting, house status |
| `plugins/homeassistant/plugin.json` | 10 | Plugin manifest — capabilities declaration |
| `plugins/homeassistant/web/index.js` | 450 | Settings UI — connection test, token management, entity preview, blacklist editor |
| `core/chat/chat_tool_calling.py` | 280 | Tool calling engine — LLM function execution, result formatting, multi-format tool call parsing |
| `core/chat/function_manager.py` | 900+ | Function registry — dynamic tool loading, toolset filtering, scope isolation, execution routing |
| `core/continuity/scheduler.py` | 600+ | Cron-based task scheduler — croniter, cooldowns, task persistence, jitter |
| `core/continuity/executor.py` | 500+ | Task executor — LLM query with tool access, result persistence, error isolation |
| `core/stt/recorder.py` | 300+ | Audio recorder — adaptive VAD, sounddevice, cross-platform device selection |
| `core/stt/server.py` | 200+ | Faster Whisper STT — GPU/CPU auto-detection, model loading, transcription |
| `core/tts/tts_client.py` | 300+ | TTS HTTP client — Kokoro server, pitch/speed control, audio playback |
| `core/wakeword/wake_detector.py` | 250+ | OpenWakeWord integration — ONNX model, threshold detection, tone acknowledgment |
| `core/event_bus.py` | 200 | Pub/sub event bus — sync + async subscribers, replay buffer, keepalive |
| `docs/HOME-ASSISTANT.md` | 120 | User-facing docs — setup guide, tool reference, blacklist patterns, troubleshooting |

---

## Epic 25: Direct Device Control Service

**Priority:** P1 High | **Duration:** 2 weeks | **Stories:** 7
**New service:** `domains/automation-core/ha-device-control/` (port 8040)

### Problem

HomeIQ can create automations that control devices, but cannot directly control a device
on demand. When a user says "turn off the kitchen lights" to `ha-ai-agent-service`, the
agent can only describe what automation to create — it cannot execute the action immediately.

Sapphire solves this with 12 LLM tool functions that call HA's REST API directly
(`plugins/homeassistant/tools/homeassistant.py:426-452` — `_call_ha_service()`).

### Architecture Decision

Create a standalone `ha-device-control` microservice (not embedded in ha-ai-agent) because:
1. Separation of concerns — agent builds context, control service executes actions
2. Other services (proactive-agent, energy-correlator) may need direct control
3. Follows HomeIQ's existing pattern of single-responsibility services
4. Can be independently scaled and circuit-broken

### Story 25.1: Service Scaffold + HA REST Client

**Priority:** High | **Estimate:** 2h | **Risk:** Low

Create `ha-device-control` service using HomeIQ's shared library patterns
(`create_app` + `ServiceLifespan` + `BaseServiceSettings`).

**Implementation notes:**
- Reuse `HAConnectionManager` from `libs/homeiq-ha/` for connection + failover
- Sapphire's connection is simpler (direct `requests.get/post` per call,
  `homeassistant.py:279-287` `_get_headers()`) — HomeIQ should use async `httpx`
  with connection pooling instead
- Add circuit breaker from `homeiq-resilience` for HA availability

**Acceptance Criteria:**
- [ ] Service starts on port 8040 with health check
- [ ] Uses `HAConnectionManager` for primary/fallback HA connection
- [ ] Circuit breaker wraps all HA REST calls
- [ ] Dockerfile follows Sprint 3 hardening standards (non-root, healthcheck, multi-stage)

**Files:**
- `domains/automation-core/ha-device-control/src/main.py` (new)
- `domains/automation-core/ha-device-control/src/settings.py` (new)
- `domains/automation-core/ha-device-control/Dockerfile` (new)
- `domains/automation-core/compose.yml` (add service)

### Story 25.2: Entity Resolution + Blacklisting

**Priority:** High | **Estimate:** 3h | **Risk:** Medium

Port Sapphire's entity resolution logic with HomeIQ enhancements.

**Sapphire reference:**
- `homeassistant.py:290-299` — `_is_blacklisted()`: glob patterns (`cover.*`),
  exact IDs (`switch.computer1`), area-based (`area:Garage`)
- `homeassistant.py:302-391` — `_get_all_entities()`: fetches all states, maps
  entities to areas via HA template API in batches of 50
- `homeassistant.py:394-423` — `_find_entity()`: matches by friendly_name,
  entity_id, or `{domain}.{name}` (case-insensitive)

**HomeIQ enhancement over Sapphire:**
- Use existing `entity_resolution_service` from ha-ai-agent-service for multi-tier
  matching (positional keywords, device type keywords, confidence scoring) instead
  of Sapphire's simple exact-match
- Cache entity registry from websocket-ingestion's discovery data (already in InfluxDB)
  instead of polling HA `/api/states` on every call like Sapphire does
- Store blacklist config in PostgreSQL (admin-api managed) not JSON file

**Acceptance Criteria:**
- [ ] Entity lookup by friendly name, entity_id, or partial match with confidence score
- [ ] Blacklist support: glob patterns, exact IDs, area-based exclusion
- [ ] Entity cache from websocket-ingestion discovery (30min TTL, same as existing)
- [ ] Blacklist CRUD via admin-api endpoint

**Files:**
- `domains/automation-core/ha-device-control/src/services/entity_resolver.py` (new)
- `domains/automation-core/ha-device-control/src/services/blacklist.py` (new)
- `domains/core-platform/admin-api/src/routes/device_blacklist.py` (new)

### Story 25.3: Light & Switch Control Endpoints

**Priority:** High | **Estimate:** 2h | **Risk:** Low

Implement the core device control endpoints — lights and switches.

**Sapphire reference:**
- `homeassistant.py:561-613` — `_area_light()`: iterates entities in area, calls
  `light/turn_on` or `light/turn_off`, converts 0-100 → 0-255 brightness
- `homeassistant.py:616-667` — `_area_color()`: checks `supported_color_modes`
  (rgb, hs, xy) before setting color
- `homeassistant.py:757-787` — `_set_light()`: per-entity brightness + optional RGB
- `homeassistant.py:790-800` — `_set_switch()`: simple on/off via `turn_on`/`turn_off`

**Endpoints:**
- `POST /api/control/light` — `{entity_id, brightness: 0-100, rgb?: [r,g,b]}`
- `POST /api/control/light/area` — `{area: str, brightness: 0-100, rgb?: [r,g,b]}`
- `POST /api/control/switch` — `{entity_id, state: "on"|"off"}`

**Acceptance Criteria:**
- [ ] Light control: on/off, brightness (0-100 scale), RGB color
- [ ] Area-wide light control (all lights in area)
- [ ] Color mode validation (skip non-RGB lights for color commands)
- [ ] Switch on/off control
- [ ] All endpoints return `{success: bool, affected: list, message: str}`

### Story 25.4: Climate & Scene Control Endpoints

**Priority:** Medium | **Estimate:** 2h | **Risk:** Low

**Sapphire reference:**
- `homeassistant.py:670-695` — `_get_thermostat()`: reads first `climate.*` entity,
  returns current + target temperature + unit
- `homeassistant.py:698-724` — `_set_thermostat()`: calls `climate/set_temperature`,
  acts on first non-blacklisted climate entity only
- `homeassistant.py:459-488` — `_list_scenes_and_scripts()`: filters by domain,
  returns `short_name (type)` format
- `homeassistant.py:491-530` — `_activate()`: matches by short_name, friendly_name,
  or entity_id, calls `scene/turn_on` or `script/turn_on`

**HomeIQ enhancement:**
- Support multi-zone climate (Sapphire only handles first thermostat)
- Return climate entity_id so user can target specific zones

**Endpoints:**
- `GET /api/control/climate` — list all climate entities with state
- `POST /api/control/climate` — `{entity_id, temperature: float, hvac_mode?: str}`
- `POST /api/control/scene` — `{name: str}` (activate scene or script)

**Acceptance Criteria:**
- [ ] Get all climate entities (not just first one like Sapphire)
- [ ] Set temperature on specific climate entity by ID
- [ ] Activate scene or script by name (fuzzy match)
- [ ] Return detailed state after action

### Story 25.5: House Status Snapshot Endpoint

**Priority:** Medium | **Estimate:** 2h | **Risk:** Low

**Sapphire reference:**
- `homeassistant.py:857-1005` — `_house_status()`: comprehensive snapshot covering
  climate, presence (`person.*`), lights by area (on/off counts), binary sensors
  (door/window/motion/occupancy with human-readable states), active switches

**HomeIQ enhancement:**
- Aggregate from existing data sources (InfluxDB recent states, websocket-ingestion
  discovery cache) instead of polling HA directly like Sapphire
- Include energy data from energy-correlator (Sapphire has none)
- Include active automations (Sapphire has none)

**Endpoint:**
- `GET /api/control/status` — full house snapshot

**Acceptance Criteria:**
- [ ] Climate summary (all zones, current + target)
- [ ] Presence tracking (person entities)
- [ ] Light status by area (on count / off count)
- [ ] Binary sensor summary (doors, windows, motion — human-readable states)
- [ ] Active switches
- [ ] Energy summary (from energy-correlator, if available)
- [ ] Active automations list

### Story 25.6: Phone Notification Endpoint

**Priority:** Medium | **Estimate:** 1h | **Risk:** Low

**Sapphire reference:**
- `homeassistant.py:804-854` — `_notify()`: strips `notify.` prefix if included,
  calls `POST /api/services/notify/{service_name}`, handles 404 with helpful
  error message pointing to HA Developer Tools

**Endpoint:**
- `POST /api/control/notify` — `{message: str, title?: str, target?: str}`

**Acceptance Criteria:**
- [ ] Send notification via HA `notify.mobile_app_*` service
- [ ] Configurable default notify service (in service settings)
- [ ] Graceful error for 404 with setup instructions
- [ ] Support optional target override for multi-device households

### Story 25.7: Wire Agent Tool Calls to Device Control

**Priority:** High | **Estimate:** 3h | **Risk:** Medium

Register device control functions as LLM tools in `ha-ai-agent-service` so the AI
agent can execute direct control when users make imperative requests.

**Sapphire reference:**
- `homeassistant.py:37-246` — `TOOLS` list: 12 OpenAI-format function definitions
  with parameter schemas, descriptions, and required fields
- `homeassistant.py:1012-1089` — `execute()` router: dispatches function_name to
  implementation, validates required params, catches all exceptions
- `chat_tool_calling.py:142-230` — `ToolCallingEngine`: executes tool calls from
  LLM response, formats results back, saves to history

**Implementation:**
- Add `ha-device-control` as a dependency of `ha-ai-agent-service`
- Register tool definitions in agent's function/tool list
- Route tool call results through existing `CrossGroupClient` with auth
- Add tool descriptions to agent's context builder (so LLM knows they exist)

**Acceptance Criteria:**
- [ ] 8 tools registered: `control_light`, `control_light_area`, `control_switch`,
      `get_climate`, `set_climate`, `activate_scene`, `house_status`, `notify`
- [ ] Agent correctly invokes tools for imperative requests ("turn off lights")
- [ ] Agent still routes to automation pipeline for rule requests ("turn off lights at sunset")
- [ ] Tool results displayed in chat UI

---

## Epic 26: Voice Gateway Service

**Priority:** P1 High | **Duration:** 2-3 weeks | **Stories:** 6
**New service:** `domains/frontends/voice-gateway/` (port 8041)

### Problem

HomeIQ is web-only. Sapphire's voice pipeline (wake word → STT → LLM → TTS) enables
hands-free smart home control — the most natural interface for home automation.

### Architecture Decision

Create a `voice-gateway` service that handles audio I/O and forwards transcriptions
to `ha-ai-agent-service:8030`. This separates voice concerns from AI concerns and
allows the voice gateway to run on a dedicated device (Raspberry Pi, etc.).

Sapphire runs voice in-process (`VoiceChatSystem` in `sapphire.py`). HomeIQ should
run it as a separate service for:
1. Hardware isolation — voice needs GPU/mic, other services don't
2. Independent scaling — one voice gateway per room
3. Protocol flexibility — WebSocket audio streaming to central service

### Story 26.1: STT Service (Faster Whisper)

**Priority:** High | **Estimate:** 3h | **Risk:** Medium

**Sapphire reference:**
- `core/stt/server.py:32-80` — `WhisperSTT.__init__()`: GPU auto-detection with
  CUDA device selection, compute type fallback chain
  (`int8` → `int8_float16` → `float16` → `int8_float32`), CPU fallback
- `core/stt/recorder.py:30-75` — `AudioRecorder.__init__()`: unified device manager,
  preferred blocksize, retry on first failure, stereo downmix detection

**Implementation notes:**
- Sapphire uses `faster-whisper` directly in-process — HomeIQ should wrap it as an
  HTTP/WebSocket endpoint for service isolation
- Sapphire's null-object pattern (`stt_null.py` — `NullWhisperClient`,
  `NullAudioRecorder`) is worth adopting for graceful degradation
- HomeIQ already has `openvino-service` — consider Whisper via OpenVINO as alternative

**Acceptance Criteria:**
- [ ] WebSocket endpoint accepts audio stream (16kHz, 16-bit PCM)
- [ ] Returns transcription text via WebSocket message
- [ ] GPU auto-detection with CPU fallback (Sapphire's cascade pattern)
- [ ] Null STT fallback when model unavailable
- [ ] Health check reports model loaded status

### Story 26.2: TTS Service (Kokoro)

**Priority:** High | **Estimate:** 3h | **Risk:** Medium

**Sapphire reference:**
- `core/tts/tts_client.py:30-50` — `TTSClient.__init__()`: primary/fallback server,
  pitch shift (0.98), speed (1.3), voice name (`af_heart`)
- `core/tts/tts_server.py` — Kokoro TTS HTTP server (separate process, managed by
  `ProcessManager` with monitor-and-restart)
- `core/tts/tts_null.py` — `NullTTS` class for graceful degradation

**Implementation notes:**
- Sapphire runs TTS as a subprocess on port 5012 — HomeIQ should run it as a
  Docker container with the same Kokoro model
- Voice selection should be configurable per-user (admin-api setting)

**Acceptance Criteria:**
- [ ] HTTP endpoint: `POST /api/tts/synthesize` → returns WAV/PCM audio
- [ ] Configurable voice, speed, pitch
- [ ] NullTTS fallback when Kokoro unavailable
- [ ] Dockerfile with GPU support (CUDA) and CPU fallback

### Story 26.3: Wake Word Detection (OpenWakeWord)

**Priority:** Medium | **Estimate:** 3h | **Risk:** Medium

**Sapphire reference:**
- `core/wakeword/wake_detector.py:12-75` — `WakeWordDetector.__init__()`:
  loads ONNX model, configurable threshold (default 0.5), tone acknowledgment
  on detection
- `core/wakeword/wake_detector.py` — `start_listening()`: background thread,
  reads audio chunks, runs prediction, fires callback on detection
- `core/wakeword/models/hey_sapphire.onnx` — custom trained wake word model
- `core/wakeword/wakeword_null.py` — null pattern for disabled state

**Implementation notes:**
- HomeIQ wake word should be "Hey HomeIQ" — requires training custom ONNX model
  via openWakeWord toolkit
- Initially can use built-in models ("hey mycroft", "hey jarvis") as placeholder
- Wake word detection runs on the voice gateway device, not centrally

**Acceptance Criteria:**
- [ ] OpenWakeWord integration with configurable model and threshold
- [ ] Audio acknowledgment tone on detection
- [ ] Null detector fallback for push-to-talk mode
- [ ] WebSocket event published on detection (`WAKEWORD_DETECTED`)

### Story 26.4: Voice Pipeline Orchestrator

**Priority:** High | **Estimate:** 4h | **Risk:** Medium

Wire the voice components into a pipeline: wake word → record → STT → agent → TTS → play.

**Sapphire reference:**
- `sapphire.py:100-200` — `VoiceChatSystem`: orchestrates all voice components
- `sapphire.py:260-285` — `process_llm_query()`: sends text to LLM chat, speaks
  response via TTS, uses processing lock to prevent concurrent queries
- `core/event_bus.py` — pub/sub events coordinate UI updates during voice flow
  (`STT_RECORDING_START` → `STT_PROCESSING` → `AI_TYPING_START` → `TTS_PLAYING`)

**Implementation:**
- Voice gateway connects to `ha-ai-agent-service:8030/api/chat` via HTTP
- Pipeline: detect wake word → record until silence → transcribe → POST to agent
  → receive text response → synthesize speech → play audio
- Publish events to HomeIQ's existing WebSocket for UI coordination

**Acceptance Criteria:**
- [ ] Full pipeline: wake → record → transcribe → agent → speak
- [ ] Processing lock prevents concurrent voice queries
- [ ] Event bus integration for UI state sync
- [ ] Configurable silence detection threshold (adaptive VAD from Sapphire)
- [ ] Push-to-talk alternative (WebSocket trigger from frontend)

### Story 26.5: Hot-Swap Component Toggling

**Priority:** Low | **Estimate:** 2h | **Risk:** Low

**Sapphire reference:**
- `sapphire.py:165-240` — `toggle_stt()`, `toggle_tts()`, `toggle_wakeword()`:
  runtime enable/disable without restart, swap between real and null implementations,
  handle model loading/unloading
- Null object pattern: `NullTTS`, `NullWhisperClient`, `NullWakeWordDetector`

**Acceptance Criteria:**
- [ ] API endpoints to enable/disable STT, TTS, wake word at runtime
- [ ] Null-object swap (no restart required)
- [ ] Status endpoint reports which components are active
- [ ] Memory freed when component disabled (model unloaded)

### Story 26.6: Frontend Voice Controls

**Priority:** Medium | **Estimate:** 3h | **Risk:** Low

Add voice interaction UI to ai-automation-ui (or health-dashboard).

**Sapphire reference:**
- `interfaces/web/static/features/mic.js` — microphone button with recording state
- `interfaces/web/static/audio.js` — WebSocket audio streaming
- `interfaces/web/static/core/event-bus.js` — client-side event bus for state sync

**Acceptance Criteria:**
- [ ] Microphone button in chat interface (ai-automation-ui)
- [ ] Visual recording indicator (waveform or pulsing dot)
- [ ] Real-time transcription preview during recording
- [ ] TTS playback with stop button
- [ ] Voice component status indicators (STT/TTS/wake word on/off)

---

## Epic 27: Scheduled AI Tasks (Continuity)

**Priority:** P2 Medium | **Duration:** 1-2 weeks | **Stories:** 5
**Enhances:** `domains/energy-analytics/proactive-agent-service/` (port 8037)

### Problem

HomeIQ's `proactive-agent-service` generates reactive suggestions but has no mechanism
for user-defined scheduled AI tasks. Sapphire's "continuity" system lets users schedule
cron-based AI tasks ("every morning summarize overnight energy", "check if garage door
is still open at 11 PM").

### Story 27.1: Cron Task Scheduler

**Priority:** High | **Estimate:** 3h | **Risk:** Low

**Sapphire reference:**
- `core/continuity/scheduler.py:60-120` — `ContinuityScheduler.__init__()`:
  30-second check interval, loads tasks from JSON directory, croniter for
  cron expression parsing
- `core/continuity/scheduler.py:150-250` — `_check_schedules()`: iterates tasks,
  evaluates cron match with 90-second window, respects cooldowns, adds jitter
  (0-30s) to prevent thundering herd
- Task persistence: JSON files in `user/continuity/` directory with fields:
  `name`, `schedule` (cron), `prompt`, `enabled`, `cooldown_minutes`,
  `tools` (allowed tool list), `last_run`, `run_count`

**Implementation:**
- Add scheduler to proactive-agent-service (not a new service)
- Store tasks in PostgreSQL (`automation` schema) not JSON files
- Use APScheduler (already a HomeIQ dependency) instead of raw croniter + threading

**Acceptance Criteria:**
- [ ] Cron expression support (standard 5-field)
- [ ] Task CRUD via admin-api endpoints
- [ ] Cooldown enforcement (prevent re-fire within window)
- [ ] Jitter (0-30s) on scheduled execution
- [ ] Task enable/disable without deletion
- [ ] Execution history in PostgreSQL

### Story 27.2: Task Executor with Tool Access

**Priority:** High | **Estimate:** 3h | **Risk:** Medium

**Sapphire reference:**
- `core/continuity/executor.py` — `ContinuityExecutor`: creates isolated LLM
  conversation with task prompt, executes with tool access (same function_manager
  as chat), saves result to task history, error isolation per task
- Key pattern: executor gets `system` reference for TTS/tools but runs in
  isolated conversation (no chat history contamination)

**Implementation:**
- Executor calls `ha-ai-agent-service/api/chat` with task prompt
- Include device control tools (Epic 25) so scheduled tasks can act
- Results stored in PostgreSQL with task_id foreign key

**Acceptance Criteria:**
- [ ] Execute task prompt via ha-ai-agent-service API
- [ ] Tool access for scheduled tasks (device control, notifications)
- [ ] Result persistence (prompt, response, tools used, duration, success/failure)
- [ ] Error isolation — one failing task doesn't block others
- [ ] Configurable max execution time per task

### Story 27.3: Built-in Task Templates

**Priority:** Medium | **Estimate:** 2h | **Risk:** Low

Provide starter templates inspired by Sapphire's continuity presets.

**Templates:**
1. "Morning Briefing" — `0 7 * * *` — summarize overnight events, energy usage, weather
2. "Security Check" — `0 23 * * *` — verify doors/windows closed, garage down, lights off
3. "Energy Report" — `0 18 * * 5` — weekly energy summary with trends
4. "Device Health" — `0 9 * * 1` — weekly check for offline/unresponsive devices

**Acceptance Criteria:**
- [ ] 4 built-in templates with sensible defaults
- [ ] Templates editable after creation
- [ ] Templates include suggested tools and notification preference

### Story 27.4: Task Management UI

**Priority:** Medium | **Estimate:** 3h | **Risk:** Low

Add scheduled tasks tab to ai-automation-ui.

**Acceptance Criteria:**
- [ ] Task list view (name, schedule, last run, status, enabled toggle)
- [ ] Create/edit task form (name, cron expression, prompt, tools, notification)
- [ ] Cron expression helper (human-readable preview: "Every day at 7 AM")
- [ ] Task execution history viewer
- [ ] Manual "Run Now" button

### Story 27.5: Notification Integration

**Priority:** Medium | **Estimate:** 2h | **Risk:** Low

Connect scheduled task results to notification channels.

**Sapphire reference:**
- Sapphire's continuity tasks can call `ha_notify` as a tool — the LLM decides
  whether to notify based on the prompt and result
- Example: "Check garage door at 11 PM. If open, send me a notification."

**Implementation:**
- Tasks can be configured with notification preference: `always`, `on_alert`, `never`
- Use device control service's notify endpoint (Story 25.6)
- Results with `on_alert` only notify when LLM response contains alert/warning

**Acceptance Criteria:**
- [ ] Per-task notification preference (always / on_alert / never)
- [ ] Notification via HA mobile app (Story 25.6)
- [ ] LLM-determined alert detection for `on_alert` mode
- [ ] Notification includes task name and summary

---

## Epic 28: Enhanced Event Bus + Real-Time Status

**Priority:** P2 Medium | **Duration:** 1 week | **Stories:** 4
**Enhances:** `domains/core-platform/websocket-ingestion/`, `domains/frontends/`

### Problem

HomeIQ ingests all HA events but doesn't expose a real-time aggregated house status
to frontends or the AI agent. Sapphire's event bus (`core/event_bus.py`) provides a
clean pub/sub model with replay buffer that keeps all UI components in sync.

### Story 28.1: House Status Aggregation Service

**Priority:** High | **Estimate:** 3h | **Risk:** Low

Create an aggregation layer that maintains current house state from websocket-ingestion
events and serves it via a single endpoint.

**Sapphire reference:**
- `homeassistant.py:857-1005` — `_house_status()`: builds snapshot from climate,
  presence, lights-by-area, binary sensors (door/window/motion with human-readable
  states like "open"/"closed"/"detected"/"clear"), active switches

**HomeIQ advantage:**
- Sapphire polls `/api/states` on every call. HomeIQ already has real-time state
  from websocket-ingestion — just needs aggregation on top of existing data.
- Can include data Sapphire doesn't have: energy, active automations, device health

**Acceptance Criteria:**
- [ ] In-memory state cache updated by websocket-ingestion events
- [ ] REST endpoint: `GET /api/status/house` returns full snapshot
- [ ] WebSocket endpoint: pushes delta updates on state change
- [ ] Sections: climate, presence, lights-by-area, sensors, switches, energy, automations

### Story 28.2: Frontend Event Bus (Client-Side)

**Priority:** Medium | **Estimate:** 2h | **Risk:** Low

**Sapphire reference:**
- `interfaces/web/static/core/event-bus.js` — client-side pub/sub, mirrors
  server events to UI components
- `interfaces/web/static/core/events.js` — event type constants

**Implementation:**
- WebSocket connection to house status endpoint
- Client-side event bus distributes updates to React components
- Replace polling in health-dashboard with push updates

**Acceptance Criteria:**
- [ ] WebSocket client with auto-reconnect
- [ ] Client-side event bus (publish/subscribe pattern)
- [ ] Health dashboard components subscribe to relevant events
- [ ] Reduces polling load on data-api

### Story 28.3: Live Status Dashboard Widget

**Priority:** Medium | **Estimate:** 2h | **Risk:** Low

Add a real-time house status card to health-dashboard home page.

**Acceptance Criteria:**
- [ ] "House Status" card showing: climate, lights on/off by area, open doors/windows
- [ ] Live updates (no polling, push via WebSocket)
- [ ] Color-coded status indicators (green/yellow/red)
- [ ] Expandable sections for details

### Story 28.4: Agent Context Enhancement

**Priority:** High | **Estimate:** 2h | **Risk:** Low

Feed real-time house status into `ha-ai-agent-service` context builder so the AI
always knows current home state without querying HA.

**Current gap:** The agent's context builder queries HA REST API for states. With the
aggregation service, it can read from local cache (faster, no HA dependency during chat).

**Acceptance Criteria:**
- [ ] Agent context builder reads from house status cache (not HA REST)
- [ ] Context includes all sections from Story 28.1
- [ ] Falls back to HA REST if aggregation service unavailable
- [ ] Agent response latency improved (no HA round-trip for context)

---

## Dependency Graph

```
Epic 25 (Device Control)        Epic 28 (Event Bus)
  ├── 25.1 scaffold              ├── 28.1 aggregation
  ├── 25.2 entity resolution     ├── 28.2 client event bus
  ├── 25.3 lights/switches       ├── 28.3 status widget
  ├── 25.4 climate/scenes        └── 28.4 agent context ← depends on 28.1
  ├── 25.5 house status
  ├── 25.6 notifications
  └── 25.7 agent wiring ← depends on 25.1-25.6

Epic 26 (Voice Gateway)         Epic 27 (Scheduled Tasks)
  ├── 26.1 STT                   ├── 27.1 scheduler
  ├── 26.2 TTS                   ├── 27.2 executor ← depends on 25.7 (tools)
  ├── 26.3 wake word             ├── 27.3 templates
  ├── 26.4 pipeline ← 26.1-26.3  ├── 27.4 UI
  ├── 26.5 hot-swap              └── 27.5 notifications ← depends on 25.6
  └── 26.6 frontend ← 26.4

Recommended execution order:
  Sprint 5: Epic 25 (device control) + Epic 28 (event bus) — in parallel
  Sprint 6: Epic 27 (scheduled tasks, needs 25.7) + Epic 26 (voice, independent)
```

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Voice gateway GPU requirements | CPU fallback for all components (Sapphire pattern); OpenVINO as alternative |
| Wake word model training | Use built-in OpenWakeWord models initially; train custom "HomeIQ" model later |
| HA REST API rate limiting | Entity caching (30min TTL), batch operations, circuit breaker |
| Security — direct device control | Blacklist pattern (Sapphire), require explicit opt-in per device domain |
| Latency — voice round-trip | STT + agent + TTS must complete in <3s; local models preferred |
| Scope creep — Sapphire has 65+ tools | Only port HA-specific tools (12 functions); ignore SSH, Bitcoin, email |
