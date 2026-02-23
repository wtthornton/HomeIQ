# Team Tracker Automation Patterns (RAG Corpus)

Generic patterns for sports/team lights automations across all leagues (NFL, NBA, MLB, NHL, MLS, NCAA, etc.).
Use when user mentions Super Bowl, team tracker, score, kickoff, game over, playoffs, sports lights.
See `implementation/teamtracker_automation_reference_guide.md` for full attribute reference.

## Sensor States

- `PRE` – pre-game; `date` available for kickoff
- `IN` – game in progress; scores, quarter, clock, possession
- `POST` – game over; `team_winner`, final scores
- `BYE` – bye week; limited attributes

## Kickoff X seconds before

- Team Tracker sensors have `date` attribute (kickoff time UTC)
- Use `time_pattern` seconds: "/1" + template condition with `as_datetime(state_attr('sensor.X','date'))` and `timedelta`
- Helper: `input_boolean.{event}_kickoff_flashed` prevents multiple fires

## Score-increase trigger

- Trigger on sensor state change
- Condition: `trigger.from_state.attributes.team_score` vs `trigger.to_state.attributes.team_score`
- Only fire when `new > old` and state is "IN"
- Use `| int(0)` for null safety: `trigger.to_state.attributes.team_score | int(0)`

## Opponent score increase

- Same trigger; condition: `trigger.to_state.attributes.opponent_score | int(0) > trigger.from_state.attributes.opponent_score | int(0)`

## Winner detection

- Prefer `team_winner` attribute (POST only)
- Fallback to `team_score` vs `opponent_score`
- When two sensors (e.g. SEA + NE): check both; use `team_winner` if not none

## State transitions

- `to: "IN"` – game started
- `to: "POST"` – game over (for game-over fireworks, etc.)

## Attribute change triggers

- `attribute: possession` – possession change (IN only)
- `attribute: quarter` – quarter/period change
- Any attribute: `trigger: state`, `entity_id: sensor.X`, `attribute: attr_name`

## Helper creation

- Create `input_boolean.{event}_kickoff_flashed` and `input_boolean.{event}_game_over_fired`
- Condition: state "off" before firing; first action: turn_on helper
- Prevents duplicate runs for kickoff and game-over

## Team colors

- `team_colors` attribute: array of 2 hex codes; convert to `rgb_color` [r,g,b] for lights
- `opponent_colors` for opponent team

## Sport-specific attributes (IN only)

- NFL/NBA: `quarter`, `clock`, `team_timeouts`, `possession`, `last_play`, `down_distance_text`
- MLB: `outs`, `balls`, `strikes`, `on_first`, `on_second`, `on_third`
- MLS: `team_total_shots`, `team_shots_on_target`
- Volleyball/Tennis: `team_sets_won`, `opponent_sets_won`

## WLED vs Hue

- WLED: effect + rgb_color (e.g. Dancing Shadows); use for ambient
- Hue individual: per-entity flash with delays (120-180ms)
- Hue groups: for sync on/off, not rapid flash

## Super Bowl guide (concrete example)

`implementation/superbowl_teamtracker_lights_guide.md` – full YAML for:
- Kickoff flash (15s before, 30s)
- Team A score flash (15s)
- Team B score flash (15s)
- Game over fireworks (60s, winner colors)
- Helper reset

These patterns apply to any league/team; only entity IDs, colors, timing change.
