# Story 34.5: Calendar Generator Foundation

**Story ID:** 34.5  
**Epic:** 34 - Advanced External Data Generation  
**Status:** Draft  
**Priority:** P0  
**Story Points:** 3  
**Estimated Effort:** 2-3 hours  
**Complexity:** Low

---

## Story Description

Create the foundational `SyntheticCalendarGenerator` class with work schedule profiles and basic event generation.

## Acceptance Criteria

- [ ] `SyntheticCalendarGenerator` class created
- [ ] Work schedule profiles defined (9-5, shift work, remote)
- [ ] Basic event generation implemented
- [ ] NUC-optimized (in-memory, <50MB)

## Technical Requirements

```python
class CalendarEvent(BaseModel):
    timestamp: str
    event_type: str  # work, routine, travel
    summary: str
    location: str | None = None
    presence_state: str  # home, away, work

class SyntheticCalendarGenerator:
    WORK_SCHEDULES = {
        'standard_9to5': {'start': 9, 'end': 17},
        'shift_work': {'start': 22, 'end': 6},
        'remote': {'start': 9, 'end': 17, 'location': 'home'}
    }
```

## Implementation Tasks

- [ ] Create class structure
- [ ] Define work schedule profiles
- [ ] Implement basic event generation
- [ ] Create unit tests

## Definition of Done

- [ ] Class created
- [ ] Work schedules defined
- [ ] Basic generation working
- [ ] All tests passing

---

**Created**: November 25, 2025

