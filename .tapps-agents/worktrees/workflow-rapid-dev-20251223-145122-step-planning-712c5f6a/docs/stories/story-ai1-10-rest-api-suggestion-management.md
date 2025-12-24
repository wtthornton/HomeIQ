# Story AI1.10: REST API - Suggestion Management

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.10  
**Priority:** High  
**Estimated Effort:** 8-10 hours  
**Dependencies:** Story AI1.9 (Scheduler and suggestions exist)

---

## User Story

**As a** frontend  
**I want** REST API endpoints for suggestion CRUD operations  
**so that** users can browse, approve, and reject suggestions

---

## Business Value

- Provides frontend with data access layer
- Enables suggestion management workflow
- Supports filtering and pagination for UX
- Foundation for user approval process

---

## Acceptance Criteria

1. ✅ List endpoint returns paginated suggestions
2. ✅ Filter by status (pending, approved, deployed, rejected)
3. ✅ Filter by confidence threshold (e.g., >80%)
4. ✅ Sort by date, confidence, category
5. ✅ Update suggestion status (pending → approved)
6. ✅ API response time <200ms for cached queries
7. ✅ OpenAPI documentation accessible at /docs
8. ✅ All endpoints return proper HTTP status codes (200, 404, 500)

---

## Technical Implementation Notes

### API Endpoints

**Create: src/api/suggestions.py**

**Reference: PRD Section 7.4**

```python
from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel
from src.database.models import Suggestion
from src.database.crud import get_suggestions, update_suggestion_status
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/suggestions", tags=["suggestions"])

# Response models
class SuggestionListItem(BaseModel):
    id: int
    title: str
    description: str
    confidence: float
    status: str
    created_at: str
    category: str

class SuggestionDetail(BaseModel):
    id: int
    title: str
    description: str
    automation_yaml: str
    rationale: str
    confidence: float
    status: str
    pattern_type: str
    created_at: str
    updated_at: str

class SuggestionListResponse(BaseModel):
    suggestions: List[SuggestionListItem]
    total: int
    page: int
    page_size: int

@router.get("/", response_model=SuggestionListResponse)
async def list_suggestions(
    status: Optional[str] = None,
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    sort_by: str = Query("confidence", regex="^(confidence|created_at|category)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List automation suggestions with filtering and pagination.
    
    Query Params:
        status: Filter by status (pending, approved, deployed, rejected)
        min_confidence: Minimum confidence threshold (0.0-1.0)
        sort_by: Sort field (confidence, created_at, category)
        sort_order: asc or desc
        page: Page number (1-indexed)
        page_size: Items per page (max 100)
    """
    
    try:
        suggestions, total = await get_suggestions(
            db,
            status=status,
            min_confidence=min_confidence,
            sort_by=sort_by,
            sort_order=sort_order,
            offset=(page - 1) * page_size,
            limit=page_size
        )
        
        return SuggestionListResponse(
            suggestions=[SuggestionListItem(**s.dict()) for s in suggestions],
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing suggestions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch suggestions")

@router.get("/{suggestion_id}", response_model=SuggestionDetail)
async def get_suggestion_detail(
    suggestion_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed view of a single suggestion"""
    
    suggestion = await get_suggestion_by_id(db, suggestion_id)
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    return SuggestionDetail(**suggestion.dict())

@router.patch("/{suggestion_id}")
async def update_suggestion(
    suggestion_id: int,
    status: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Update suggestion status.
    
    Status transitions:
        pending → approved
        pending → rejected
        approved → pending (undo)
    """
    
    valid_statuses = ['pending', 'approved', 'rejected']
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    success = await update_suggestion_status(db, suggestion_id, status)
    
    if not success:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    logger.info(f"Suggestion {suggestion_id} status updated to {status}")
    
    return {"success": True, "suggestion_id": suggestion_id, "status": status}
```

### Database CRUD Operations

**Create: src/database/crud.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.database.models import Suggestion, Pattern
from typing import List, Tuple, Optional

async def get_suggestions(
    db: AsyncSession,
    status: Optional[str] = None,
    min_confidence: float = 0.0,
    sort_by: str = "confidence",
    sort_order: str = "desc",
    offset: int = 0,
    limit: int = 10
) -> Tuple[List[Suggestion], int]:
    """
    Query suggestions with filtering, sorting, and pagination.
    """
    
    query = select(Suggestion)
    
    # Apply filters
    if status:
        query = query.where(Suggestion.status == status)
    
    if min_confidence > 0:
        query = query.where(Suggestion.confidence >= min_confidence)
    
    # Apply sorting
    if sort_by == "confidence":
        order_col = Suggestion.confidence
    elif sort_by == "created_at":
        order_col = Suggestion.created_at
    elif sort_by == "category":
        order_col = Suggestion.category
    
    if sort_order == "desc":
        query = query.order_by(order_col.desc())
    else:
        query = query.order_by(order_col.asc())
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    suggestions = result.scalars().all()
    
    return suggestions, total
```

---

## Integration Verification

**IV1: API endpoints don't conflict with existing APIs**
- Port 8011 (AI service) separate from 8003 (admin-api) and 8006 (data-api)
- No route conflicts
- OpenAPI docs don't overlap

**IV2: Port 8011 accessible from frontend**
- Frontend can reach http://localhost:8011
- CORS configured for localhost:3002
- Network connectivity verified

**IV3: CORS configured for localhost:3002**
- CORSMiddleware allows frontend origin
- Preflight requests handled
- Credentials supported

**IV4: API follows existing FastAPI patterns**
- Uses same Pydantic models approach
- Follows same error handling
- Consistent response formats

---

## Tasks Breakdown

1. **Create suggestions router** (2 hours)
2. **Implement GET /api/suggestions (list)** (2 hours)
3. **Implement GET /api/suggestions/{id} (detail)** (1 hour)
4. **Implement PATCH /api/suggestions/{id} (update)** (1.5 hours)
5. **Add pagination support** (1 hour)
6. **Add filtering and sorting** (1.5 hours)
7. **Create Pydantic response models** (1 hour)
8. **Unit tests for all endpoints** (2 hours)
9. **OpenAPI documentation** (0.5 hours)

**Total:** 8-10 hours

---

## Testing Strategy

### Unit Tests

```python
# tests/test_suggestions_api.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_list_suggestions():
    """Test GET /api/suggestions"""
    response = client.get("/api/suggestions")
    
    assert response.status_code == 200
    data = response.json()
    assert 'suggestions' in data
    assert 'total' in data
    assert 'page' in data

def test_filter_by_status():
    """Test filtering by status"""
    response = client.get("/api/suggestions?status=pending")
    
    assert response.status_code == 200
    suggestions = response.json()['suggestions']
    assert all(s['status'] == 'pending' for s in suggestions)

def test_pagination():
    """Test pagination works correctly"""
    # Page 1
    page1 = client.get("/api/suggestions?page=1&page_size=5")
    # Page 2
    page2 = client.get("/api/suggestions?page=2&page_size=5")
    
    # Should be different results
    assert page1.json()['suggestions'] != page2.json()['suggestions']

def test_update_suggestion_status():
    """Test PATCH /api/suggestions/{id}"""
    response = client.patch("/api/suggestions/1", json={"status": "approved"})
    
    assert response.status_code == 200
    assert response.json()['status'] == 'approved'
```

---

## Definition of Done

- [ ] Suggestions router implemented
- [ ] List endpoint with filters/sorting/pagination
- [ ] Detail endpoint returning full suggestion
- [ ] Update endpoint for status changes
- [ ] Pydantic models for type safety
- [ ] CRUD operations in database layer
- [ ] API response time <200ms (cached)
- [ ] OpenAPI docs complete
- [ ] Unit tests pass (80%+ coverage)
- [ ] CORS configured correctly
- [ ] Code reviewed and approved

---

## Reference Files

**Copy patterns from:**
- `services/admin-api/src/health_endpoints.py` - FastAPI patterns
- `services/data-api/src/devices_endpoints.py` - Pagination examples
- PRD Section 7.4 (API specifications)

---

## Notes

- Keep endpoints simple (CRUD only)
- Pagination required (may have 100+ suggestions over time)
- Filtering critical for UX (show pending only)
- Sorting by confidence helps users prioritize
- OpenAPI docs auto-generated by FastAPI

---

**Story Status:** Not Started  
**Assigned To:** TBD  
**Created:** 2025-10-15  
**Updated:** 2025-10-15

