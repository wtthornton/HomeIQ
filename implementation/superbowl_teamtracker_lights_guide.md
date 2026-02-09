# Home Assistant: Super Bowl Lights (Team Tracker + Hue + WLED)

This guide captures **everything we set up**: Team Tracker sensors for the Super Bowl, helper toggles, and the automations (kickoff, scoring, game over, and helper reset).  
Target HA version: **2026.2.1** (UI-managed automations, YAML mode).

---

## What you’re building

You’ll have:

1. **Kickoff flash**: starts **15s before kickoff** and runs **30s** (fast flashing)
2. **SEA score flash**: runs **15s**, **SEA colors only**
3. **NE score flash**: runs **15s**, **NE colors only**, visually distinct (red/blue “punch”)
4. **Game over fireworks**: runs **60s**, automatically picks the **winner** using Team Tracker (`team_winner` preferred; score fallback).  
   - WLED stays on **Dancing Shadows**, but gets nudged toward winner colors  
   - Hue individual lights flash **independently** and stay between **75–100% brightness**
5. **Reset helpers**: one automation to reset both helper flags

All “flash” loops are **time-bounded** (repeat-until), so they won’t accidentally run long if HA is busy.

---

## Prereqs

- Team Tracker integration installed (HACS or manual)
- Your Team Tracker sensors exist:
  - `sensor.super_bowl_sea`
  - `sensor.super_bowl_ne`
- Your WLED lights exist:
  - `light.bar`
  - `light.kitchen_strip`
  - `light.living_room_2`
  - `light.wled`
  - `light.wled_dishes`
  - plus two Hue-group entities you requested to include for “all” WLED lists:
    - `light.garage`
    - `light.garage_2`

> Note: `light.garage` and `light.garage_2` are Hue groups in your list (`is_hue_group: true`).  
> You explicitly asked to include them for all, so they’re included in **WLED lists** for the automations.

Your Hue **individual** lights (non-group) used for independent flashing (no office groups):
- `light.back_front_hallway`
- `light.dining_back`
- `light.dinning_front`
- `light.front_front_hallway`
- `light.garage_door`
- `light.hue_color_downlight_1`
- `light.hue_color_downlight_1_2`
- `light.hue_color_downlight_1_3`
- `light.hue_color_downlight_1_4`
- `light.hue_color_downlight_1_5`
- `light.hue_color_downlight_1_8`
- `light.hue_color_downlight_2`
- `light.hue_color_downlight_3`
- `light.hue_color_downlight_4`
- `light.hue_lr_back_left_ceiling`
- `light.hue_play_1`

---

## Step 1 — Set up Team Tracker for the Super Bowl

### Create two Team Tracker entries
You already did this, but here’s the “known good” approach:

1. **Settings → Devices & Services → Add Integration**
2. Search for **Team Tracker**
3. Create **two** entries (because you have people watching both teams):
   - Entry A for **SEA**
   - Entry B for **NE**
4. Confirm you get these sensors:
   - `sensor.super_bowl_sea`
   - `sensor.super_bowl_ne`

### Verify attributes look right
Developer Tools → **States** → open `sensor.super_bowl_sea`.  
You should see attributes like:
- `date` (kickoff time in UTC)
- `team_score`, `opponent_score`
- `team_winner` (typically becomes true/false after POST)
- sensor **state** transitions: `PRE` → `IN` → `POST`

---

## Step 2 — Create helpers (toggles)

Go to **Settings → Devices & Services → Helpers → Create Helper → Toggle** and create:

- `input_boolean.super_bowl_kickoff_flashed`
- `input_boolean.super_bowl_game_over_fired`

These prevent the kickoff and game-over automations from firing multiple times.

---

## Step 3 — Editing automations in YAML

Use UI-managed automations (recommended):

1. **Settings → Automations & Scenes → Automations**
2. Create a new automation
3. Top-right **⋮** menu → **Edit in YAML**
4. Paste one automation YAML at a time
5. Save

Important HA schema rules used here:
- Top-level keys are **singular**: `trigger`, `condition`, `action` (not plural)
- Service calls use `service:` (not `action:`)

---

## Color palettes used

### SEA (Seahawks)
- Navy:  `[0, 42, 92]`
- Green: `[105, 190, 40]`
- Silver: `[165, 172, 175]`

### NE (Patriots)
- Blue:   `[0, 34, 68]`
- Red:    `[198, 12, 48]`
- Silver: `[176, 183, 188]`

---

## Automations

### 1) Kickoff Flash (Starts -15s, Runs 30s, FAST)

- Checks kickoff time from `sensor.super_bowl_sea` attribute `date`
- Uses a 1-second tick (`time_pattern`) so it hits the -15s window reliably
- Runs for exactly 30 seconds

```yaml
alias: Super Bowl - Kickoff Flash (Starts -15s, Runs 30s)
description: >
  Starts 15 seconds before kickoff (Team Tracker 'date') and flashes for 30 seconds.
  WLED uses Dancing Shadows and is nudged to random SEA/NE colors.
  Hue individual lights flash independently. Brightness stays 75-100%.
mode: single

trigger:
  - platform: time_pattern
    seconds: "/1"

condition:
  - condition: state
    entity_id: input_boolean.super_bowl_kickoff_flashed
    state: "off"
  - condition: state
    entity_id: sensor.super_bowl_sea
    state: "PRE"
  - condition: template
    value_template: >
      {% set kickoff = as_datetime(state_attr('sensor.super_bowl_sea','date')) %}
      {% if kickoff is none %} false
      {% else %}
        {% set t = now() %}
        {{ t >= (kickoff - timedelta(seconds=15)) and t <= (kickoff + timedelta(seconds=15)) }}
      {% endif %}

action:
  - service: input_boolean.turn_on
    target:
      entity_id: input_boolean.super_bowl_kickoff_flashed

  - variables:
      start_ts: "{{ as_timestamp(now()) }}"
      wled_lights:
        - light.bar
        - light.kitchen_strip
        - light.living_room_2
        - light.wled
        - light.wled_dishes
        - light.garage
        - light.garage_2
      hue_lights:
        - light.back_front_hallway
        - light.dining_back
        - light.dinning_front
        - light.front_front_hallway
        - light.garage_door
        - light.hue_color_downlight_1
        - light.hue_color_downlight_1_2
        - light.hue_color_downlight_1_3
        - light.hue_color_downlight_1_4
        - light.hue_color_downlight_1_5
        - light.hue_color_downlight_1_8
        - light.hue_color_downlight_2
        - light.hue_color_downlight_3
        - light.hue_color_downlight_4
        - light.hue_lr_back_left_ceiling
        - light.hue_play_1
      sea_colors:
        - [0, 42, 92]
        - [105, 190, 40]
        - [165, 172, 175]
      ne_colors:
        - [0, 34, 68]
        - [198, 12, 48]
        - [176, 183, 188]
      kickoff_colors: "{{ sea_colors + ne_colors }}"

  - service: scene.create
    data:
      scene_id: sb_kickoff_snapshot
      snapshot_entities: "{{ wled_lights + hue_lights }}"

  - service: light.turn_on
    target:
      entity_id: "{{ wled_lights }}"
    data:
      effect: "Dancing Shadows"
      brightness_pct: 95
      transition: 0

  - repeat:
      until:
        - condition: template
          value_template: "{{ (as_timestamp(now()) - start_ts) >= 30 }}"
      sequence:
        - variables:
            hi: "{{ range(90, 101) | random }}"
            lo: "{{ range(75, 86) | random }}"
            wled_rgb: "{{ kickoff_colors | random }}"

        - service: light.turn_on
          target:
            entity_id: "{{ wled_lights }}"
          data:
            effect: "Dancing Shadows"
            rgb_color: "{{ wled_rgb }}"
            brightness_pct: "{{ hi }}"
            transition: 0

        - repeat:
            for_each: "{{ hue_lights }}"
            sequence:
              - service: light.turn_on
                target:
                  entity_id: "{{ repeat.item }}"
                data:
                  rgb_color: "{{ kickoff_colors | random }}"
                  brightness_pct: "{{ range(85, 101) | random }}"
                  transition: 0

        - delay:
            milliseconds: 120

        - repeat:
            for_each: "{{ hue_lights }}"
            sequence:
              - service: light.turn_on
                target:
                  entity_id: "{{ repeat.item }}"
                data:
                  brightness_pct: "{{ lo }}"
                  transition: 0

        - delay:
            milliseconds: 120

        - delay:
            milliseconds: 180

  - service: scene.turn_on
    target:
      entity_id: scene.sb_kickoff_snapshot
```

---

### 2) SEA Score Flash (15s, SEA colors only)

Triggers when `team_score` increases on `sensor.super_bowl_sea`.

```yaml
alias: Super Bowl - SEA Score Flash (15s)
description: When SEA score increases, flash 15s using SEA colors only (brightness 75-100%).
mode: single

trigger:
  - platform: state
    entity_id: sensor.super_bowl_sea

condition:
  - condition: state
    entity_id: sensor.super_bowl_sea
    state: "IN"
  - condition: template
    value_template: >
      {% set old = trigger.from_state.attributes.team_score | int(0) if trigger.from_state else 0 %}
      {% set new = trigger.to_state.attributes.team_score | int(0) if trigger.to_state else 0 %}
      {{ new > old }}

action:
  - variables:
      start_ts: "{{ as_timestamp(now()) }}"
      wled_lights:
        - light.bar
        - light.kitchen_strip
        - light.living_room_2
        - light.wled
        - light.wled_dishes
        - light.garage
        - light.garage_2
      hue_lights:
        - light.back_front_hallway
        - light.dining_back
        - light.dinning_front
        - light.front_front_hallway
        - light.garage_door
        - light.hue_color_downlight_1
        - light.hue_color_downlight_1_2
        - light.hue_color_downlight_1_3
        - light.hue_color_downlight_1_4
        - light.hue_color_downlight_1_5
        - light.hue_color_downlight_1_8
        - light.hue_color_downlight_2
        - light.hue_color_downlight_3
        - light.hue_color_downlight_4
        - light.hue_lr_back_left_ceiling
        - light.hue_play_1
      sea_colors:
        - [0, 42, 92]
        - [105, 190, 40]
        - [165, 172, 175]

  - service: scene.create
    data:
      scene_id: sb_sea_score_snapshot
      snapshot_entities: "{{ wled_lights + hue_lights }}"

  - service: light.turn_on
    target:
      entity_id: "{{ wled_lights }}"
    data:
      effect: "Dancing Shadows"
      brightness_pct: 95
      transition: 0

  - repeat:
      until:
        - condition: template
          value_template: "{{ (as_timestamp(now()) - start_ts) >= 15 }}"
      sequence:
        - variables:
            hi: "{{ range(90, 101) | random }}"
            lo: "{{ range(75, 86) | random }}"
            wled_rgb: "{{ sea_colors | random }}"

        - service: light.turn_on
          target:
            entity_id: "{{ wled_lights }}"
          data:
            effect: "Dancing Shadows"
            rgb_color: "{{ wled_rgb }}"
            brightness_pct: "{{ hi }}"
            transition: 0

        - repeat:
            for_each: "{{ hue_lights }}"
            sequence:
              - service: light.turn_on
                target:
                  entity_id: "{{ repeat.item }}"
                data:
                  rgb_color: "{{ sea_colors | random }}"
                  brightness_pct: "{{ range(85, 101) | random }}"
                  transition: 0

        - delay:
            milliseconds: 120

        - repeat:
            for_each: "{{ hue_lights }}"
            sequence:
              - service: light.turn_on
                target:
                  entity_id: "{{ repeat.item }}"
                data:
                  brightness_pct: "{{ lo }}"
                  transition: 0

        - delay:
            milliseconds: 120

        - delay:
            milliseconds: 180

  - service: scene.turn_on
    target:
      entity_id: scene.sb_sea_score_snapshot
```

---

### 3) NE Score Flash (15s, Red/Blue punch)

Triggers when `team_score` increases on `sensor.super_bowl_ne`.

```yaml
alias: Super Bowl - NE Score Flash (15s, Red/Blue Punch)
description: When NE score increases, flash 15s using a distinct Patriots red/blue pattern (75-100%).
mode: single

trigger:
  - platform: state
    entity_id: sensor.super_bowl_ne

condition:
  - condition: state
    entity_id: sensor.super_bowl_ne
    state: "IN"
  - condition: template
    value_template: >
      {% set old = trigger.from_state.attributes.team_score | int(0) if trigger.from_state else 0 %}
      {% set new = trigger.to_state.attributes.team_score | int(0) if trigger.to_state else 0 %}
      {{ new > old }}

action:
  - variables:
      start_ts: "{{ as_timestamp(now()) }}"
      wled_lights:
        - light.bar
        - light.kitchen_strip
        - light.living_room_2
        - light.wled
        - light.wled_dishes
        - light.garage
        - light.garage_2
      hue_lights:
        - light.back_front_hallway
        - light.dining_back
        - light.dinning_front
        - light.front_front_hallway
        - light.garage_door
        - light.hue_color_downlight_1
        - light.hue_color_downlight_1_2
        - light.hue_color_downlight_1_3
        - light.hue_color_downlight_1_4
        - light.hue_color_downlight_1_5
        - light.hue_color_downlight_1_8
        - light.hue_color_downlight_2
        - light.hue_color_downlight_3
        - light.hue_color_downlight_4
        - light.hue_lr_back_left_ceiling
        - light.hue_play_1
      ne_blue: [0, 34, 68]
      ne_red:  [198, 12, 48]
      ne_silver: [176, 183, 188]

  - service: scene.create
    data:
      scene_id: sb_ne_score_snapshot
      snapshot_entities: "{{ wled_lights + hue_lights }}"

  - service: light.turn_on
    target:
      entity_id: "{{ wled_lights }}"
    data:
      effect: "Dancing Shadows"
      brightness_pct: 95
      transition: 0

  - repeat:
      until:
        - condition: template
          value_template: "{{ (as_timestamp(now()) - start_ts) >= 15 }}"
      sequence:
        - variables:
            hi: "{{ range(90, 101) | random }}"
            lo: "{{ range(75, 86) | random }}"

        - service: light.turn_on
          target:
            entity_id: "{{ wled_lights }}"
          data:
            effect: "Dancing Shadows"
            rgb_color: "{{ ne_blue }}"
            brightness_pct: "{{ hi }}"
            transition: 0

        - repeat:
            for_each: "{{ hue_lights }}"
            sequence:
              - service: light.turn_on
                target:
                  entity_id: "{{ repeat.item }}"
                data:
                  rgb_color: "{{ ([ne_blue, ne_silver] | random) }}"
                  brightness_pct: "{{ range(85, 101) | random }}"
                  transition: 0

        - delay:
            milliseconds: 150

        - service: light.turn_on
          target:
            entity_id: "{{ wled_lights }}"
          data:
            effect: "Dancing Shadows"
            rgb_color: "{{ ne_red }}"
            brightness_pct: "{{ hi }}"
            transition: 0

        - repeat:
            for_each: "{{ hue_lights }}"
            sequence:
              - service: light.turn_on
                target:
                  entity_id: "{{ repeat.item }}"
                data:
                  rgb_color: "{{ ([ne_red, ne_silver] | random) }}"
                  brightness_pct: "{{ range(85, 101) | random }}"
                  transition: 0

        - delay:
            milliseconds: 150

        - repeat:
            for_each: "{{ hue_lights }}"
            sequence:
              - service: light.turn_on
                target:
                  entity_id: "{{ repeat.item }}"
                data:
                  brightness_pct: "{{ lo }}"
                  transition: 0

        - delay:
            milliseconds: 120

  - service: scene.turn_on
    target:
      entity_id: scene.sb_ne_score_snapshot
```

---

### 4) Game Over Fireworks (Winner colors, 60s, Dancing Shadows)

Triggers when either Team Tracker sensor enters `POST`.

```yaml
alias: Super Bowl - Game Over Fireworks (Winner Colors, 60s)
description: >
  When game ends (POST), pick winner (team_winner if available; else scores).
  60s fireworks: WLED stays Dancing Shadows but nudged winner-colored.
  Hue individual lights flash independently (brightness 75-100%). Restores snapshot.
mode: single

trigger:
  - platform: state
    entity_id:
      - sensor.super_bowl_ne
      - sensor.super_bowl_sea
    to: "POST"

condition:
  - condition: state
    entity_id: input_boolean.super_bowl_game_over_fired
    state: "off"

action:
  - service: input_boolean.turn_on
    target:
      entity_id: input_boolean.super_bowl_game_over_fired

  - variables:
      start_ts: "{{ as_timestamp(now()) }}"

      sea_colors:
        - [0, 42, 92]
        - [105, 190, 40]
        - [165, 172, 175]
      ne_colors:
        - [0, 34, 68]
        - [198, 12, 48]
        - [176, 183, 188]

      sea_winner: "{{ state_attr('sensor.super_bowl_sea','team_winner') }}"
      ne_winner:  "{{ state_attr('sensor.super_bowl_ne','team_winner') }}"

      sea_score: "{{ state_attr('sensor.super_bowl_sea','team_score') | int(0) }}"
      sea_opp:   "{{ state_attr('sensor.super_bowl_sea','opponent_score') | int(0) }}"
      ne_score:  "{{ state_attr('sensor.super_bowl_ne','team_score') | int(0) }}"
      ne_opp:    "{{ state_attr('sensor.super_bowl_ne','opponent_score') | int(0) }}"

      winner: >
        {% if sea_winner is not none or ne_winner is not none %}
          {{ 'SEA' if sea_winner else 'NE' }}
        {% elif sea_score + sea_opp > 0 %}
          {{ 'SEA' if sea_score > sea_opp else 'NE' }}
        {% elif ne_score + ne_opp > 0 %}
          {{ 'NE' if ne_score > ne_opp else 'SEA' }}
        {% else %}
          NE
        {% endif %}

      win_colors: "{{ sea_colors if winner == 'SEA' else ne_colors }}"

      wled_lights:
        - light.bar
        - light.kitchen_strip
        - light.living_room_2
        - light.wled
        - light.wled_dishes
        - light.garage
        - light.garage_2

      hue_lights:
        - light.back_front_hallway
        - light.dining_back
        - light.dinning_front
        - light.front_front_hallway
        - light.garage_door
        - light.hue_color_downlight_1
        - light.hue_color_downlight_1_2
        - light.hue_color_downlight_1_3
        - light.hue_color_downlight_1_4
        - light.hue_color_downlight_1_5
        - light.hue_color_downlight_1_8
        - light.hue_color_downlight_2
        - light.hue_color_downlight_3
        - light.hue_color_downlight_4
        - light.hue_lr_back_left_ceiling
        - light.hue_play_1

  - service: scene.create
    data:
      scene_id: sb_gameover_snapshot
      snapshot_entities: "{{ wled_lights + hue_lights }}"

  - service: light.turn_on
    target:
      entity_id: "{{ wled_lights }}"
    data:
      effect: "Dancing Shadows"
      brightness_pct: 95
      transition: 0

  - repeat:
      until:
        - condition: template
          value_template: "{{ (as_timestamp(now()) - start_ts) >= 60 }}"
      sequence:
        - variables:
            wled_rgb: "{{ win_colors | random }}"
            hi: "{{ range(90, 101) | random }}"
            lo: "{{ range(75, 86) | random }}"

        - service: light.turn_on
          target:
            entity_id: "{{ wled_lights }}"
          data:
            effect: "Dancing Shadows"
            rgb_color: "{{ wled_rgb }}"
            brightness_pct: "{{ hi }}"
            transition: 0

        - repeat:
            for_each: "{{ hue_lights }}"
            sequence:
              - service: light.turn_on
                target:
                  entity_id: "{{ repeat.item }}"
                data:
                  rgb_color: "{{ win_colors | random }}"
                  brightness_pct: "{{ range(85, 101) | random }}"
                  transition: 0

        - delay:
            milliseconds: 120

        - repeat:
            for_each: "{{ hue_lights }}"
            sequence:
              - service: light.turn_on
                target:
                  entity_id: "{{ repeat.item }}"
                data:
                  brightness_pct: "{{ lo }}"
                  transition: 0

        - delay:
            milliseconds: 120

        - delay:
            milliseconds: 180

  - service: scene.turn_on
    target:
      entity_id: scene.sb_gameover_snapshot
```

---

### 5) Reset Helpers (one automation for both)

```yaml
alias: Super Bowl - Reset Helpers
description: Reset kickoff/game-over helper flags for testing or next game.
mode: single

trigger:
  - platform: state
    entity_id:
      - input_boolean.super_bowl_kickoff_flashed
      - input_boolean.super_bowl_game_over_fired
    to: "on"
    for: "00:10:00"

action:
  - service: input_boolean.turn_off
    target:
      entity_id:
        - input_boolean.super_bowl_kickoff_flashed
        - input_boolean.super_bowl_game_over_fired
```

---

## Tuning (quick knobs)

- Faster flashes: change delays `120ms` → `90ms` (Hue may start missing updates below ~100ms)
- More “breathing room”: increase the final `delay` in each loop from `180ms` → `250ms`
- Reduce brightness range: adjust `range(90, 101)` and `range(75, 86)`.

---

## Troubleshooting

### “Message malformed: extra keys not allowed”
Usually caused by:
- using `triggers:` instead of `trigger:`
- using `actions:` instead of `action:`
- using `action:` instead of `service:` inside actions

All YAMLs in this file follow HA’s expected schema.

### Winner detection
At game end, Team Tracker may set `team_winner` (preferred). If it’s not available, the automation falls back to score comparison.

---

**End of guide.**
