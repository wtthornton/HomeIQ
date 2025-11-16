# Team Tracker Integration Guide

**Last Updated:** November 14, 2025
**Version:** 1.0.0

## Overview

HomeIQ integrates with [Team Tracker](https://github.com/vasqued2/ha-teamtracker), a Home Assistant custom integration that tracks sports teams and provides real-time game information. This integration enables you to create automations triggered by sports events like game starts, scores, and wins.

## Features

- **Automatic Detection**: HomeIQ automatically detects Team Tracker sensor entities
- **Team Management**: Add, configure, and activate teams from the HomeIQ UI
- **AI Automation**: Ask AI understands Team Tracker entities and can generate sports-based automations
- **Real-time Sync**: Synchronize team configurations with Home Assistant

## Prerequisites

1. **Home Assistant** installed and running
2. **HomeIQ** services running (Device Intelligence Service + AI Automation UI)

## Installation Steps

### Step 1: Install Team Tracker in Home Assistant

There are two methods to install Team Tracker:

#### Method A: HACS (Recommended)

1. Open **HACS** in Home Assistant
2. Go to **Integrations**
3. Click **Explore & Download Repositories**
4. Search for **"Team Tracker"**
5. Click **Download**
6. Restart Home Assistant

#### Method B: Manual Installation

1. Download the latest release from [GitHub](https://github.com/vasqued2/ha-teamtracker/releases)
2. Extract to `config/custom_components/teamtracker/`
3. Restart Home Assistant

### Step 2: Configure Team Tracker in Home Assistant

Add your teams via the Home Assistant UI:

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **Team Tracker**
4. Select your league (NFL, NBA, MLB, NHL, MLS, etc.)
5. Enter team ID/abbreviation (e.g., "DAL" for Dallas Cowboys)
6. (Optional) Customize sensor name
7. Click **Submit**

**Example YAML Configuration:**

```yaml
sensor:
  - platform: teamtracker
    league_id: "NFL"
    team_id: "DAL"
    name: "Cowboys"

  - platform: teamtracker
    league_id: "NFL"
    team_id: "NO"
    name: "Saints"
```

### Step 3: Detect Teams in HomeIQ

1. Open **HomeIQ AI Automation UI** (http://localhost:3001)
2. Navigate to **Settings**
3. Scroll to **Team Tracker Integration** section
4. Click **Detect Teams** button

HomeIQ will scan for Team Tracker sensor entities and add them to your configuration.

### Step 4: Manage Teams

In the **Team Tracker Integration** section of Settings:

- **View Teams**: See all configured teams with their status
- **Add Team**: Manually add teams you plan to configure in Home Assistant
- **Toggle Active**: Enable/disable teams for automation context
- **Sync from HA**: Refresh team data from Home Assistant
- **Delete Team**: Remove teams from HomeIQ (does not affect HA)

## Team Tracker Entity Structure

### Sensor States

Team Tracker sensors have the following states:

- `PRE`: Pre-game (before the game starts)
- `IN`: In-progress (game is being played)
- `POST`: Post-game (game has ended)
- `BYE`: Bye week (no game scheduled)
- `NOT_FOUND`: No game found or invalid configuration

### Key Attributes

Team Tracker sensors expose these attributes for use in automations:

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `team_score` | integer | Your team's current score | `21` |
| `opponent_score` | integer | Opponent's current score | `14` |
| `team_name` | string | Team name | `"Cowboys"` |
| `opponent_name` | string | Opponent name | `"Eagles"` |
| `team_long_name` | string | Full team name with city | `"Dallas Cowboys"` |
| `last_play` | string | Description of most recent play | `"Touchdown pass to Cooper"` |
| `possession` | string | Which team has the ball | `"DAL"` |
| `date` | datetime | Game date and time | `2025-11-24T16:30:00` |
| `kickoff_in` | string | Human-readable time until kickoff | `"in 2 hours"` |
| `venue` | string | Game venue name | `"AT&T Stadium"` |
| `location` | string | City/state of venue | `"Arlington, TX"` |

### Supported Leagues

- **NFL** - National Football League
- **NBA** - National Basketball Association
- **MLB** - Major League Baseball
- **NHL** - National Hockey League
- **MLS** - Major League Soccer
- **NCAAF** - NCAA Football
- **NCAAB** - NCAA Basketball

## Creating Automations

### Example 1: Flash Lights When Team Scores

**User Request (Ask AI):**
> "Flash all the lights in the bar area when Dallas Cowboys score"

**Generated Automation:**

```yaml
id: '2025111401'
alias: 'Flash Bar Lights - Cowboys Score'
description: 'Flash all bar lights when Cowboys score'
mode: single
triggers:
  - trigger: template
    value_template: >
      {{ state_attr('sensor.team_tracker_cowboys', 'team_score') | int(0) >
         state_attr('sensor.team_tracker_cowboys', 'team_score') | int(0) }}
    # Note: In practice, use a helper to store previous score
conditions:
  - condition: state
    entity_id: sensor.team_tracker_cowboys
    state: "IN"
actions:
  - repeat:
      count: 3
      sequence:
        - action: light.turn_on
          target:
            area_id: bar_area
          data:
            brightness: 255
        - delay:
            milliseconds: 500
        - action: light.turn_off
          target:
            area_id: bar_area
        - delay:
            milliseconds: 500
```

### Example 2: Game Start Notification

**User Request:**
> "Send me a notification when the Cowboys game starts"

**Generated Automation:**

```yaml
id: '2025111402'
alias: 'Cowboys Game Start Alert'
description: 'Notify when Cowboys game begins'
mode: single
triggers:
  - trigger: state
    entity_id: sensor.team_tracker_cowboys
    from: "PRE"
    to: "IN"
actions:
  - action: notify.mobile_app
    data:
      title: "🏈 Game Time!"
      message: >
        {{ state_attr('sensor.team_tracker_cowboys', 'team_long_name') }} vs
        {{ state_attr('sensor.team_tracker_cowboys', 'opponent_name') }}
        has started!
```

### Example 3: Victory Celebration

**User Request:**
> "When the Cowboys win, play victory music and turn bar lights green"

**Generated Automation:**

```yaml
id: '2025111403'
alias: 'Cowboys Victory Celebration'
description: 'Celebrate Cowboys wins'
mode: single
triggers:
  - trigger: state
    entity_id: sensor.team_tracker_cowboys
    from: "IN"
    to: "POST"
conditions:
  - condition: template
    value_template: >
      {{ state_attr('sensor.team_tracker_cowboys', 'team_score') | int(0) >
         state_attr('sensor.team_tracker_cowboys', 'opponent_score') | int(0) }}
actions:
  - action: media_player.play_media
    target:
      entity_id: media_player.bar_speaker
    data:
      media_content_id: "local_media/victory_song.mp3"
      media_content_type: "music"
  - action: light.turn_on
    target:
      area_id: bar_area
    data:
      color_name: "green"
      brightness: 255
  - delay:
      minutes: 5
  - action: light.turn_on
    target:
      area_id: bar_area
    data:
      brightness: 127
```

### Example 4: Pre-Game Reminder

**User Request:**
> "Remind me 1 hour before Cowboys games"

**Generated Automation:**

```yaml
id: '2025111404'
alias: 'Cowboys Pre-Game Reminder'
description: 'Reminder before Cowboys games'
mode: single
triggers:
  - trigger: template
    value_template: >
      {{ state_attr('sensor.team_tracker_cowboys', 'kickoff_in') == 'in 1 hour' }}
conditions:
  - condition: state
    entity_id: sensor.team_tracker_cowboys
    state: "PRE"
actions:
  - action: notify.mobile_app
    data:
      title: "⏰ Game Alert"
      message: >
        {{ state_attr('sensor.team_tracker_cowboys', 'team_long_name') }}
        plays in 1 hour!
```

## Troubleshooting

### Team Tracker Not Detected

**Problem**: HomeIQ shows "Not Installed" status

**Solutions**:
1. Verify Team Tracker is installed in Home Assistant (check **Integrations** page)
2. Ensure you've configured at least one team in Home Assistant
3. Click **Detect Teams** button in HomeIQ Settings
4. Check Home Assistant logs for Team Tracker errors
5. Restart Home Assistant and click **Detect Teams** again

### Teams Not Appearing in AI Context

**Problem**: Ask AI doesn't recognize team entities

**Solutions**:
1. Ensure teams are marked as **Active** in Settings → Team Tracker
2. Click **Sync from HA** to refresh team data
3. Verify entity IDs match in both HomeIQ and Home Assistant
4. Check that sensors are in "available" state in Home Assistant

### Automation Not Triggering

**Problem**: Sports-based automation doesn't fire

**Solutions**:
1. **Verify Sensor State**: Check sensor in Home Assistant Developer Tools
2. **Check Game Status**: Ensure game is actually in progress (state should be "IN")
3. **Review Automation Trace**: Use HA automation trace to debug
4. **Attribute Availability**: Some attributes only available during specific game states
5. **Template Syntax**: Validate templates in HA Template Editor

### Entity ID Mismatch

**Problem**: HomeIQ shows wrong entity_id

**Solutions**:
1. Click **Sync from HA** in Settings
2. Manually edit team configuration to match HA entity_id
3. Delete and re-detect teams if necessary

## API Reference

### Get Team Tracker Status

```bash
GET http://localhost:8028/api/team-tracker/status
```

**Response:**
```json
{
  "is_installed": true,
  "installation_status": "detected",
  "version": null,
  "last_checked": "2025-11-14T12:00:00Z",
  "configured_teams_count": 2,
  "active_teams_count": 2
}
```

### Get Configured Teams

```bash
GET http://localhost:8028/api/team-tracker/teams?active_only=true
```

**Response:**
```json
[
  {
    "id": 1,
    "team_id": "DAL",
    "league_id": "NFL",
    "team_name": "Cowboys",
    "team_long_name": "Dallas Cowboys",
    "entity_id": "sensor.team_tracker_cowboys",
    "is_active": true,
    "configured_in_ha": true,
    "last_detected": "2025-11-14T12:00:00Z"
  }
]
```

### Detect Team Tracker Entities

```bash
POST http://localhost:8028/api/team-tracker/detect
```

### Sync from Home Assistant

```bash
POST http://localhost:8028/api/team-tracker/sync-from-ha
```

## Architecture

### Components Involved

1. **Device Intelligence Service** (Port 8028)
   - Stores Team Tracker metadata
   - Detects and syncs team entities
   - Provides Team Tracker API

2. **AI Automation Service** (Port 8024)
   - Fetches Team Tracker teams for AI context
   - Includes Team Tracker in automation generation prompts
   - Generates sports-based automations

3. **AI Automation UI** (Port 3001)
   - Team Tracker settings page
   - Team management interface
   - Detection and sync controls

### Database Schema

**`team_tracker_integration` table:**
- `id`: Primary key
- `is_installed`: Boolean installation status
- `installation_status`: String status (not_installed, detected, configured)
- `version`: Team Tracker version (optional)
- `last_checked`: Last detection timestamp

**`team_tracker_teams` table:**
- `id`: Primary key
- `team_id`: Team abbreviation
- `league_id`: League identifier
- `team_name`: Team name
- `entity_id`: HA sensor entity ID
- `is_active`: Active for automation context
- `configured_in_ha`: Detected in Home Assistant
- `last_detected`: Last seen timestamp

## Best Practices

1. **Keep Teams Active**: Only activate teams you actually want to track to reduce AI context size
2. **Sync Regularly**: Use "Sync from HA" when adding new teams in Home Assistant
3. **Descriptive Names**: Use clear team names for better AI understanding
4. **Test Automations**: Test sports automations during live games to verify triggers
5. **Score Tracking**: Use input_number helpers to track previous scores for accurate score change detection

## Future Enhancements

- [ ] Auto-detection on startup
- [ ] Team logo display in UI
- [ ] Historical game data integration
- [ ] Multi-team pattern detection
- [ ] Playoff/championship special automations
- [ ] Team schedule preview

## Support

For issues with:
- **Team Tracker Installation**: See [Team Tracker GitHub](https://github.com/vasqued2/ha-teamtracker)
- **HomeIQ Integration**: Open an issue in HomeIQ repository
- **Automation Generation**: Check AI Automation Service logs

---

**Document Metadata:**
- **Created:** November 14, 2025
- **Version:** 1.0.0
- **Maintainer:** HomeIQ Development Team
