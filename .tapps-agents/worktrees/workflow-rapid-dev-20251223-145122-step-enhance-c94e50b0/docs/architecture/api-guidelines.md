# API Guidelines

This document provides comprehensive guidelines for designing, implementing, and maintaining APIs within the Home Assistant Ingestor project.

## API Design Principles

### RESTful API Design

#### Resource-Based URLs
- Use nouns, not verbs in URLs
- Use plural nouns for collections
- Use hierarchical structure for related resources

```
# Good
GET    /api/v1/events
POST   /api/v1/events
GET    /api/v1/events/{event_id}
PUT    /api/v1/events/{event_id}
DELETE /api/v1/events/{event_id}

# Bad
GET    /api/v1/getEvents
POST   /api/v1/createEvent
GET    /api/v1/eventDetails/{event_id}
```

#### HTTP Methods
- **GET** - Retrieve data (idempotent)
- **POST** - Create new resources
- **PUT** - Update entire resource (idempotent)
- **PATCH** - Partial update
- **DELETE** - Remove resource (idempotent)

### API Versioning Strategy

#### URL Versioning
```
/api/v1/events
/api/v2/events
```

#### Header Versioning
```http
Accept: application/vnd.api+json;version=1
```

#### Implementation Example
```python
# services/admin-api/src/main.py
from fastapi import APIRouter

# Version 1 API
v1_router = APIRouter(prefix="/api/v1", tags=["v1"])

@v1_router.get("/events")
async def get_events_v1():
    """Get events - API version 1"""
    pass

# Version 2 API
v2_router = APIRouter(prefix="/api/v2", tags=["v2"])

@v2_router.get("/events")
async def get_events_v2():
    """Get events - API version 2 with enhanced features"""
    pass

# Include both versions
app.include_router(v1_router)
app.include_router(v2_router)
```

## Request/Response Standards

### Request Format

#### Standard Request Headers
```http
Content-Type: application/json
Accept: application/json
Authorization: Bearer <token>
X-Request-ID: <unique-id>
X-Client-Version: 1.0.0
```

#### Query Parameters
```python
# services/admin-api/src/events_endpoints.py
from fastapi import Query, Path
from typing import Optional
from datetime import datetime

@router.get("/events")
async def get_events(
    limit: int = Query(10, ge=1, le=100, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    sort_by: str = Query("timestamp", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order")
):
    """Get events with filtering and pagination"""
    pass
```

### Response Format

#### Standard Response Structure
```python
# services/admin-api/src/models.py
from pydantic import BaseModel
from typing import Optional, Any, List
from datetime import datetime

class APIResponse(BaseModel):
    """Standard API response model"""
    success: bool = True
    data: Optional[Any] = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None

class PaginatedResponse(BaseModel):
    """Paginated response model"""
    success: bool = True
    data: List[Any]
    pagination: dict = {
        "limit": int,
        "offset": int,
        "total": int,
        "has_next": bool,
        "has_prev": bool
    }
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None

class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: dict = {
        "code": str,
        "message": str,
        "details": Optional[dict] = None,
        "timestamp": datetime,
        "request_id": Optional[str] = None
    }
```

#### Response Examples
```python
# Success Response
{
    "success": true,
    "data": {
        "events": [
            {
                "id": "event_123",
                "entity_id": "sensor.temperature",
                "state": "22.5",
                "timestamp": "2024-01-27T10:00:00Z",
                "attributes": {
                    "unit_of_measurement": "°C",
                    "friendly_name": "Temperature"
                }
            }
        ]
    },
    "message": "Events retrieved successfully",
    "timestamp": "2024-01-27T10:00:00Z",
    "request_id": "req_456"
}

# Error Response
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid input parameters",
        "details": {
            "field": "limit",
            "message": "Value must be between 1 and 100"
        },
        "timestamp": "2024-01-27T10:00:00Z",
        "request_id": "req_456"
    }
}
```

## Authentication & Authorization

### Token-Based Authentication

#### JWT Token Implementation
```python
# services/admin-api/src/auth.py
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

class AuthManager:
    def __init__(self):
        self.secret_key = os.getenv('JWT_SECRET_KEY')
        self.algorithm = os.getenv('JWT_ALGORITHM', 'HS256')
        self.token_expiry = timedelta(hours=24)
    
    def create_token(self, user_id: str, roles: List[str]) -> str:
        """Create JWT token"""
        payload = {
            'user_id': user_id,
            'roles': roles,
            'exp': datetime.utcnow() + self.token_expiry,
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def validate_token(self, token: str) -> dict:
        """Validate JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

# Dependency for protected endpoints
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from token"""
    auth_manager = AuthManager()
    payload = auth_manager.validate_token(credentials.credentials)
    return payload
```

#### Role-Based Authorization
```python
# services/admin-api/src/auth.py
from enum import Enum

class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"

def require_role(required_role: Role):
    """Decorator for role-based authorization"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            user_roles = current_user.get('roles', [])
            if required_role not in user_roles:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage example
@router.get("/admin/users")
@require_role(Role.ADMIN)
async def get_users(current_user: dict = Depends(get_current_user)):
    """Get all users - Admin only"""
    pass
```

## Error Handling

### Standard Error Codes

#### HTTP Status Codes
- **200 OK** - Successful request
- **201 Created** - Resource created successfully
- **400 Bad Request** - Invalid request parameters
- **401 Unauthorized** - Authentication required
- **403 Forbidden** - Insufficient permissions
- **404 Not Found** - Resource not found
- **422 Unprocessable Entity** - Validation error
- **500 Internal Server Error** - Server error

#### Custom Error Codes
```python
# services/admin-api/src/errors.py
class APIError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 500, details: dict = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}

# Common error codes
class ErrorCodes:
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
```

### Error Handling Implementation

#### Global Exception Handler
```python
# services/admin-api/src/main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """Handle custom API errors"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": getattr(request.state, 'request_id', None)
            }
        }
    )

@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": ErrorCodes.VALIDATION_ERROR,
                "message": "Validation error",
                "details": {"validation_errors": exc.errors()},
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": getattr(request.state, 'request_id', None)
            }
        }
    )
```

## Rate Limiting

### Rate Limiting Implementation

#### Token Bucket Algorithm
```python
# services/admin-api/src/rate_limiter.py
import time
from collections import defaultdict
from typing import Dict, Tuple

class RateLimiter:
    def __init__(self):
        self.buckets: Dict[str, Dict[str, float]] = defaultdict(lambda: {
            'tokens': 0,
            'last_refill': time.time()
        })
    
    def is_allowed(self, key: str, limit: int, window: int) -> Tuple[bool, dict]:
        """Check if request is allowed"""
        now = time.time()
        bucket = self.buckets[key]
        
        # Refill tokens
        time_passed = now - bucket['last_refill']
        tokens_to_add = time_passed * (limit / window)
        bucket['tokens'] = min(limit, bucket['tokens'] + tokens_to_add)
        bucket['last_refill'] = now
        
        # Check if request is allowed
        if bucket['tokens'] >= 1:
            bucket['tokens'] -= 1
            return True, {
                'limit': limit,
                'remaining': int(bucket['tokens']),
                'reset_time': int(now + window)
            }
        else:
            return False, {
                'limit': limit,
                'remaining': 0,
                'reset_time': int(now + window)
            }

# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    client_ip = request.client.host
    rate_limiter = RateLimiter()
    
    # Check rate limit
    allowed, info = rate_limiter.is_allowed(
        key=client_ip,
        limit=100,  # 100 requests
        window=3600  # per hour
    )
    
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "success": False,
                "error": {
                    "code": ErrorCodes.RATE_LIMIT_EXCEEDED,
                    "message": "Rate limit exceeded",
                    "details": info
                }
            },
            headers={
                "X-RateLimit-Limit": str(info['limit']),
                "X-RateLimit-Remaining": str(info['remaining']),
                "X-RateLimit-Reset": str(info['reset_time'])
            }
        )
    
    response = await call_next(request)
    
    # Add rate limit headers
    response.headers["X-RateLimit-Limit"] = str(info['limit'])
    response.headers["X-RateLimit-Remaining"] = str(info['remaining'])
    response.headers["X-RateLimit-Reset"] = str(info['reset_time'])
    
    return response
```

## API Documentation

### OpenAPI/Swagger Documentation

#### Automatic Documentation Generation
```python
# services/admin-api/src/main.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="Home Assistant Ingestor API",
    description="API for managing Home Assistant data ingestion and monitoring",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Home Assistant Ingestor API",
        version="1.0.0",
        description="API for managing Home Assistant data ingestion and monitoring",
        routes=app.routes,
    )
    
    # Add custom tags
    openapi_schema["tags"] = [
        {
            "name": "Health",
            "description": "Health check and monitoring endpoints"
        },
        {
            "name": "Events",
            "description": "Event data management endpoints"
        },
        {
            "name": "Statistics",
            "description": "Statistical data endpoints"
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

#### Detailed Endpoint Documentation
```python
# services/admin-api/src/events_endpoints.py
@router.post(
    "/events",
    response_model=APIResponse,
    summary="Create new event",
    description="Create a new Home Assistant event in the system",
    responses={
        201: {
            "description": "Event created successfully",
            "model": APIResponse
        },
        400: {
            "description": "Validation error",
            "model": ErrorResponse
        },
        401: {
            "description": "Authentication required",
            "model": ErrorResponse
        }
    },
    tags=["Events"]
)
async def create_event(
    event: EventCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new Home Assistant event.
    
    This endpoint allows authenticated users to create new events
    in the Home Assistant Ingestor system.
    
    Args:
        event: Event data to create
        current_user: Current authenticated user
        
    Returns:
        APIResponse: Created event information
        
    Raises:
        ValidationError: If event data is invalid
        AuthenticationError: If user is not authenticated
    """
    pass
```

## API Testing

### Unit Testing

#### API Endpoint Testing
```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from services.admin-api.src.main import app

client = TestClient(app)

def test_get_events():
    """Test GET /api/v1/events endpoint"""
    response = client.get("/api/v1/events")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert "timestamp" in data

def test_create_event():
    """Test POST /api/v1/events endpoint"""
    event_data = {
        "entity_id": "sensor.temperature",
        "state": "22.5",
        "attributes": {
            "unit_of_measurement": "°C"
        }
    }
    
    response = client.post("/api/v1/events", json=event_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["entity_id"] == "sensor.temperature"

def test_rate_limiting():
    """Test rate limiting functionality"""
    # Make multiple requests quickly
    for _ in range(101):  # Exceed rate limit
        response = client.get("/api/v1/events")
    
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["error"]["message"]
```

### Integration Testing

#### API Integration Tests
```python
# tests/test_api_integration.py
import pytest
import asyncio
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_event_lifecycle():
    """Test complete event lifecycle"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create event
        event_data = {
            "entity_id": "sensor.temperature",
            "state": "22.5"
        }
        
        response = await client.post("/api/v1/events", json=event_data)
        assert response.status_code == 201
        
        event_id = response.json()["data"]["id"]
        
        # Get event
        response = await client.get(f"/api/v1/events/{event_id}")
        assert response.status_code == 200
        
        # Update event
        update_data = {"state": "23.0"}
        response = await client.patch(f"/api/v1/events/{event_id}", json=update_data)
        assert response.status_code == 200
        
        # Delete event
        response = await client.delete(f"/api/v1/events/{event_id}")
        assert response.status_code == 200
        
        # Verify deletion
        response = await client.get(f"/api/v1/events/{event_id}")
        assert response.status_code == 404
```

## Performance Optimization

### Caching Strategy

#### Response Caching
```python
# services/admin-api/src/cache.py
import redis
import json
from typing import Optional, Any

class CacheManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=0
        )
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception:
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 300):
        """Set cached value with TTL"""
        try:
            self.redis_client.setex(key, ttl, json.dumps(value))
        except Exception:
            pass

# Caching decorator
def cache_response(ttl: int = 300):
    """Cache response for specified TTL"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache_manager = CacheManager()
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

# Usage example
@router.get("/events/stats")
@cache_response(ttl=600)  # Cache for 10 minutes
async def get_event_stats():
    """Get event statistics - cached"""
    pass
```

### Database Optimization

#### Query Optimization
```python
# services/admin-api/src/database.py
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

class EventRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_events_paginated(self, limit: int, offset: int, filters: dict):
        """Get events with pagination and filtering"""
        query = self.db.query(Event)
        
        # Apply filters
        if filters.get('entity_id'):
            query = query.filter(Event.entity_id == filters['entity_id'])
        
        if filters.get('start_time'):
            query = query.filter(Event.timestamp >= filters['start_time'])
        
        if filters.get('end_time'):
            query = query.filter(Event.timestamp <= filters['end_time'])
        
        # Apply ordering
        query = query.order_by(desc(Event.timestamp))
        
        # Apply pagination
        total = query.count()
        events = query.offset(offset).limit(limit).all()
        
        return {
            'events': events,
            'total': total,
            'has_next': offset + limit < total,
            'has_prev': offset > 0
        }
```

## Real-Time Metrics API (Epic 23)

### Standardized Event Rate Endpoint

All microservices expose a standardized `/api/v1/event-rate` endpoint for real-time metrics collection.

#### Endpoint Specification

```
GET /api/v1/event-rate
```

**Response Format**:
```json
{
  "service": "service-name",
  "events_per_second": 0.0,
  "events_per_hour": 0.0,
  "total_events_processed": 0,
  "uptime_seconds": 3600.0,
  "processing_stats": {
    "is_running": true,
    "max_workers": 4,
    "active_workers": 2,
    "processed_events": 1000,
    "failed_events": 10,
    "success_rate": 99.0,
    "processing_rate_per_second": 0.5,
    "average_processing_time_ms": 100.0,
    "queue_size": 5,
    "queue_maxsize": 1000,
    "uptime_seconds": 3600.0,
    "last_processing_time": "2024-01-15T10:30:00.000Z",
    "event_handlers_count": 8
  },
  "connection_stats": {
    "is_connected": true,
    "is_subscribed": false,
    "total_events_received": 1000,
    "events_by_type": {
      "event_type_1": 400,
      "event_type_2": 300,
      "event_type_3": 200,
      "event_type_4": 100
    },
    "last_event_time": "2024-01-15T10:30:00.000Z"
  },
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**Services Implementing This Endpoint**:
- websocket-ingestion (port 8000)
- admin-api (port 8001)
- enrichment-pipeline (port 8002)
- data-api (port 8006)
- ai-automation-service (port 8008)
- air-quality-service (port 8010)
- calendar-service (port 8011)
- carbon-intensity-service (port 8012)
- data-retention (port 8013)
- electricity-pricing-service (port 8014)
- energy-correlator (port 8015)
- smart-meter-service (port 8016)
- sports-api (port 8018)
- sports-data (port 8019)
- weather-api (port 8020)

### Consolidated Metrics Endpoint

The Admin API provides a consolidated endpoint that aggregates metrics from all services.

#### Endpoint Specification

```
GET /api/v1/real-time-metrics
```

**Features**:
- Parallel collection from all 15 services
- Individual timeouts per service (3-10s based on priority)
- Overall timeout protection (15s)
- Fallback metrics for unavailable services
- Health scoring and status categorization

**Response Format**:
```json
{
  "events_per_second": 0.0,
  "api_calls_active": 5,
  "data_sources_active": ["home_assistant", "weather_api", "sports_api"],
  "api_metrics": [
    {
      "service": "websocket-ingestion",
      "events_per_second": 2.5,
      "events_per_hour": 9000.0,
      "uptime_seconds": 3600.0,
      "status": "active",
      "response_time_ms": 150,
      "last_success": "2024-01-15T10:30:00.000Z"
    },
    {
      "service": "data-api",
      "events_per_second": 0.0,
      "events_per_hour": 0.0,
      "uptime_seconds": 0.0,
      "status": "timeout",
      "response_time_ms": null,
      "last_success": null,
      "error_message": "Timeout after 5s",
      "is_fallback": true
    }
  ],
  "inactive_apis": 5,
  "error_apis": 2,
  "total_apis": 15,
  "health_summary": {
    "healthy": 8,
    "unhealthy": 7,
    "total": 15,
    "health_percentage": 53.3
  },
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**Status Values**:
- `active` - Service responding normally with events
- `inactive` - Service responding but no events processing
- `timeout` - Service didn't respond within timeout
- `not_configured` - Service URL not configured
- `error` - Service returned an error

**Implementation Details**:
- Uses `asyncio.gather()` for parallel requests
- Implements per-service timeout configuration
- Graceful degradation with fallback metrics
- Error message propagation for debugging

**Usage Example**:
```typescript
// Frontend polling example
const { metrics, loading, error } = useRealTimeMetrics(5000); // 5s polling

// Access metrics
console.log(`Active APIs: ${metrics.api_calls_active}`);
console.log(`Health: ${metrics.health_summary.health_percentage}%`);
console.log(`Events/hour: ${metrics.api_metrics[0].events_per_hour}`);
```

These API guidelines ensure consistent, secure, and performant API design and implementation across the Home Assistant Ingestor project.
