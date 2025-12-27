# Story 22.4: User Preferences Storage (Optional)

**Epic:** Epic 22 - SQLite Metadata Storage  
**Status:** Cancelled  
**Created:** 2025-01-14  
**Cancelled:** 2025-01-14  
**Story Points:** 3  
**Priority:** Low (Optional)  
**Depends On:** Story 22.1

---

## Story

**As a** user,  
**I want** my team selections and preferences persisted on the server,  
**so that** my settings work across devices and sessions.

---

## Story Context

**Existing System Integration:**

- **Integrates with:** Story 22.1 (SQLite infrastructure)
- **Technology:** Python 3.11, FastAPI 0.104.1, React 18, TypeScript 5.2
- **Follows pattern:** Simple CRUD pattern for user settings
- **Touch points:**
  - Dashboard localStorage (current storage)
  - Environment variables for team selection (current)
  - SQLite database (new storage)
  - New API endpoints for preferences

**Current Behavior:**
- Team selections stored in environment variables
- Dashboard preferences stored in browser localStorage
- No server-side persistence
- Settings lost when switching devices
- No user-specific customization

**New Behavior:**
- User preferences stored in SQLite `user_preferences` table
- Server-side persistence across devices
- API endpoints for reading/writing preferences
- Dashboard loads preferences from API
- Default preferences for new users
- Simple single-user model (user_id = 'default')

---

## Acceptance Criteria

**Functional Requirements:**

1. `user_preferences` table created with schema (user_id PK, selected_teams JSON, notification_settings JSON, updated_at) (AC#1)
2. Alembic migration created for user_preferences table (AC#2)
3. GET `/api/user/preferences` endpoint returns user preferences (AC#3)
4. POST `/api/user/preferences` endpoint saves preferences (AC#4)
5. Dashboard loads preferences from API on startup (AC#5)
6. Dashboard saves preferences to API on change (AC#6)

**Integration Requirements:**

7. Default preferences created for new users (AC#7)
8. Migration imports existing preferences from environment variables (AC#8)
9. Dashboard falls back to localStorage if API unavailable (AC#9)
10. Preferences include selected teams (NFL/NHL) and notification settings (AC#10)

**Quality Requirements:**

11. Preferences stored as JSON strings for flexibility (AC#11)
12. Simple single-user model (user_id='default') for small app (AC#12)
13. Unit tests cover preferences CRUD operations (AC#13)
14. Integration tests verify API endpoints and dashboard integration (AC#14)
15. No breaking changes to existing dashboard behavior (AC#15)

---

## Tasks / Subtasks

- [ ] **Task 1: Create SQLAlchemy model** (AC: 1, 11, 12)
  - [ ] Create `services/data-api/src/models/user_preference.py`
  - [ ] Define `UserPreference` model
  - [ ] Use 'default' as default user_id
  - [ ] Store selected_teams as JSON string
  - [ ] Store notification_settings as JSON string
  - [ ] Add updated_at timestamp

- [ ] **Task 2: Create Alembic migration** (AC: 2)
  - [ ] Generate migration: `alembic revision --autogenerate -m "add user_preferences"`
  - [ ] Review migration script
  - [ ] Add default row for user_id='default'
  - [ ] Test migration: `alembic upgrade head`

- [ ] **Task 3: Create migration script from env vars** (AC: 8)
  - [ ] Create `services/data-api/src/migrate_preferences.py`
  - [ ] Read SELECTED_TEAMS from environment
  - [ ] Parse team selections
  - [ ] Create default preferences object
  - [ ] Insert into SQLite
  - [ ] Log migration results

- [ ] **Task 4: Create preferences API endpoints** (AC: 3, 4, 7)
  - [ ] Create `services/data-api/src/preferences_endpoints.py`
  - [ ] Implement GET `/api/user/preferences`
  - [ ] Implement POST `/api/user/preferences`
  - [ ] Create default preferences if not exist
  - [ ] Validate preference structure
  - [ ] Return 200 with preferences JSON

- [ ] **Task 5: Create Pydantic models** (AC: 10)
  - [ ] Create `UserPreferencesRequest` model
  - [ ] Create `UserPreferencesResponse` model
  - [ ] Define selected_teams structure (nfl_teams, nhl_teams)
  - [ ] Define notification_settings structure
  - [ ] Add validation rules

- [ ] **Task 6: Update dashboard to use API** (AC: 5, 6, 9)
  - [ ] Create `src/services/preferences.ts`
  - [ ] Implement `getPreferences()` API call
  - [ ] Implement `savePreferences()` API call
  - [ ] Update Sports tab to load from API
  - [ ] Update Sports tab to save to API
  - [ ] Keep localStorage as fallback
  - [ ] Add loading states

- [ ] **Task 7: Add preferences context** (AC: 5, 6)
  - [ ] Create `src/contexts/PreferencesContext.tsx`
  - [ ] Load preferences on app startup
  - [ ] Provide preferences to components
  - [ ] Handle save operations
  - [ ] Show error notifications

- [ ] **Task 8: Write unit tests** (AC: 13)
  - [ ] Test UserPreference model
  - [ ] Test preferences endpoints
  - [ ] Test default preferences creation
  - [ ] Test preference validation
  - [ ] Test update operations

- [ ] **Task 9: Write integration tests** (AC: 14)
  - [ ] Test GET `/api/user/preferences`
  - [ ] Test POST `/api/user/preferences`
  - [ ] Test dashboard loads preferences
  - [ ] Test dashboard saves preferences
  - [ ] Test fallback to localStorage

- [ ] **Task 10: Documentation** (AC: 15)
  - [ ] Update data-api README
  - [ ] Document preferences API
  - [ ] Document preference structure
  - [ ] Update dashboard README
  - [ ] Document migration process

---

## Dev Notes

### Project Context

**Database Schema:**
```sql
CREATE TABLE user_preferences (
    user_id TEXT PRIMARY KEY DEFAULT 'default',
    selected_teams TEXT,  -- JSON: {"nfl": ["sf", "dal"], "nhl": ["bos"]}
    notification_settings TEXT,  -- JSON: {"gameStart": true, "scoreChange": true}
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**SQLAlchemy Model:**
```python
# models/user_preference.py
from sqlalchemy import Column, String, DateTime
from datetime import datetime
from ..database import Base

class UserPreference(Base):
    __tablename__ = "user_preferences"
    
    user_id = Column(String, primary_key=True, default='default')
    selected_teams = Column(String)  # JSON string
    notification_settings = Column(String)  # JSON string
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Pydantic Models:**
```python
# Pydantic models
class SelectedTeams(BaseModel):
    nfl: List[str] = []
    nhl: List[str] = []

class NotificationSettings(BaseModel):
    game_start: bool = True
    score_change: bool = True
    game_end: bool = True

class UserPreferencesRequest(BaseModel):
    selected_teams: SelectedTeams
    notification_settings: NotificationSettings

class UserPreferencesResponse(BaseModel):
    user_id: str
    selected_teams: SelectedTeams
    notification_settings: NotificationSettings
    updated_at: datetime
```

**API Endpoints:**
```python
# preferences_endpoints.py
@router.get("/api/user/preferences", response_model=UserPreferencesResponse)
async def get_preferences(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == 'default')
    )
    pref = result.scalar_one_or_none()
    
    if not pref:
        # Create default
        pref = UserPreference(
            user_id='default',
            selected_teams='{"nfl": [], "nhl": []}',
            notification_settings='{"game_start": true, "score_change": true}'
        )
        db.add(pref)
        await db.commit()
    
    return {
        "user_id": pref.user_id,
        "selected_teams": json.loads(pref.selected_teams),
        "notification_settings": json.loads(pref.notification_settings),
        "updated_at": pref.updated_at
    }

@router.post("/api/user/preferences")
async def save_preferences(
    preferences: UserPreferencesRequest,
    db: AsyncSession = Depends(get_db)
):
    pref = UserPreference(
        user_id='default',
        selected_teams=json.dumps(preferences.selected_teams.dict()),
        notification_settings=json.dumps(preferences.notification_settings.dict())
    )
    await db.merge(pref)  # Upsert
    await db.commit()
    return {"success": True}
```

**Dashboard Integration:**
```typescript
// src/services/preferences.ts
export const getPreferences = async (): Promise<UserPreferences> => {
  try {
    const response = await fetch('http://localhost:8006/api/user/preferences');
    return await response.json();
  } catch (error) {
    // Fallback to localStorage
    const stored = localStorage.getItem('user-preferences');
    return stored ? JSON.parse(stored) : DEFAULT_PREFERENCES;
  }
};

export const savePreferences = async (prefs: UserPreferences): Promise<void> => {
  try {
    await fetch('http://localhost:8006/api/user/preferences', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(prefs)
    });
    // Also save to localStorage as backup
    localStorage.setItem('user-preferences', JSON.stringify(prefs));
  } catch (error) {
    console.error('Failed to save preferences:', error);
    localStorage.setItem('user-preferences', JSON.stringify(prefs));
  }
};
```

**Key Reference Files:**
- Sports Tab: `services/health-dashboard/src/components/tabs/SportsTab.tsx`
- Context7 KB: `docs/kb/context7-cache/libraries/sqlite/fastapi-best-practices.md`

---

## Testing

### Unit Tests (Backend)
```python
# tests/test_preferences.py
async def test_create_default_preferences()
async def test_get_preferences()
async def test_save_preferences()
async def test_preferences_updated_at()
```

### Unit Tests (Frontend)
```typescript
// tests/preferences.test.ts
test('loads preferences from API')
test('saves preferences to API')
test('falls back to localStorage on API error')
```

### Integration Tests
```python
# tests/test_preferences_integration.py
async def test_preferences_api_flow()
async def test_dashboard_integration()
```

---

## File List

_(To be filled during development)_

---

## Dev Agent Record

### Agent Model Used
- GPT-4 / Claude Sonnet 4.5

### Debug Log References
- See: `.ai/debug-log.md`

### Completion Notes
_(To be filled upon completion)_

### Change Log
_(To be filled during development)_

---

## Cancellation Reason

**Cancelled by user on 2025-01-14**

**Rationale:**
- localStorage already works well for single-user app
- Environment variables sufficient for team selection
- Not critical for core functionality
- Can be implemented later if multi-device usage increases
- Keeping the system simple per project philosophy

**Impact**: None - Epic 22 core goals achieved without this story

---

## Definition of Done Checklist

- [x] Story cancelled per user request
- [x] No implementation needed
- [x] May be reconsidered in future if requirements change

