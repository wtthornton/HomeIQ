# Team Tracker Installation Guide

## Install Team Tracker

**First, try searching in HACS directly - it's in the default store:**

1. Go to HACS → Integrations
2. Click "EXPLORE & DOWNLOAD REPOSITORIES" 
3. Search for "Team Tracker"
4. It should appear in the list
5. Click "Download"
6. Restart Home Assistant

**If that doesn't work, add as custom repository:**

### Steps:
1. Open HACS in Home Assistant
2. Click the three-dot menu (⋮) in top right
3. Select "Custom repositories"
4. Click "+ ADD CUSTOM REPOSITORY"
5. Enter:
   - **Repository:** `vasqued2/ha-teamtracker` (NOT the full URL)
   - **Category:** Integration
   
   **Important:** 
   - Enter just the repository name `vasqued2/ha-teamtracker`
   - Note: It's "vasqued2" (one 'd'), NOT "vasquatch2" (with 'ch')
   - Do NOT enter the full URL like `https://github.com/...`
6. Click "ADD"

### Then Install:
1. After adding repository, go to HACS → Integrations
2. You should now see "Team Tracker" in the list
3. Click on "Team Tracker"
4. Click "Download"
5. Restart Home Assistant
6. Go to Settings → Devices & Services
7. Click "+ ADD INTEGRATION"
8. Search for "Team Tracker"
9. Configure your teams (NFL, NHL, NBA, MLB)

## Alternative: Search for Different Terms

If the repository isn't showing up, try searching for:
- "vasquatch2"
- "team_tracker"
- "NFL NHL"
- "sports tracker"

## Verify Installation

After installation, check if sensors are created:
```bash
# Check for Team Tracker sensors
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://YOUR_HA_URL:8123/api/states | \
     grep team_tracker
```

You should see sensors like:
- `sensor.team_tracker_raiders`
- `sensor.team_tracker_vegas_golden_knights`

## Troubleshooting

If Team Tracker doesn't show up in HACS:
1. Update HACS to latest version
2. Clear HACS cache (HACS → Settings → Clear cache)
3. Restart Home Assistant
4. Try adding as custom repository

## Links

- GitHub Repository: https://github.com/vasquatch2/team_tracker
- HACS: https://hacs.xyz

