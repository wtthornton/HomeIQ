# Compliance Standard Framework

This document provides a platform for implementing compliance standards for the Home Assistant Ingestor environment, including code that implements a set of compliance rules and reports back to the system.

## Compliance Framework Overview

The Home Assistant Ingestor implements a comprehensive compliance framework that ensures adherence to security, performance, and quality standards across all services and components.

### Compliance Domains

1. **Security Compliance** - Authentication, authorization, data protection
2. **Performance Compliance** - Response times, throughput, resource usage
3. **Quality Compliance** - Code quality, testing coverage, documentation
4. **Operational Compliance** - Logging, monitoring, error handling
5. **Data Compliance** - Data integrity, retention, privacy

## Security Compliance Standards

### Authentication & Authorization

#### Required Standards
- **Multi-Factor Authentication** - Required for production deployments
- **Token-Based Authentication** - JWT tokens with expiration
- **Role-Based Access Control** - Granular permission management
- **Session Management** - Secure session handling and timeout

#### Implementation Rules
```python
# services/admin-api/src/auth.py
class AuthManager:
    def __init__(self):
        self.token_expiry = timedelta(hours=24)
        self.max_login_attempts = 5
        self.session_timeout = timedelta(hours=8)
    
    def validate_token(self, token: str) -> bool:
        """Validate JWT token with security checks"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            
            # Check token expiration
            if datetime.utcnow() > datetime.fromtimestamp(payload['exp']):
                return False
            
            # Check token revocation
            if self.is_token_revoked(token):
                return False
                
            return True
        except jwt.InvalidTokenError:
            return False
```

### Data Protection Standards

#### Encryption Requirements
- **Data at Rest** - All sensitive data encrypted in storage
- **Data in Transit** - HTTPS/TLS for all communications
- **Password Storage** - Bcrypt with salt for password hashing
- **API Keys** - Encrypted storage of external API credentials

#### Implementation Example
```python
# services/admin-api/src/encryption.py
from cryptography.fernet import Fernet
import bcrypt

class DataProtection:
    def __init__(self):
        self.cipher_suite = Fernet(os.getenv('ENCRYPTION_KEY'))
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data before storage"""
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data for use"""
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
    
    def hash_password(self, password: str) -> str:
        """Hash password with bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()
```

### Input Validation Standards

#### Required Validations
- **SQL Injection Prevention** - Parameterized queries only
- **XSS Prevention** - Input sanitization and output encoding
- **CSRF Protection** - CSRF tokens for state-changing operations
- **Rate Limiting** - API endpoint rate limiting

#### Implementation Example
```python
# services/admin-api/src/validation.py
from pydantic import BaseModel, validator
import re

class InputValidator:
    @staticmethod
    def sanitize_input(value: str) -> str:
        """Sanitize user input to prevent XSS"""
        # Remove HTML tags
        clean_value = re.sub(r'<[^>]+>', '', value)
        # Escape special characters
        clean_value = clean_value.replace('&', '&amp;')
        clean_value = clean_value.replace('<', '&lt;')
        clean_value = clean_value.replace('>', '&gt;')
        return clean_value
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

class APIRequest(BaseModel):
    email: str
    message: str
    
    @validator('email')
    def validate_email_field(cls, v):
        if not InputValidator.validate_email(v):
            raise ValueError('Invalid email format')
        return v
    
    @validator('message')
    def sanitize_message(cls, v):
        return InputValidator.sanitize_input(v)
```

## Performance Compliance Standards

### Response Time Requirements

#### API Performance Standards
- **Health Check Endpoints** - < 100ms response time
- **Read Operations** - < 500ms response time
- **Write Operations** - < 1000ms response time
- **Complex Queries** - < 2000ms response time

#### Implementation Monitoring
```python
# services/admin-api/src/middleware.py
import time
from fastapi import Request, Response

@app.middleware("http")
async def performance_monitoring(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    # Log performance metrics
    logger.info(f"Performance: {request.method} {request.url.path} - {process_time:.3f}s")
    
    # Add performance headers
    response.headers["X-Process-Time"] = str(process_time)
    
    # Alert on slow requests
    if process_time > 2.0:  # 2 second threshold
        logger.warning(f"Slow request detected: {request.url.path} - {process_time:.3f}s")
    
    return response
```

### Resource Usage Standards

#### Memory Usage Limits
- **Per Service** - Maximum 512MB memory usage
- **Database Connections** - Maximum 20 connections per service
- **File Handles** - Maximum 100 open files per process
- **CPU Usage** - Maximum 80% CPU utilization

#### Implementation Example
```python
# services/websocket-ingestion/src/memory_manager.py
import psutil
import logging

class MemoryManager:
    def __init__(self, max_memory_mb: int = 512):
        self.max_memory_mb = max_memory_mb
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
    
    def check_memory_usage(self) -> bool:
        """Check if memory usage is within limits"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        if memory_info.rss > self.max_memory_bytes:
            logging.error(f"Memory limit exceeded: {memory_info.rss / 1024 / 1024:.1f}MB")
            return False
        
        return True
    
    def get_memory_stats(self) -> dict:
        """Get current memory statistics"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent(),
            "limit_mb": self.max_memory_mb
        }
```

## Quality Compliance Standards

### Code Quality Requirements

#### Testing Coverage Standards
- **Unit Tests** - Minimum 80% code coverage
- **Integration Tests** - All API endpoints covered
- **E2E Tests** - Critical user workflows covered
- **Performance Tests** - Load testing for all endpoints

#### Implementation Example
```python
# tests/test_compliance.py
import pytest
from fastapi.testclient import TestClient
from services.admin-api.src.main import app

client = TestClient(app)

def test_api_response_time():
    """Test API response time compliance"""
    import time
    
    start_time = time.time()
    response = client.get("/api/v1/health")
    response_time = time.time() - start_time
    
    assert response.status_code == 200
    assert response_time < 0.1  # 100ms limit

def test_memory_usage():
    """Test memory usage compliance"""
    import psutil
    
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    
    assert memory_mb < 512  # 512MB limit

@pytest.mark.parametrize("endpoint", [
    "/api/v1/health",
    "/api/v1/stats",
    "/api/v1/config"
])
def test_endpoint_security(endpoint):
    """Test endpoint security compliance"""
    response = client.get(endpoint)
    
    # Check security headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "X-XSS-Protection" in response.headers
```

### Documentation Standards

#### Required Documentation
- **API Documentation** - OpenAPI/Swagger documentation
- **Code Documentation** - Docstrings for all functions
- **Architecture Documentation** - System design documentation
- **Deployment Documentation** - Setup and deployment guides

#### Implementation Example
```python
# services/admin-api/src/health_endpoints.py
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

router = APIRouter()

@router.get("/health", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for service monitoring.
    
    Returns:
        Dict[str, Any]: Health status information including:
            - status: Overall service status
            - timestamp: Current timestamp
            - version: Service version
            - dependencies: Status of dependent services
    
    Raises:
        HTTPException: If service is unhealthy (status code 503)
    """
    try:
        # Check service dependencies
        dependencies = await check_dependencies()
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "dependencies": dependencies
        }
        
        # Check if all dependencies are healthy
        if not all(dep["status"] == "healthy" for dep in dependencies.values()):
            health_status["status"] = "degraded"
            raise HTTPException(status_code=503, detail="Service dependencies unhealthy")
        
        return health_status
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
```

## Operational Compliance Standards

### Logging Standards

#### Required Log Information
- **Structured Logging** - JSON format for all log entries
- **Log Levels** - Appropriate use of DEBUG, INFO, WARNING, ERROR
- **Request Tracking** - Unique request IDs for tracing
- **Security Events** - Log all authentication and authorization events

#### Implementation Example
```python
# shared/logging_config.py
import logging
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # JSON formatter
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_structured(self, level: str, message: str, **kwargs):
        """Log structured JSON message"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "service": self.logger.name,
            **kwargs
        }
        
        self.logger.info(json.dumps(log_entry))
    
    def log_security_event(self, event_type: str, user_id: str = None, **kwargs):
        """Log security-related events"""
        self.log_structured(
            "INFO",
            f"Security event: {event_type}",
            event_type="security",
            user_id=user_id,
            **kwargs
        )
```

### Error Handling Standards

#### Error Response Format
- **Consistent Error Format** - Standardized error response structure
- **Error Codes** - Unique error codes for different error types
- **Error Context** - Sufficient context for debugging
- **Security** - No sensitive information in error messages

#### Implementation Example
```python
# services/admin-api/src/error_handler.py
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

class ErrorHandler:
    @staticmethod
    def create_error_response(
        error_code: str,
        message: str,
        status_code: int = 500,
        details: dict = None
    ) -> JSONResponse:
        """Create standardized error response"""
        error_response = {
            "error": {
                "code": error_code,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": getattr(request.state, 'request_id', None)
            }
        }
        
        if details:
            error_response["error"]["details"] = details
        
        return JSONResponse(
            status_code=status_code,
            content=error_response
        )
    
    @staticmethod
    def handle_validation_error(exc: ValidationError):
        """Handle Pydantic validation errors"""
        return ErrorHandler.create_error_response(
            error_code="VALIDATION_ERROR",
            message="Invalid input data",
            status_code=400,
            details={"validation_errors": exc.errors()}
        )
```

## Data Compliance Standards

### Data Integrity Requirements

#### Data Validation
- **Schema Validation** - All data must match defined schemas
- **Referential Integrity** - Foreign key relationships maintained
- **Data Consistency** - Consistent data across all services
- **Backup Verification** - Regular backup integrity checks

#### Implementation Example
```python
# services/enrichment-pipeline/src/data_validator.py
from pydantic import BaseModel, validator
from typing import Optional

class EventData(BaseModel):
    """Event data model with validation"""
    entity_id: str
    state: str
    timestamp: datetime
    attributes: dict
    
    @validator('entity_id')
    def validate_entity_id(cls, v):
        """Validate entity ID format"""
        if not re.match(r'^[a-z_]+\.[a-z_]+$', v):
            raise ValueError('Invalid entity ID format')
        return v
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Validate timestamp is not in the future"""
        if v > datetime.utcnow():
            raise ValueError('Timestamp cannot be in the future')
        return v

class DataValidator:
    def validate_event_data(self, data: dict) -> EventData:
        """Validate and normalize event data"""
        try:
            return EventData(**data)
        except ValidationError as e:
            raise ValueError(f"Data validation failed: {e}")
```

### Data Retention Standards

#### Retention Policies
- **Raw Data** - 90 days retention
- **Processed Data** - 1 year retention
- **Aggregated Data** - 5 years retention
- **Logs** - 30 days retention

#### Implementation Example
```python
# services/data-retention/src/retention_policy.py
from datetime import datetime, timedelta

class RetentionPolicy:
    def __init__(self):
        self.policies = {
            "raw_events": timedelta(days=90),
            "processed_events": timedelta(days=365),
            "aggregated_data": timedelta(days=1825),  # 5 years
            "logs": timedelta(days=30)
        }
    
    def get_expiration_date(self, data_type: str, created_at: datetime) -> datetime:
        """Get expiration date for data type"""
        if data_type not in self.policies:
            raise ValueError(f"Unknown data type: {data_type}")
        
        return created_at + self.policies[data_type]
    
    def should_retain(self, data_type: str, created_at: datetime) -> bool:
        """Check if data should be retained"""
        expiration_date = self.get_expiration_date(data_type, created_at)
        return datetime.utcnow() < expiration_date
```

## Compliance Monitoring and Reporting

### Automated Compliance Checks

#### Continuous Monitoring
```python
# scripts/compliance_check.py
import asyncio
from typing import Dict, List

class ComplianceMonitor:
    async def run_compliance_checks(self) -> Dict[str, bool]:
        """Run all compliance checks"""
        checks = {
            "security": await self.check_security_compliance(),
            "performance": await self.check_performance_compliance(),
            "quality": await self.check_quality_compliance(),
            "operational": await self.check_operational_compliance(),
            "data": await self.check_data_compliance()
        }
        
        return checks
    
    async def check_security_compliance(self) -> bool:
        """Check security compliance"""
        # Check authentication endpoints
        # Verify HTTPS configuration
        # Validate input sanitization
        # Check for security headers
        return True
    
    async def check_performance_compliance(self) -> bool:
        """Check performance compliance"""
        # Measure response times
        # Check memory usage
        # Verify resource limits
        return True
```

### Compliance Reporting

#### Daily Compliance Report
```python
# services/admin-api/src/compliance_report.py
from datetime import datetime, timedelta

class ComplianceReporter:
    def generate_daily_report(self) -> dict:
        """Generate daily compliance report"""
        report = {
            "report_date": datetime.utcnow().isoformat(),
            "compliance_status": "PASS",
            "checks": {
                "security": self.check_security_compliance(),
                "performance": self.check_performance_compliance(),
                "quality": self.check_quality_compliance(),
                "operational": self.check_operational_compliance(),
                "data": self.check_data_compliance()
            },
            "violations": [],
            "recommendations": []
        }
        
        # Check for any violations
        for check_type, status in report["checks"].items():
            if not status:
                report["violations"].append(f"{check_type}_compliance_failed")
                report["compliance_status"] = "FAIL"
        
        return report
```

This compliance framework ensures that the Home Assistant Ingestor maintains high standards for security, performance, quality, and operational excellence across all components and services.
