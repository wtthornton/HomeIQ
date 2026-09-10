# Sport-Specific Automation Patterns for Home Assistant

## MLB (Baseball)

### Team Tracker Attributes (MLB)
- `team_score`, `opponent_score`
- `innings`, `outs`, `balls`, `strikes`
- `on_first`, `on_second`, `on_third` (boolean)
- `team_hits`, `opponent_hits`
- `team_errors`, `opponent_errors`

### Home Run Celebration
```yaml
alias: "MLB Home Run Lights"
trigger:
  - platform: state
    entity_id: sensor.mlb_team_tracker
    attribute: team_score
condition:
  - condition: template
    value_template: "{{ trigger.to_state.attributes.team_score | int > trigger.from_state.attributes.team_score | int }}"
  - condition: template
    value_template: "{{ trigger.to_state.attributes.on_first == false and trigger.to_state.attributes.on_second == false and trigger.to_state.attributes.on_third == false }}"
action:
  - service: light.turn_on
    target:
      entity_id: light.wled_strip
    data:
      effect: "Fireworks"
      brightness: 255
mode: single
```

### Strikeout Flash
```yaml
alias: "MLB Strikeout Flash"
trigger:
  - platform: state
    entity_id: sensor.mlb_team_tracker
    attribute: outs
condition:
  - condition: template
    value_template: "{{ trigger.to_state.attributes.strikes | int == 3 }}"
action:
  - service: light.turn_on
    target:
      entity_id: light.game_lights
    data:
      flash: short
mode: single
```

## MLS / Soccer

### Team Tracker Attributes (Soccer)
- `team_score`, `opponent_score`
- `team_shots_on_target`, `opponent_shots_on_target`
- `team_total_shots`, `opponent_total_shots`
- `possession` (percentage)
- `team_yellow_cards`, `team_red_cards`
- `clock` (match time)

### Goal Celebration
```yaml
alias: "Soccer Goal Celebration"
trigger:
  - platform: state
    entity_id: sensor.mls_team_tracker
    attribute: team_score
condition:
  - condition: template
    value_template: "{{ trigger.to_state.attributes.team_score | int > trigger.from_state.attributes.team_score | int }}"
action:
  - service: light.turn_on
    target:
      entity_id: light.wled_strip
    data:
      effect: "Color Wipe"
      rgb_color: "{{ state_attr('sensor.mls_team_tracker', 'team_colors') | first }}"
      brightness: 255
  - delay:
      seconds: 30
  - service: light.turn_on
    target:
      entity_id: light.wled_strip
    data:
      effect: "Solid"
      brightness: 150
mode: single
```

## Tennis / Volleyball

### Team Tracker Attributes (Tennis)
- `team_sets_won`, `opponent_sets_won`
- `team_score` (current game score)
- `clock` (match time)

### Set Won Celebration
```yaml
alias: "Tennis Set Won"
trigger:
  - platform: state
    entity_id: sensor.tennis_tracker
    attribute: team_sets_won
condition:
  - condition: template
    value_template: "{{ trigger.to_state.attributes.team_sets_won | int > trigger.from_state.attributes.team_sets_won | int }}"
action:
  - service: light.turn_on
    target:
      entity_id: light.wled_strip
    data:
      effect: "Rainbow"
      brightness: 255
  - delay:
      seconds: 15
  - service: light.turn_on
    target:
      entity_id: light.wled_strip
    data:
      effect: "Solid"
mode: single
```

## NHL (Hockey)

### Team Tracker Attributes (NHL)
- `team_score`, `opponent_score`
- `team_shots_on_goal`, `opponent_shots_on_goal`
- `power_play` (boolean)
- `period` (1, 2, 3, OT)
- `clock` (period time)

### Goal Horn
```yaml
alias: "NHL Goal Horn"
trigger:
  - platform: state
    entity_id: sensor.nhl_team_tracker
    attribute: team_score
condition:
  - condition: template
    value_template: "{{ trigger.to_state.attributes.team_score | int > trigger.from_state.attributes.team_score | int }}"
action:
  - service: media_player.play_media
    target:
      entity_id: media_player.living_room_speaker
    data:
      media_content_type: music
      media_content_id: "media-source://media_source/local/goal_horn.mp3"
  - service: light.turn_on
    target:
      entity_id: light.wled_strip
    data:
      effect: "Police"
      brightness: 255
mode: single
```

### Power Play Indicator
```yaml
alias: "NHL Power Play Lights"
trigger:
  - platform: state
    entity_id: sensor.nhl_team_tracker
    attribute: power_play
    to: "True"
action:
  - service: light.turn_on
    target:
      entity_id: light.wled_strip
    data:
      effect: "Breathe"
      rgb_color: "{{ state_attr('sensor.nhl_team_tracker', 'team_colors') | first }}"
mode: single
```

## Generic Team Tracker Reference

All sports share these common attributes:
- `team_name`, `opponent_name`
- `team_score`, `opponent_score`
- `team_abbr`, `opponent_abbr`
- `team_colors` (list of RGB tuples)
- `state` (PRE, IN, POST, NOT_FOUND)
- `date`, `kickoff_in`
- `last_updated`

### Generic Score Change Trigger Pattern
```yaml
trigger:
  - platform: state
    entity_id: sensor.{sport}_team_tracker
    attribute: team_score
condition:
  - condition: template
    value_template: >
      {{ trigger.to_state.attributes.team_score | int >
         trigger.from_state.attributes.team_score | int }}
```
