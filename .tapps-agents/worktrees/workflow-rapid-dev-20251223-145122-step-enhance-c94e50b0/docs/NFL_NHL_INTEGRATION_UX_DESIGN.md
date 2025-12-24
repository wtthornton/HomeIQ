# NFL & NHL Integration - UX/UI Design Document

## 🎯 Executive Summary

This document outlines a comprehensive UX/UI design for integrating NFL and NHL sports data into the HA Ingestor Dashboard, providing real-time game monitoring, statistics visualization, and intelligent alerting capabilities.

## 🎨 Design Philosophy

**Key Principles:**
- **Real-Time First**: Live updates with WebSocket connections for instant score changes
- **Sports-Centric Aesthetics**: Team colors, dynamic theming, and sports-specific iconography
- **Personalization**: User-selectable favorite teams and customizable views
- **Mobile-Responsive**: Optimized for viewing games on any device
- **Data-Rich, Clutter-Free**: Information hierarchy that prioritizes active games

---

## 📊 Dashboard Layout Design

### 1. **Sports Tab** (New Primary Tab)

```
┌─────────────────────────────────────────────────────────────┐
│  🏈 NFL & 🏒 NHL     [⚙️ Configure] [🔄 Auto-Refresh: ON]   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 🏈 NFL       │  │ 🏒 NHL       │  │ ⭐ Favorites │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  📍 LIVE NOW (3 games)                                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 🟢 LIVE  Q3  12:45                                  │    │
│  │ ┌──────────────┐ vs ┌──────────────┐               │    │
│  │ │ 🏈 49ers  24 │    │ Seahawks  17 │  📊 Stats    │    │
│  │ └──────────────┘    └──────────────┘  🔔 Alerts   │    │
│  │ [View Play-by-Play] [Team Stats] [Player Stats]    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  📅 UPCOMING TODAY (5 games)                                 │
│  📜 COMPLETED (4 games)                                       │
└─────────────────────────────────────────────────────────────┘
```

### 2. **Sports Overview Dashboard**

**Header Section:**
```
┌─────────────────────────────────────────────────────────────┐
│  🏈 NFL Week 7 | 🏒 NHL Season 2024-25                      │
│  └─ 3 Live Games • 5 Upcoming Today • 12 Favorites Active  │
└─────────────────────────────────────────────────────────────┘
```

**Live Games Section** (Priority #1):
- **Card-based Layout** with pulsing "LIVE" indicator
- **Team Logos** and colors prominently displayed
- **Real-time Score Updates** with animation on score changes
- **Game Clock** and period/quarter display
- **Quick Stats**: Passing yards, shots on goal, etc.
- **Expandable Details**: Click to see full stats

**Upcoming Games Section**:
- **Countdown Timer** to game start
- **Pre-game Analysis**: Odds, predictions, team form
- **Set Alert Button**: "Notify me when game starts"
- **Weather Conditions** for outdoor NFL games

**Recently Completed Section**:
- **Final Scores** with winning team highlighted
- **Key Statistics** and game highlights
- **Links to Full Game Analysis**

---

## 🎯 Core Features & UX Patterns

### Feature 1: Team Selection & Personalization ⭐ **CORE REQUIREMENT**

**Critical Design Principle:** Only fetch data for teams the user explicitly selects. No background data fetching for unselected teams.

**User Experience:**

1. **Mandatory First-Time Setup Wizard**:
   ```
   ┌─────────────────────────────────────────────────────┐
   │  🎯 Sports Integration Setup (Step 1 of 3)         │
   │                                                      │
   │  To optimize performance and API usage, please      │
   │  select ONLY the teams you want to track:          │
   │                                                      │
   │  🏈 NFL Teams (Select at least 1):                 │
   │  ┌──────────────────────────────────────────┐      │
   │  │ [Search teams...]                         │      │
   │  └──────────────────────────────────────────┘      │
   │                                                      │
   │  [Grid of 32 NFL team logos - click to select]     │
   │  ☐ 49ers  ☐ Bears  ☐ Bengals  ☐ Bills             │
   │  ☐ Broncos ☐ Browns ☑ Cowboys ☐ Dolphins          │
   │  ... (show all 32)                                  │
   │                                                      │
   │  Selected: 1 team (Cowboys)                         │
   │                                                      │
   │  [Back] [Continue] [Select All - Not Recommended]  │
   │                                                      │
   │  💡 Tip: Select 3-5 teams for best performance     │
   └─────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────┐
   │  🎯 Sports Integration Setup (Step 2 of 3)         │
   │                                                      │
   │  🏒 NHL Teams (Optional - or skip):                │
   │  [Search teams...]                                  │
   │                                                      │
   │  [Grid of 32 NHL team logos]                        │
   │  ☐ Bruins  ☐ Blackhawks  ☐ Blue Jackets           │
   │  ☑ Capitals ☐ Flames  ☐ Flyers  ☐ Golden Knights  │
   │  ... (show all 32)                                  │
   │                                                      │
   │  Selected: 1 team (Capitals)                        │
   │                                                      │
   │  [Back] [Continue] [Skip NHL]                       │
   └─────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────┐
   │  🎯 Sports Integration Setup (Step 3 of 3)         │
   │                                                      │
   │  ✅ Review Your Selections:                        │
   │                                                      │
   │  🏈 NFL Teams (1):                                 │
   │  • Dallas Cowboys                                   │
   │                                                      │
   │  🏒 NHL Teams (1):                                 │
   │  • Washington Capitals                              │
   │                                                      │
   │  📊 Estimated API Usage:                           │
   │  • ~24 calls/day (well within free tier)           │
   │  • Updates every 15 seconds during games            │
   │                                                      │
   │  ⚠️ Important: Only these teams will be monitored. │
   │     You can add/remove teams anytime in Settings.  │
   │                                                      │
   │  [Back] [Confirm & Start]                           │
   └─────────────────────────────────────────────────────┘
   ```

2. **Team Management Interface**:
   ```
   ┌─────────────────────────────────────────────────────┐
   │  ⚙️ Manage Tracked Teams                           │
   ├─────────────────────────────────────────────────────┤
   │                                                      │
   │  🏈 NFL Teams (2 selected):                        │
   │  ┌──────────────────────────────────────────┐      │
   │  │ [+ Add Team]                              │      │
   │  └──────────────────────────────────────────┘      │
   │                                                      │
   │  ┌─────────────────────────────────────────┐       │
   │  │ 🏈 Dallas Cowboys            [⭐] [🗑️] │       │
   │  │ Next game: vs Eagles (Sun 4:25 PM)      │       │
   │  │ Record: 7-3  │  Alerts: ✅ ON           │       │
   │  └─────────────────────────────────────────┘       │
   │                                                      │
   │  ┌─────────────────────────────────────────┐       │
   │  │ 🏈 San Francisco 49ers      [⭐] [🗑️] │       │
   │  │ Next game: @ Seahawks (Sun 1:00 PM)     │       │
   │  │ Record: 8-2  │  Alerts: ✅ ON           │       │
   │  └─────────────────────────────────────────┘       │
   │                                                      │
   │  🏒 NHL Teams (1 selected):                        │
   │  [+ Add Team]                                       │
   │                                                      │
   │  ┌─────────────────────────────────────────┐       │
   │  │ 🏒 Washington Capitals      [⭐] [🗑️] │       │
   │  │ Next game: vs Penguins (Tue 7:00 PM)    │       │
   │  │ Record: 12-5-2 │ Alerts: ✅ ON          │       │
   │  └─────────────────────────────────────────┘       │
   │                                                      │
   │  📊 Current API Usage:                              │
   │  • 42 calls today (of 100 free tier limit)         │
   │  • 3 teams = ~36 calls/day estimated               │
   │                                                      │
   │  💡 Recommendations:                                │
   │  • You can safely add 2-3 more teams               │
   │  • Consider upgrading for unlimited tracking       │
   │                                                      │
   │  [Save Changes]                                     │
   └─────────────────────────────────────────────────────┘
   ```

3. **Smart Team Selection Features**:
   - **Search & Filter**: Quick search by team name or city
   - **Division Selection**: "Track all NFC East teams"
   - **Rivalry Mode**: Automatically add division rivals
   - **Import Favorites**: Sync from ESPN or other apps (future)
   - **Quick Add**: Add team from any game card
   - **Team Limits**: Warn when approaching API limits

4. **Empty State (No Teams Selected)**:
   ```
   ┌─────────────────────────────────────────┐
   │         🏈🏒                            │
   │                                          │
   │    No Teams Selected Yet!                │
   │                                          │
   │    Start tracking your favorite teams    │
   │    to see live scores and updates.      │
   │                                          │
   │    [+ Add Your First Team]               │
   │                                          │
   │    💡 New here? Try adding:             │
   │    • Your local team                     │
   │    • Your favorite team                  │
   │    • Top teams this season               │
   └─────────────────────────────────────────┘
   ```

### Feature 2: Real-Time Game Monitoring

**Live Game Card Design:**
```
┌──────────────────────────────────────────────────────────┐
│ 🟢 LIVE  │  Quarter 3  │  12:45  │  🔔 Alerts: 3       │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌────────────────────┐  vs  ┌────────────────────┐     │
│  │  [49ers Logo]      │      │  [Seahawks Logo]   │     │
│  │  San Francisco     │      │  Seattle           │     │
│  │  49ers             │      │  Seahawks          │     │
│  │                    │      │                    │     │
│  │     24             │      │     17             │     │
│  │  ▲ +7 (Last TD)    │      │  ▼                 │     │
│  └────────────────────┘      └────────────────────┘     │
│                                                           │
│  📊 Stats Comparison:                                    │
│  Total Yards:  352 ━━━━━━━━━━━━━▓▓▓▓▓▓ 287             │
│  1st Downs:     18 ━━━━━━━━━━▓▓▓▓▓▓▓▓▓▓ 15             │
│  Possession: 18:23 ━━━━━━━━━━━━▓▓▓▓▓▓▓▓ 11:37          │
│                                                           │
│  🎯 Key Plays:                                           │
│  • 12:45 - 49ers TD: G. Kittle 15 yd pass from Purdy   │
│  • 14:32 - Seahawks FG: Myers 42 yards                  │
│                                                           │
│  [📺 Live Stream] [📊 Full Stats] [🔔 Game Alerts]     │
└──────────────────────────────────────────────────────────┘
```

**Real-Time Features:**
- **Score Change Animation**: Pulse effect + sound notification
- **Momentum Indicator**: Visual bar showing which team has momentum
- **Critical Moments**: Red border flash for touchdowns/goals
- **Live Play-by-Play**: Scrolling ticker at bottom

### Feature 3: Intelligent Alerting System

**Alert Types:**

1. **Score Alerts**:
   - Goal scored (NHL)
   - Touchdown/Field Goal (NFL)
   - End of period/quarter
   - Final score

2. **Game Status Alerts**:
   - Game starting (5 min warning)
   - Overtime starting
   - Close game (within 3 points/1 goal in final 5 minutes)
   - Blowout protection (turn off alerts if >21 point lead)

3. **Player Alerts** (Advanced):
   - Your favorite player scores
   - Hat trick watch (2 goals for player)
   - Injury updates

**Alert Configuration UI:**
```
┌─────────────────────────────────────────┐
│  🔔 Alert Preferences                   │
├─────────────────────────────────────────┤
│                                          │
│  Alert Method:                           │
│  ☑️ Browser Notification                │
│  ☑️ Dashboard Badge                     │
│  ☐ Email (for major events)            │
│  ☐ Home Assistant Notification          │
│                                          │
│  Alert Frequency:                        │
│  ⚫ Every Score                          │
│  ⚪ Quarter/Period Ends Only            │
│  ⚪ Final Scores Only                   │
│                                          │
│  Quiet Hours:                            │
│  From: [22:00] To: [08:00]              │
│  ☑️ Except for favorite teams           │
│                                          │
│  [Save Settings]                         │
└─────────────────────────────────────────┘
```

### Feature 4: Statistics Visualization

**Using Recharts for Interactive Charts:**

**1. Score Timeline (Line Chart)**:
```jsx
<ResponsiveContainer width="100%" height={300}>
  <LineChart data={scoreData}>
    <CartesianGrid strokeDasharray="3 3" />
    <XAxis dataKey="time" label="Game Time" />
    <YAxis label="Score" />
    <Tooltip />
    <Line type="monotone" dataKey="homeScore" stroke="#FF0000" name="Home" strokeWidth={2} />
    <Line type="monotone" dataKey="awayScore" stroke="#0000FF" name="Away" strokeWidth={2} />
  </LineChart>
</ResponsiveContainer>
```

**2. Team Stats Comparison (Horizontal Bar Chart)**:
- Passing Yards
- Rushing Yards
- Time of Possession
- Shots on Goal
- Power Play Efficiency

**3. Season Performance (Area Chart)**:
- Win/Loss trend over season
- Points accumulation
- Home vs Away performance

**4. Player Performance Radar Chart**:
- Multi-dimensional player stats
- Compare multiple players

### Feature 5: Historical Data & Analytics

**Season View:**
```
┌──────────────────────────────────────────────────────────┐
│  📈 Season Analytics - San Francisco 49ers               │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Record: 5-2  │  Division: 1st NFC West  │  Streak: W3  │
│                                                           │
│  [Last 10 Games Performance Chart]                       │
│                                                           │
│  Points Per Game:                                        │
│  Scored: 28.3 (Rank: 4th) ━━━━━━━━━━━━━━━━━━▓▓ 35      │
│  Allowed: 18.7 (Rank: 8th) ━━━━━━━━━━▓▓▓▓▓▓▓▓▓▓ 35     │
│                                                           │
│  Upcoming Schedule (Next 5 games):                       │
│  • Week 8: vs Cowboys (Home) - Projected: 62% win       │
│  • Week 9: @ Cardinals (Away) - Projected: 71% win      │
│                                                           │
│  [View Full Stats] [Compare Teams] [Playoff Scenarios]  │
└──────────────────────────────────────────────────────────┘
```

---

## 🎨 Visual Design System

### Color Scheme

**Dynamic Team Colors:**
- Automatically theme cards with team primary colors
- Maintain WCAG AA contrast ratios
- Subtle gradients for depth

**System Colors:**
- Live Games: `#00E676` (Green pulse)
- Upcoming: `#FFC107` (Amber)
- Completed: `#9E9E9E` (Gray)
- Favorite: `#FFD700` (Gold star)

### Typography

- **Scores**: Bold, 3rem, system-ui font
- **Team Names**: Semibold, 1.25rem
- **Stats**: Regular, 0.875rem
- **Timestamps**: Monospace font for consistency

### Spacing & Layout

- **Card Padding**: 1.5rem
- **Card Gap**: 1rem
- **Border Radius**: 0.75rem (modern, soft)
- **Shadow**: Subtle elevation with hover lift effect

### Animations

1. **Score Update**:
   - Scale animation (1 → 1.1 → 1)
   - Color flash
   - Duration: 600ms

2. **Live Indicator**:
   - Pulsing dot animation
   - Infinite loop, 2s duration

3. **Card Hover**:
   - Lift effect (translateY -4px)
   - Shadow intensification
   - Duration: 200ms

---

## 🔧 Configuration & Setup UX

### Initial Setup Flow

**Step 1: API Provider Selection**
```
┌─────────────────────────────────────────┐
│  🏈🏒 Sports Data Configuration          │
│                                          │
│  Select your data provider:              │
│                                          │
│  ⚪ ESPN API (Free tier: 100 calls/day) │
│     ✓ Real-time scores                  │
│     ✓ Team stats                        │
│     ✗ Limited historical data           │
│                                          │
│  ⚪ The Sports DB (Free, rate-limited)  │
│     ✓ Team information                  │
│     ✓ Historical data                   │
│     ✗ No real-time updates              │
│                                          │
│  ⚪ SportsData.io (Paid: from $19/mo)   │
│     ✓ Real-time play-by-play           │
│     ✓ Advanced statistics               │
│     ✓ Unlimited calls                   │
│                                          │
│  [Continue with ESPN API] [Compare →]   │
└─────────────────────────────────────────┘
```

**Step 2: API Key Entry**
```
┌─────────────────────────────────────────┐
│  🔑 ESPN API Configuration               │
│                                          │
│  API Key:                                │
│  [●●●●●●●●●●●●●●●●●●●●●●●●●●]          │
│                                          │
│  ℹ️ How to get an API key:              │
│  1. Visit developer.espn.com            │
│  2. Create free account                 │
│  3. Generate API key                    │
│                                          │
│  [Test Connection] [Save & Continue]    │
│                                          │
│  Status: ✅ Connected successfully       │
│  Rate Limit: 95 / 100 calls remaining   │
└─────────────────────────────────────────┘
```

**Step 3: Feature Selection**
```
┌─────────────────────────────────────────┐
│  ⚙️ Feature Configuration                │
│                                          │
│  Enable features:                        │
│                                          │
│  ☑️ NFL Integration                     │
│     ☑️ Live scores                      │
│     ☑️ Team statistics                  │
│     ☑️ Player statistics                │
│     ☐ Play-by-play (requires paid API) │
│                                          │
│  ☑️ NHL Integration                     │
│     ☑️ Live scores                      │
│     ☑️ Team statistics                  │
│     ☑️ Player statistics                │
│                                          │
│  Update Frequency:                       │
│  Live Games: [Every 15 seconds ▼]       │
│  Other Data: [Every 5 minutes ▼]        │
│                                          │
│  [Back] [Save Configuration]            │
└─────────────────────────────────────────┘
```

### Configuration Tab Integration

**Add to existing Configuration tab:**
```
┌─────────────────────────────────────────┐
│  ⚙️ Integration Configuration            │
├─────────────────────────────────────────┤
│                                          │
│  [🏠 Home Assistant]  [Configured ✓]   │
│  [☁️ Weather API]     [Configured ✓]   │
│  [💾 InfluxDB]        [Configured ✓]   │
│  [🏈 NFL Sports]      [Configure →]     │  ← NEW
│  [🏒 NHL Sports]      [Configure →]     │  ← NEW
│                                          │
└─────────────────────────────────────────┘
```

---

## 📊 Monitoring & Health Dashboard

### Service Health Monitoring

**Add to Services Tab:**
```
┌──────────────────────────────────────────┐
│  🌐 External Data Services (2)           │
├──────────────────────────────────────────┤
│                                           │
│  ┌────────────────────────────────────┐  │
│  │ 🏈 NFL Data Service                │  │
│  │ Status: 🟢 Running                 │  │
│  │ Provider: ESPN API                 │  │
│  │ Last Update: 5 seconds ago         │  │
│  │ Rate Limit: 87/100 calls           │  │
│  │ Cache Hit Rate: 78%                │  │
│  │ [View Details] [Configure]         │  │
│  └────────────────────────────────────┘  │
│                                           │
│  ┌────────────────────────────────────┐  │
│  │ 🏒 NHL Data Service                │  │
│  │ Status: 🟢 Running                 │  │
│  │ Provider: NHL Official API         │  │
│  │ Last Update: 12 seconds ago        │  │
│  │ Rate Limit: Unlimited              │  │
│  │ Cache Hit Rate: 85%                │  │
│  │ [View Details] [Configure]         │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

### Metrics Dashboard

**Add to Analytics Tab:**
```
┌──────────────────────────────────────────────────────────┐
│  📊 Sports Data Analytics (Last 24 Hours)                │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  API Call Statistics:                                    │
│  ┌────────────────┬────────────┬──────────┬───────────┐ │
│  │ Service        │ Total Calls│ Cached   │ Failed    │ │
│  ├────────────────┼────────────┼──────────┼───────────┤ │
│  │ NFL Data       │ 1,247      │ 978 (78%)│ 3 (0.2%)  │ │
│  │ NHL Data       │ 892        │ 758 (85%)│ 1 (0.1%)  │ │
│  └────────────────┴────────────┴──────────┴───────────┘ │
│                                                           │
│  [API Calls Over Time Chart]                             │
│                                                           │
│  Cache Performance:                                       │
│  Hit Rate: 82% ━━━━━━━━━━━━━━━━▓▓▓▓ 100%               │
│  Avg Response Time: 45ms (cached), 340ms (API)          │
│                                                           │
│  Data Freshness:                                         │
│  • Live Games: 15s average latency                       │
│  • Upcoming Games: 5m update cycle                       │
│  • Historical Data: 1h update cycle                      │
│                                                           │
│  [Export Report] [Configure Thresholds]                  │
└──────────────────────────────────────────────────────────┘
```

---

## 🚨 Alert & Notification System

### Alert Center UI

```
┌──────────────────────────────────────────────────────────┐
│  🚨 Sports Alerts Center                                 │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Active Alerts (5):                                      │
│                                                           │
│  ⚪ NEW 🏈 49ers score TD! Leading 24-17 (Q3)           │
│        2 seconds ago  [View Game] [Dismiss]              │
│                                                           │
│  ⚪ NEW 🏒 Bruins vs Maple Leafs starting in 5 minutes  │
│        5 minutes ago  [Watch] [Dismiss]                  │
│                                                           │
│  ⚫ 🏈 Cowboys game: Final Score DAL 31 - PHI 28        │
│        1 hour ago  [View Summary] [Dismiss]              │
│                                                           │
│  Alert History: [Today (12)] [This Week (47)] [All]     │
│                                                           │
│  Quick Actions:                                          │
│  [Mark All as Read] [Configure Alerts] [Clear History]  │
└──────────────────────────────────────────────────────────┘
```

### Browser Notifications

**Desktop Notification Example:**
```
┌─────────────────────────────────┐
│  🏈 HA Ingestor - NFL Alert     │
├─────────────────────────────────┤
│  TOUCHDOWN!                      │
│                                  │
│  San Francisco 49ers: 24        │
│  Seattle Seahawks: 17            │
│                                  │
│  G. Kittle 15 yd pass from Purdy│
│  Q3 - 12:45                      │
│                                  │
│  [View Game] [Dismiss]           │
└─────────────────────────────────┘
```

---

## 🎮 Mobile-Responsive Design

### Mobile View (< 768px)

**Stacked Layout:**
```
┌─────────────────────────┐
│  🏈🏒 Sports            │
│  [☰ Menu]   [🔔 3]     │
├─────────────────────────┤
│                         │
│  🟢 LIVE (3)            │
│                         │
│  ┌───────────────────┐ │
│  │ 🏈 Q3 12:45       │ │
│  │ 49ers     24      │ │
│  │ Seahawks  17      │ │
│  │ [Tap for details] │ │
│  └───────────────────┘ │
│                         │
│  ┌───────────────────┐ │
│  │ 🏒 P2 15:32       │ │
│  │ Bruins    2       │ │
│  │ Leafs     1       │ │
│  │ [Tap for details] │ │
│  └───────────────────┘ │
│                         │
│  📅 Upcoming (5) ▼     │
│                         │
└─────────────────────────┘
```

**Swipe Gestures:**
- Swipe left/right to navigate between games
- Swipe down to refresh
- Pinch to zoom on charts

---

## 💡 Advanced Features (Phase 2)

### 1. Fantasy Sports Integration
- Link to fantasy team
- Track your players across games
- Fantasy points calculator
- Lineup optimizer suggestions

### 2. Social Features
- Share game moments to Twitter/social media
- In-app chat for game discussions
- Community predictions and polls

### 3. Video Highlights
- Embedded video highlights (via YouTube API)
- Key play replays
- Post-game interviews

### 4. Betting/Odds Integration
- Live odds display (where legal)
- Line movement tracking
- Props tracking

### 5. Multi-Game View
- Picture-in-picture for multiple games
- Quad-view layout
- Auto-switch to close games in final minutes

### 6. Voice Assistant Integration
- "Alexa, what's the score of the 49ers game?"
- Home Assistant automation triggers
- TTS score updates

---

## 🛠️ Technical Implementation Notes

### API Integration Architecture

```python
# services/sports-data/src/sports_api_client.py

class SportsAPIClient:
    """Base client for sports data APIs"""
    
    def __init__(self, api_key: str, cache_ttl: int = 60):
        self.api_key = api_key
        self.cache = SportsCacheService(ttl=cache_ttl)
        
    async def get_live_games(self, league: str) -> List[Game]:
        """Fetch live games with caching"""
        cache_key = f"live_games_{league}"
        
        # Check cache first
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
            
        # Fetch from API
        games = await self._fetch_from_api(f"/v1/{league}/scoreboard")
        
        # Cache for 15 seconds during live games
        await self.cache.set(cache_key, games, ttl=15)
        
        return games
```

### Real-Time Updates with WebSocket

```typescript
// services/health-dashboard/src/hooks/useSportsLive.ts

export const useSportsLive = (gameId: string) => {
  const [gameData, setGameData] = useState<GameData | null>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);

  useEffect(() => {
    // Connect to WebSocket for real-time updates
    const websocket = new WebSocket(`ws://localhost:8005/games/${gameId}`);
    
    websocket.onmessage = (event) => {
      const update = JSON.parse(event.data);
      
      // Animate score change
      if (update.type === 'SCORE_UPDATE') {
        triggerScoreAnimation(update);
      }
      
      setGameData(update.gameData);
    };
    
    setWs(websocket);
    
    return () => websocket.close();
  }, [gameId]);

  return { gameData, isConnected: ws?.readyState === WebSocket.OPEN };
};
```

### Data Model

```typescript
// services/health-dashboard/src/types/sports.ts

export interface Game {
  id: string;
  league: 'NFL' | 'NHL';
  status: 'scheduled' | 'live' | 'final';
  startTime: string;
  
  homeTeam: Team;
  awayTeam: Team;
  
  score: {
    home: number;
    away: number;
  };
  
  period: {
    current: number;
    total: number;
    timeRemaining?: string;
  };
  
  stats?: GameStats;
  playByPlay?: Play[];
}

export interface Team {
  id: string;
  name: string;
  abbreviation: string;
  logo: string;
  colors: {
    primary: string;
    secondary: string;
  };
  record?: {
    wins: number;
    losses: number;
    ties?: number;
  };
}
```

---

## 📋 Implementation Checklist

### Phase 1: Core Features (MVP)
- [ ] API provider integration (ESPN or equivalent)
- [ ] Sports tab in dashboard
- [ ] Live game display with real-time updates
- [ ] Basic team personalization (favorites)
- [ ] Score change notifications
- [ ] Configuration UI for API setup
- [ ] Service health monitoring
- [ ] Mobile-responsive layout

### Phase 2: Enhanced Features
- [ ] Advanced statistics visualization (Recharts integration)
- [ ] Historical data and trends
- [ ] Enhanced alert system with customization
- [ ] Player statistics tracking
- [ ] Season analytics dashboard
- [ ] Team comparison tools

### Phase 3: Advanced Features
- [ ] Fantasy sports integration
- [ ] Video highlights
- [ ] Social features
- [ ] Multi-game view
- [ ] Voice assistant integration
- [ ] Betting/odds tracking (where legal)

---

## 🎯 Success Metrics

**User Engagement:**
- Daily active users viewing sports tab
- Average session duration on sports pages
- Number of favorite teams configured
- Alert interaction rate

**Technical Performance:**
- API response time < 500ms (95th percentile)
- Cache hit rate > 80%
- WebSocket connection stability > 99%
- UI render time < 100ms for score updates

**User Satisfaction:**
- Net Promoter Score (NPS)
- Feature usage analytics
- User feedback and feature requests

---

## 📚 Resources & References

### API Providers

**Free Tier:**
- [ESPN Hidden API](http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard) - Free, unofficial
- [The Sports DB](https://www.thesportsdb.com/api.php) - Free for non-commercial
- [NHL Official API](https://gitlab.com/dword4/nhlapi) - Free, comprehensive

**Paid Tier:**
- [SportsData.io](https://sportsdata.io/) - From $19/month
- [The Odds API](https://the-odds-api.com/) - From $49/month
- [RapidAPI Sports](https://rapidapi.com/hub) - Various pricing

### Design Inspiration

- [ESPN Mobile App](https://apps.apple.com/us/app/espn/id317469184)
- [The Score App](https://www.thescore.com/)
- [Yahoo Sports](https://sports.yahoo.com/)
- [NHL App](https://www.nhl.com/app)

### Technical Documentation

- [Recharts Documentation](https://recharts.org/)
- [React Documentation](https://react.dev/)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

---

## 🎨 Figma Design Files

*(To be created)*

- Wireframes for all views
- Interactive prototype
- Component library
- Color palette and typography system
- Icon set

---

## 📝 Notes

This design prioritizes:
1. **Real-time responsiveness** - Users want instant updates
2. **Visual hierarchy** - Live games always top priority
3. **Personalization** - Every user cares about different teams
4. **Mobile-first** - Many users check scores on phones
5. **Performance** - Fast loading, smooth animations
6. **Scalability** - Easy to add more leagues (MLB, NBA, MLS, etc.)

**Next Steps:**
1. Review and approve design concepts
2. Create detailed Figma mockups
3. Implement Phase 1 features
4. Beta test with real users
5. Iterate based on feedback

---

*Created: October 12, 2025*  
*Author: BMad Master (AI Assistant)*  
*Version: 1.0*

