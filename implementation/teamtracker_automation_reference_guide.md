# Team Tracker Automation Reference Guide (Generic)

**Epic:** HomeIQ Automation Platform Improvements  
**Purpose:** Generic solution for all Team Tracker sensor attributes across leagues (NFL, NBA, MLB, NHL, MLS, NCAA, etc.)  
**Source:** Based on [ha-teamtracker](https://github.com/vasqued2/ha-teamtracker) integration and Context7 Home Assistant docs.

---

## Team Tracker Sensor States

| State     | Description                                      | Attributes Available                    |
|-----------|--------------------------------------------------|-----------------------------------------|
| `PRE`     | Pre-game; ESPN published pre-game info           | Most attributes; game not started       |
| `IN`      | Game in progress                                 | Full set (scores, clock, possession…)   |
| `POST`    | Game completed                                   | Final scores, team_winner, etc.         |
| `BYE`     | Team has a bye week                              | Limited (abbr, name, logo, last_update) |
| `NOT_FOUND` | No game found                                 | api_message, api_url                    |

---

## Team Tracker Attributes (Complete)

### Core Attributes (PRE / IN / POST)

| Attribute           | Type    | States     | Description                                   | Use in Automation                        |
|---------------------|---------|------------|-----------------------------------------------|------------------------------------------|
| `date`              | datetime| PRE IN POST| Kickoff / game start time (UTC)               | Kickoff-before triggers                  |
| `kickoff_in`        | string  | PRE IN POST| Human-readable ("in 30 minutes", "tomorrow")   | Display / logging                        |
| `team_abbr`         | string  | PRE IN POST BYE | Team abbreviation (e.g., SEA)           | Identify team in templates               |
| `team_name`         | string  | PRE IN POST BYE | Team name (e.g., Seahawks)             | Display, notifications                   |
| `team_long_name`    | string  | PRE IN POST BYE | Full name (e.g., Seattle Seahawks)      | Display                                  |
| `team_score`        | int     | IN POST    | Team score                                   | **Score-increase trigger**, winner logic |
| `opponent_score`    | int     | IN POST    | Opponent score                               | **Winner detection** (fallback)          |
| `team_winner`       | bool    | POST       | Team won                                     | **Winner detection** (preferred)         |
| `opponent_winner`   | bool    | POST       | Opponent won                                 | Winner detection                         |
| `team_colors`       | list[str] | PRE IN POST | Two hex colors [primary, secondary]       | **Light colors** (convert to rgb)        |
| `opponent_colors`   | list[str] | PRE IN POST | Opponent colors                           | Opponent-team light colors               |
| `team_id`           | int     | PRE IN POST| ESPN numeric team ID                         | Match `possession`                       |
| `opponent_id`       | int     | PRE IN POST| Opponent ESPN ID                             | Match `possession`                       |
| `possession`        | id/null | IN         | Team ID in possession (ball)                 | Possession-based automations             |
| `last_play`         | string  | IN         | Last play description                        | Play-by-play notifications               |
| `last_update`       | datetime| PRE IN POST BYE | Last API update timestamp              | Staleness checks                         |

### In-Game (IN only)

| Attribute             | Type   | Sport  | Description                              | Use in Automation                      |
|-----------------------|--------|--------|------------------------------------------|----------------------------------------|
| `quarter`             | int/str| most   | Current quarter/period                    | Quarter-specific automations           |
| `clock`               | string | most   | Clock within quarter (e.g., "15:00")      | End-of-quarter, halftime               |
| `down_distance_text`  | string | NFL    | "2nd and 7"                               | Down/distance notifications            |
| `team_timeouts`       | int    | NFL/NBA| Remaining timeouts                        | Low-timeout alerts                     |
| `opponent_timeouts`   | int    | NFL/NBA| Opponent timeouts                         | -                                      |
| `team_win_probability`| float  | IN     | Win probability % (can be null)           | Probability-based triggers             |
| `opponent_win_probability` | float | IN | Opponent win probability                  | -                                      |

### Baseball (MLB) – IN only

| Attribute   | Type | Description          |
|-------------|------|----------------------|
| `clock`     | str  | Inning (e.g., "3")   |
| `outs`      | int  | Number of outs       |
| `balls`     | int  | Balls count          |
| `strikes`   | int  | Strikes count        |
| `on_first`  | bool | Runner on first      |
| `on_second` | bool | Runner on second     |
| `on_third`  | bool | Runner on third      |

### Soccer (MLS etc.) – IN only

| Attribute              | Type | Description           |
|------------------------|------|-----------------------|
| `team_total_shots`     | int  | Total shots           |
| `team_shots_on_target` | int  | Shots on net          |
| `opponent_total_shots` | int  | Opponent shots        |
| `opponent_shots_on_target` | int | Opponent on net   |

### Volleyball / Tennis – IN only

| Attribute         | Type | Description      |
|-------------------|------|------------------|
| `team_sets_won`   | int  | Sets won         |
| `opponent_sets_won` | int | Opponent sets    |

### Pre-Game (PRE only)

| Attribute   | Type  | Description                    |
|-------------|-------|--------------------------------|
| `odds`      | string| Betting odds (e.g., "PIT -5.0")|
| `overunder` | string| Over/under total (e.g., "42.5")|

### Meta

| Attribute   | States         | Description                 |
|-------------|-----------------|-----------------------------|
| `sport`     | PRE IN POST     | Sport name                  |
| `league`    | PRE IN POST     | League name                 |
| `venue`     | PRE IN POST     | Stadium name                |
| `location`  | PRE IN POST     | City, state                 |
| `tv_network`| PRE IN POST     | TV network                  |
| `event_name`| PRE IN POST     | Event (e.g., "The Masters") |
| `api_message`| All            | Troubleshooting message     |
| `api_url`   | All             | ESPN API URL                |

---

## Generic Automation Patterns

### 1. Kickoff X Seconds Before

- **Trigger:** `time_pattern` seconds: "/1"
- **Condition:** state "PRE" + template:
  - `as_datetime(state_attr('sensor.{team}','date'))`
  - `now() >= (kickoff - timedelta(seconds=X)) and now() <= (kickoff + timedelta(seconds=Y))`
- **Helper:** `input_boolean.{event}_kickoff_flashed` to prevent multiple fires

### 2. Score Increase (any team)

- **Trigger:** `platform: state`, `entity_id: sensor.{team}`
- **Condition:** state "IN" + template:
  - `trigger.to_state.attributes.team_score | int(0) > trigger.from_state.attributes.team_score | int(0)`

### 3. Opponent Score Increase (for multi-sensor setups)

- **Trigger:** same as above
- **Condition:** template:
  - `trigger.to_state.attributes.opponent_score | int(0) > trigger.from_state.attributes.opponent_score | int(0)`

### 4. Winner Detection

- **Preferred:** `state_attr('sensor.{team}','team_winner')` (POST only)
- **Fallback:** compare `team_score` vs `opponent_score` when both sensors available

### 5. State Transitions (PRE → IN, IN → POST)

- **Trigger:** `platform: state`, `entity_id: sensor.{team}`, `to: "IN"` or `to: "POST"`
- **Use for:** game start flash, game-over fireworks, etc.

### 6. Possession Change (IN)

- **Trigger:** `platform: state`, `entity_id: sensor.{team}`, `attribute: possession`
- **Use for:** possession-based lighting or notifications

### 7. Quarter / Halftime (IN)

- **Trigger:** state change on sensor
- **Condition:** template checking `state_attr('sensor.{team}','quarter')` or `clock` for halftime

### 8. Team Colors for Lights

- **Attribute:** `team_colors` – array of 2 hex codes
- **Convert:** hex → `[r, g, b]` for `rgb_color` in light.turn_on
- **Example:** `#006A4D` → `[0, 106, 77]`

### 9. Attribute Change (generic)

- **Trigger:** `trigger: state`, `entity_id: sensor.{team}`, `attribute: {attr_name}`
- **Use for:** any attribute change (possession, quarter, etc.)

---

## Example Use Cases (Beyond Super Bowl)

### NFL Game Day (generic)

- Kickoff flash (PRE, `date` attribute)
- Team score flash (IN, `team_score` increase)
- Opponent score flash (IN, `opponent_score` increase) if tracking both
- Game over fireworks (POST, `team_winner` or score fallback)

### NBA Playoffs

- Same patterns; `quarter` for period-specific actions (e.g., end-of-quarter buzzer lights)

### MLB

- Score increase on `team_score`
- `outs` = 3 → end of inning notification
- `on_first`, `on_second`, `on_third` for baserunner alerts

### Soccer (MLS)

- Goal on `team_score` or `opponent_score` increase
- `team_shots_on_target` threshold notification

### Tennis / Volleyball

- Set won: `team_sets_won` increase
- Match over: state POST + `team_winner`

### Golf / Racing (individual)

- Uses athlete sensors; attributes may differ; check `event_name`, `date`, state transitions

---

## Super Bowl Guide as One Example

`implementation/superbowl_teamtracker_lights_guide.md` is a concrete implementation of these patterns for:

- Two Team Tracker sensors (SEA, NE)
- Kickoff flash (15s before, 30s duration)
- SEA score flash (15s, SEA colors)
- NE score flash (15s, NE red/blue pattern)
- Game over fireworks (60s, winner colors)
- Helper reset

The same **generic patterns** apply to any league/team; only entity IDs, colors, and timing parameters change.

---

## RAG / Schema Alignment

- **RAG corpus** (`superbowl_guide_excerpts.md`) should reference this guide and cover all attribute patterns above.
- **Schema** must support: `time_pattern` seconds, `attribute` in state triggers, template conditions, variables, repeat.until, repeat.for_each.
- **HA AI Agent prompt** should cite this guide and the Super Bowl guide as examples when sports/team tracker keywords are detected.

---

## References

- [ha-teamtracker README](https://github.com/vasqued2/ha-teamtracker) – sensor states and attributes
- [Home Assistant automation trigger docs](https://www.home-assistant.io/docs/automation/trigger/) – state, attribute, template
- Super Bowl guide: `implementation/superbowl_teamtracker_lights_guide.md`
- RAG excerpts: `services/ha-ai-agent-service/src/data/superbowl_guide_excerpts.md`
