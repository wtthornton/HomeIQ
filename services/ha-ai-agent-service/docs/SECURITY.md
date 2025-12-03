# Security Review

**Service:** HA AI Agent Service  
**Last Updated:** January 2025

This document covers security considerations, best practices, and recommendations for the HA AI Agent Service.

## API Key Management

### OpenAI API Key

**Storage:**
- ✅ Environment variable: `OPENAI_API_KEY`
- ✅ Never committed to git
- ✅ Loaded from `.env` file or Docker secrets

**Best Practices:**
- Use environment variables or secrets management
- Rotate keys periodically
- Use separate keys for dev/prod
- Monitor API usage for anomalies

**Security:**
- ✅ Never logged in plain text
- ✅ Not exposed in error messages
- ✅ Stored securely (not in code)

### Home Assistant Token

**Storage:**
- ✅ Environment variable: `HA_TOKEN`
- ✅ Long-lived access token (not password)
- ✅ Scoped permissions only

**Best Practices:**
- Generate tokens with minimal required permissions
- Rotate tokens periodically
- Use separate tokens per service
- Revoke unused tokens

**Security:**
- ✅ Never logged in plain text
- ✅ Not exposed in error messages
- ✅ Stored securely

## Rate Limiting

### Chat Endpoint Rate Limiting

**Current Implementation:**
- Simple in-memory rate limiter
- 100 requests/minute per IP address
- No persistent storage

**Limitations:**
- In-memory (resets on restart)
- Per-IP (single user limit)
- No distributed rate limiting

**Recommendations:**
- Implement Redis-backed rate limiting for production
- Per-user rate limiting (not just IP)
- Configurable limits per endpoint
- Distributed rate limiting for multi-instance

### OpenAI Rate Limiting

**Handling:**
- ✅ Automatic retry with exponential backoff
- ✅ Retry up to 3 attempts
- ✅ Returns 503 when rate limit exceeded

**Best Practices:**
- Monitor OpenAI usage
- Implement request queuing for high volume
- Use token budget limits
- Consider upgrading OpenAI plan for higher limits

## Input Validation

### Request Validation

**Pydantic Models:**
- ✅ All requests validated with Pydantic
- ✅ Type checking enforced
- ✅ Required fields validated

**Examples:**
```python
class ChatRequest(BaseModel):
    message: str  # Required
    conversation_id: Optional[str] = None
    refresh_context: bool = False
```

**Security:**
- ✅ SQL injection prevention (SQLAlchemy parameterized queries)
- ✅ XSS prevention (JSON responses, no HTML)
- ✅ Input sanitization (Pydantic validation)

### SQL Injection Prevention

**Implementation:**
- ✅ SQLAlchemy ORM (parameterized queries)
- ✅ No raw SQL queries
- ✅ Input validation before database operations

**Example:**
```python
# Safe - SQLAlchemy handles parameterization
conversation = await session.get(ConversationModel, conversation_id)

# Safe - Parameterized query
result = await session.execute(
    select(ConversationModel).where(ConversationModel.conversation_id == conversation_id)
)
```

## CORS Configuration

### Current Configuration

**Allowed Origins:**
- Environment variable: `HA_AI_AGENT_ALLOWED_ORIGINS`
- Default: `http://localhost:3000,http://localhost:3001`

**Configuration:**
```python
ALLOWED_ORIGINS = _parse_allowed_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Security:**
- ✅ Restricted to allowed origins only
- ⚠️ Configure for production (not localhost)
- ✅ Credentials allowed (for authentication)

**Recommendations:**
- Set specific origins in production
- Use HTTPS only in production
- Remove wildcard methods/headers if possible

## Database Security

### SQLite Database

**Location:**
- `/app/data/ha_ai_agent.db` (container)
- Persistent volume: `ha_ai_agent_data`

**Security:**
- ✅ File permissions (container user)
- ✅ No direct external access
- ⚠️ No encryption at rest (consider for sensitive data)

**Recommendations:**
- Encrypt database for production (SQLCipher)
- Regular backups
- Access control (container-level)

## Error Handling Security

### Error Messages

**Current:**
- ✅ User-friendly error messages
- ✅ No sensitive data in errors
- ✅ Stack traces only in logs

**Example:**
```python
# Safe - Generic error message
raise HTTPException(
    status_code=500,
    detail="Internal server error"
)

# Safe - Logs contain details
logger.exception("Detailed error information")
```

**Security:**
- ✅ API keys never in error messages
- ✅ No stack traces exposed to users
- ✅ Generic messages prevent information leakage

## Network Security

### Service Isolation

**Docker Network:**
- ✅ Runs on isolated Docker network (`homeiq-network`)
- ✅ No external network access required
- ✅ Internal service communication only

**Port Exposure:**
- ✅ Port 8030 exposed to host
- ⚠️ Consider firewall rules for production
- ✅ No unnecessary ports exposed

### HTTPS Recommendation

**Current:**
- HTTP only (no TLS/SSL)

**Production Recommendations:**
- Use reverse proxy (nginx, Traefik) with TLS
- Terminate TLS at proxy level
- Use Let's Encrypt for certificates
- Force HTTPS redirects

## Authentication & Authorization

### Current State

**No Authentication:**
- ⚠️ Service has no authentication layer
- ⚠️ Anyone with network access can use API
- ⚠️ No user identification

**Recommendations:**
- Implement API key authentication
- Add user authentication (JWT tokens)
- Role-based access control
- Rate limiting per user

### API Key Authentication (Future)

**Proposed:**
```python
# API key in header
Authorization: Bearer <api-key>

# Validate in middleware
@app.middleware("http")
async def authenticate(request: Request, call_next):
    api_key = request.headers.get("Authorization")
    # Validate API key
    ...
```

## Dependency Security

### Python Dependencies

**Management:**
- ✅ `requirements.txt` with pinned versions
- ✅ Regular dependency updates
- ⚠️ No automated vulnerability scanning

**Recommendations:**
- Use `pip-audit` for vulnerability scanning
- Regular dependency updates
- Monitor security advisories
- Use Dependabot or similar

### Container Security

**Base Image:**
- ✅ `python:3.12-slim` (official, minimal)
- ✅ Regular base image updates
- ✅ Minimal attack surface

**Recommendations:**
- Scan images for vulnerabilities
- Use multi-stage builds
- Run as non-root user
- Minimal system packages

## Data Privacy

### Conversation Storage

**Storage:**
- SQLite database (conversations, messages)
- TTL-based cleanup (30 days default)

**Privacy:**
- ⚠️ No encryption at rest
- ⚠️ User data stored in plain text
- ✅ Automatic cleanup (TTL)

**Recommendations:**
- Encrypt sensitive data at rest
- Implement data retention policies
- User data deletion capabilities
- GDPR compliance considerations

### Logging Privacy

**Current:**
- Logs may contain user messages
- No PII filtering

**Recommendations:**
- Filter PII from logs
- Implement log sanitization
- Redact sensitive data
- Compliance with privacy regulations

## Security Checklist

### Production Deployment

- [ ] Set `HA_AI_AGENT_ALLOWED_ORIGINS` to production URLs
- [ ] Use HTTPS (reverse proxy with TLS)
- [ ] Rotate API keys regularly
- [ ] Implement API key authentication
- [ ] Enable database encryption
- [ ] Set up firewall rules
- [ ] Configure log aggregation
- [ ] Enable security monitoring
- [ ] Regular dependency updates
- [ ] Vulnerability scanning

### Ongoing Security

- [ ] Monitor error logs for anomalies
- [ ] Review API usage patterns
- [ ] Update dependencies regularly
- [ ] Rotate credentials periodically
- [ ] Audit access logs
- [ ] Review security advisories

## Security Best Practices

1. **Defense in Depth** - Multiple security layers
2. **Least Privilege** - Minimal permissions
3. **Input Validation** - Validate all inputs
4. **Error Handling** - Don't leak information
5. **Secure Storage** - Encrypt sensitive data
6. **Regular Updates** - Keep dependencies current
7. **Monitoring** - Watch for security events
8. **Incident Response** - Plan for security incidents

## Related Documentation

- [Environment Variables](./ENVIRONMENT_VARIABLES.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Error Handling](./ERROR_HANDLING.md)

