# Error Handling Documentation

**Service:** HA AI Agent Service  
**Last Updated:** January 2025

This document describes error handling patterns, error codes, and troubleshooting strategies for the HA AI Agent Service.

## Error Response Format

All errors follow FastAPI standard error response format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

## HTTP Status Codes

### 200 OK
- **Description:** Request successful
- **When:** Normal operation

### 400 Bad Request
- **Description:** Invalid request parameters
- **Examples:**
  - Missing required fields
  - Invalid conversation ID format
  - Token budget exceeded

### 404 Not Found
- **Description:** Resource not found
- **Examples:**
  - Conversation not found
  - Invalid conversation ID

### 429 Too Many Requests
- **Description:** Rate limit exceeded
- **Details:** Chat endpoint rate limit (100 requests/minute per IP)
- **Response:** Retry after delay

### 500 Internal Server Error
- **Description:** Unexpected server error
- **When:** Unhandled exceptions
- **Action:** Check logs for details

### 503 Service Unavailable
- **Description:** Service or dependency unavailable
- **Examples:**
  - OpenAI API unavailable
  - Home Assistant connection failed
  - Data API service down

## Error Categories

### 1. OpenAI API Errors

#### Rate Limit Error (429)
```json
{
  "detail": "OpenAI API rate limit exceeded. Please try again later."
}
```

**HTTP Status:** 503 Service Unavailable

**Causes:**
- Too many requests to OpenAI API
- API quota exceeded

**Solutions:**
- Wait and retry (exponential backoff automatic)
- Check OpenAI API usage limits
- Use lower-cost model (gpt-4o-mini)

**Recovery:**
- Automatic retry with exponential backoff (3 attempts)
- Manual retry after delay

#### Token Budget Exceeded (400)
```json
{
  "detail": "Message too long. Please shorten your message or start a new conversation."
}
```

**HTTP Status:** 400 Bad Request

**Causes:**
- Conversation history too long
- Context + message exceeds token limit

**Solutions:**
- Start new conversation
- Shorten message
- Reduce context size

**Recovery:**
- Create new conversation
- Reduce message length

#### OpenAI API Error (503)
```json
{
  "detail": "OpenAI API error. Please try again later."
}
```

**HTTP Status:** 503 Service Unavailable

**Causes:**
- OpenAI API down
- Network connectivity issues
- Invalid API key

**Solutions:**
- Check OpenAI API status
- Verify API key
- Check network connectivity

**Recovery:**
- Automatic retry (3 attempts)
- Manual retry after delay

### 2. Home Assistant Errors

#### Connection Error
```
Could not connect to Home Assistant at {url}
```

**Causes:**
- Home Assistant service down
- Network connectivity issues
- Incorrect HA_URL

**Solutions:**
- Verify Home Assistant is running
- Check HA_URL environment variable
- Verify network connectivity

#### Authentication Error
```
Home Assistant authentication failed
```

**Causes:**
- Invalid or expired access token
- Token doesn't have required permissions

**Solutions:**
- Generate new long-lived access token
- Verify HA_TOKEN environment variable
- Check token permissions

### 3. Data API Errors

#### Connection Error
```
Could not connect to Data API at {url}
```

**Causes:**
- Data API service down
- Network connectivity issues

**Solutions:**
- Verify data-api service is running
- Check DATA_API_URL environment variable
- Check Docker network connectivity

#### Timeout Error
```
Data API request timed out after 30 seconds
```

**Causes:**
- Data API overloaded
- Network latency issues

**Solutions:**
- Check Data API service health
- Verify network connectivity
- Increase timeout if needed

### 4. Conversation Errors

#### Conversation Not Found (404)
```json
{
  "detail": "Conversation {conversation_id} not found"
}
```

**HTTP Status:** 404 Not Found

**Causes:**
- Invalid conversation ID
- Conversation deleted or expired
- Database connection issue

**Solutions:**
- Verify conversation ID
- Check conversation TTL settings
- Create new conversation

### 5. Database Errors

#### Database Connection Error
```
Database connection failed
```

**Causes:**
- SQLite file locked
- Disk full
- Permission issues

**Solutions:**
- Check disk space
- Verify file permissions
- Restart service

### 6. Validation Errors

#### Invalid Request (400)
```json
{
  "detail": "Validation error: {field} is required"
}
```

**HTTP Status:** 400 Bad Request

**Causes:**
- Missing required fields
- Invalid data types
- Validation failed

**Solutions:**
- Check request format
- Verify required fields
- Check data types

## Error Recovery Strategies

### Automatic Retries

**OpenAI API:**
- **Max Retries:** 3 attempts
- **Backoff:** Exponential (2s, 4s, 8s)
- **Conditions:** Rate limit errors, transient failures

**Data API:**
- **Max Retries:** 3 attempts
- **Backoff:** Exponential (2s, 4s, 10s)
- **Conditions:** Network errors, timeouts

### Graceful Degradation

**Device Intelligence Service:**
- Service continues if unavailable
- Capability patterns optional
- Context building continues without patterns

**Data API:**
- Entity queries optional for basic functionality
- Service can operate with reduced context

### Error Logging

All errors are logged with:
- Error message
- Stack trace (for 500 errors)
- Request context
- Timestamp

**Log Levels:**
- **ERROR:** All API errors, service failures
- **WARNING:** Rate limits, retries
- **INFO:** Successful operations

## Troubleshooting Guide

### Service Won't Start

**Symptoms:**
- Container exits immediately
- Health check fails

**Diagnosis:**
```bash
# Check logs
docker-compose logs ha-ai-agent-service

# Check environment variables
docker exec homeiq-ha-ai-agent-service env | grep -E "HA_|OPENAI_"
```

**Common Causes:**
- Missing required environment variables
- Invalid API keys
- Database permissions

### Chat Endpoint Returns 503

**Symptoms:**
- All chat requests fail with 503

**Diagnosis:**
```bash
# Check service health
curl http://localhost:8030/health

# Check OpenAI connectivity
docker exec homeiq-ha-ai-agent-service curl -v https://api.openai.com/v1/models
```

**Common Causes:**
- OpenAI API key invalid
- Network connectivity issues
- Service dependencies down

### Conversations Not Persisting

**Symptoms:**
- Conversations lost after restart
- Conversation not found errors

**Diagnosis:**
```bash
# Check database
docker exec homeiq-ha-ai-agent-service sqlite3 /app/data/ha_ai_agent.db ".tables"

# Check volume mount
docker volume inspect homeiq_ha_ai_agent_data
```

**Common Causes:**
- Database volume not mounted
- Database file permissions
- TTL expired

### High Error Rate

**Symptoms:**
- Many 503 errors in logs
- Service unstable

**Diagnosis:**
```bash
# Check error logs
docker-compose logs ha-ai-agent-service | grep ERROR

# Check resource usage
docker stats homeiq-ha-ai-agent-service
```

**Common Causes:**
- Resource limits exceeded
- Dependencies overloaded
- Database locks

## Monitoring Errors

### Log Monitoring

```bash
# Watch errors in real-time
docker-compose logs -f ha-ai-agent-service | grep ERROR

# Count errors
docker-compose logs ha-ai-agent-service | grep -c ERROR
```

### Health Check

```bash
# Check health endpoint
curl http://localhost:8030/health
```

**Healthy Response:**
```json
{
  "status": "healthy",
  "service": "ha-ai-agent-service",
  "version": "1.0.0"
}
```

## Best Practices

1. **Always check logs** before reporting errors
2. **Verify environment variables** are set correctly
3. **Check service dependencies** are healthy
4. **Monitor error rates** for patterns
5. **Use retry logic** for transient failures
6. **Implement circuit breakers** for external services

## Related Documentation

- [Deployment Guide](./DEPLOYMENT.md)
- [Monitoring](./MONITORING.md)
- [API Documentation](./API_DOCUMENTATION.md)

