# Admin API Service

Tier 1 critical service providing REST administration endpoints for the HomeIQ platform on port 8004.

## Architecture

- `src/main.py` - FastAPI app, AdminAPIService class, route registration
- `src/helpers.py` - Health check, metrics computation, formatting utilities
- `src/middleware.py` - Observability, CORS, rate limiting, request logging
- `src/models.py` - Pydantic response models (APIResponse, ErrorResponse)

## Testing

```bash
cd domains/core-platform/admin-api
pytest tests/ -v
```

## Key Dependencies

- FastAPI, Pydantic, aiohttp, uvicorn
- homeiq-data (auth, rate limiter, error handler)
- homeiq-observability (logging, monitoring, tracing)
