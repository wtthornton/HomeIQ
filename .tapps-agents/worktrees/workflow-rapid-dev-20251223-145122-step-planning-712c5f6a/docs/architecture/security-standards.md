# Security Standards

This document defines comprehensive security standards and best practices for the Home Assistant Ingestor project.

## Security Framework Overview

The Home Assistant Ingestor implements a defense-in-depth security approach with multiple layers of protection across all services and components.

### Security Layers

1. **Network Security** - Firewall rules, network segmentation, encrypted communications
2. **Application Security** - Input validation, authentication, authorization
3. **Data Security** - Encryption at rest and in transit, data classification
4. **Infrastructure Security** - Container security, host hardening
5. **Operational Security** - Monitoring, logging, incident response

## Authentication & Authorization

### Authentication Standards

#### Multi-Factor Authentication (MFA)
- **Production Deployments** - MFA required for all administrative access
- **Development Environment** - MFA recommended for team members
- **API Access** - Token-based authentication with JWT

#### Token Management
```python
# services/admin-api/src/auth.py
import jwt
from datetime import datetime, timedelta
import secrets

class TokenManager:
    def __init__(self):
        self.secret_key = os.getenv('JWT_SECRET_KEY', secrets.token_urlsafe(32))
        self.algorithm = 'HS256'
        self.access_token_expiry = timedelta(hours=1)
        self.refresh_token_expiry = timedelta(days=30)
    
    def create_token_pair(self, user_id: str, roles: list) -> dict:
        """Create access and refresh token pair"""
        now = datetime.utcnow()
        
        # Access token
        access_payload = {
            'user_id': user_id,
            'roles': roles,
            'type': 'access',
            'exp': now + self.access_token_expiry,
            'iat': now,
            'jti': secrets.token_urlsafe(16)  # Unique token ID
        }
        
        # Refresh token
        refresh_payload = {
            'user_id': user_id,
            'type': 'refresh',
            'exp': now + self.refresh_token_expiry,
            'iat': now,
            'jti': secrets.token_urlsafe(16)
        }
        
        return {
            'access_token': jwt.encode(access_payload, self.secret_key, algorithm=self.algorithm),
            'refresh_token': jwt.encode(refresh_payload, self.secret_key, algorithm=self.algorithm),
            'expires_in': int(self.access_token_expiry.total_seconds())
        }
    
    def validate_token(self, token: str) -> dict:
        """Validate and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get('type') != 'access':
                raise jwt.InvalidTokenError("Invalid token type")
            
            # Check if token is revoked
            if self.is_token_revoked(payload['jti']):
                raise jwt.InvalidTokenError("Token has been revoked")
            
            return payload
        except jwt.ExpiredSignatureError:
            raise SecurityException("Token expired")
        except jwt.InvalidTokenError:
            raise SecurityException("Invalid token")
```

### Authorization Standards

#### Role-Based Access Control (RBAC)
```python
# services/admin-api/src/rbac.py
from enum import Enum
from typing import List

class Permission(str, Enum):
    READ_EVENTS = "read:events"
    WRITE_EVENTS = "write:events"
    DELETE_EVENTS = "delete:events"
    READ_STATS = "read:stats"
    READ_CONFIG = "read:config"
    WRITE_CONFIG = "write:config"
    ADMIN_USERS = "admin:users"
    ADMIN_SYSTEM = "admin:system"

class Role(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    READONLY = "readonly"

# Role-Permission mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: [
        Permission.READ_EVENTS,
        Permission.WRITE_EVENTS,
        Permission.DELETE_EVENTS,
        Permission.READ_STATS,
        Permission.READ_CONFIG,
        Permission.WRITE_CONFIG,
        Permission.ADMIN_USERS,
        Permission.ADMIN_SYSTEM
    ],
    Role.OPERATOR: [
        Permission.READ_EVENTS,
        Permission.WRITE_EVENTS,
        Permission.READ_STATS,
        Permission.READ_CONFIG
    ],
    Role.VIEWER: [
        Permission.READ_EVENTS,
        Permission.READ_STATS,
        Permission.READ_CONFIG
    ],
    Role.READONLY: [
        Permission.READ_EVENTS,
        Permission.READ_STATS
    ]
}

class AuthorizationManager:
    def __init__(self):
        self.role_permissions = ROLE_PERMISSIONS
    
    def has_permission(self, user_roles: List[str], required_permission: Permission) -> bool:
        """Check if user has required permission"""
        for role in user_roles:
            if role in self.role_permissions:
                if required_permission in self.role_permissions[role]:
                    return True
        return False
    
    def check_permission(self, user_roles: List[str], required_permission: Permission):
        """Check permission and raise exception if not authorized"""
        if not self.has_permission(user_roles, required_permission):
            raise SecurityException(f"Insufficient permissions for {required_permission}")
```

## Input Validation & Sanitization

### Input Validation Standards

#### Comprehensive Input Validation
```python
# services/admin-api/src/validation.py
from pydantic import BaseModel, validator, Field
import re
from typing import Optional

class SecurityValidator:
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize string input to prevent injection attacks"""
        if not isinstance(value, str):
            raise ValueError("Input must be a string")
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Limit length
        if len(value) > max_length:
            value = value[:max_length]
        
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', '\x00', '\r', '\n']
        for char in dangerous_chars:
            value = value.replace(char, '')
        
        return value.strip()
    
    @staticmethod
    def validate_entity_id(entity_id: str) -> str:
        """Validate Home Assistant entity ID format"""
        if not re.match(r'^[a-z_]+\.[a-z0-9_]+$', entity_id):
            raise ValueError("Invalid entity ID format")
        return entity_id
    
    @staticmethod
    def validate_timestamp(timestamp: str) -> str:
        """Validate ISO timestamp format"""
        try:
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return timestamp
        except ValueError:
            raise ValueError("Invalid timestamp format")

class EventCreateRequest(BaseModel):
    entity_id: str = Field(..., description="Home Assistant entity ID")
    state: str = Field(..., max_length=255, description="Entity state")
    timestamp: Optional[str] = Field(None, description="Event timestamp")
    attributes: Optional[dict] = Field(default_factory=dict, description="Entity attributes")
    
    @validator('entity_id')
    def validate_entity_id_field(cls, v):
        return SecurityValidator.validate_entity_id(v)
    
    @validator('state')
    def sanitize_state(cls, v):
        return SecurityValidator.sanitize_string(v, max_length=255)
    
    @validator('timestamp')
    def validate_timestamp_field(cls, v):
        if v is not None:
            return SecurityValidator.validate_timestamp(v)
        return v
    
    @validator('attributes')
    def sanitize_attributes(cls, v):
        if not isinstance(v, dict):
            raise ValueError("Attributes must be a dictionary")
        
        sanitized = {}
        for key, value in v.items():
            # Sanitize key
            clean_key = SecurityValidator.sanitize_string(key, max_length=100)
            
            # Sanitize value based on type
            if isinstance(value, str):
                clean_value = SecurityValidator.sanitize_string(value, max_length=1000)
            elif isinstance(value, (int, float, bool)):
                clean_value = value
            else:
                clean_value = str(value)[:1000]  # Convert to string and limit length
            
            sanitized[clean_key] = clean_value
        
        return sanitized
```

### SQL Injection Prevention

#### Parameterized Queries
```python
# services/admin-api/src/database.py
from sqlalchemy import text
from sqlalchemy.orm import Session

class SecureDatabase:
    def __init__(self, db: Session):
        self.db = db
    
    def get_events_by_entity(self, entity_id: str, limit: int = 100):
        """Get events by entity ID using parameterized query"""
        # Use parameterized query to prevent SQL injection
        query = text("""
            SELECT * FROM events 
            WHERE entity_id = :entity_id 
            ORDER BY timestamp DESC 
            LIMIT :limit
        """)
        
        result = self.db.execute(query, {
            'entity_id': entity_id,
            'limit': limit
        })
        
        return result.fetchall()
    
    def search_events(self, search_term: str, limit: int = 100):
        """Search events with safe pattern matching"""
        # Sanitize search term
        safe_search = re.escape(search_term)
        
        query = text("""
            SELECT * FROM events 
            WHERE entity_id ILIKE :pattern 
            OR state ILIKE :pattern
            ORDER BY timestamp DESC 
            LIMIT :limit
        """)
        
        result = self.db.execute(query, {
            'pattern': f'%{safe_search}%',
            'limit': limit
        })
        
        return result.fetchall()
```

## Data Protection

### Encryption Standards

#### Data Encryption at Rest
```python
# services/admin-api/src/encryption.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class DataEncryption:
    def __init__(self):
        self.encryption_key = self._get_or_create_key()
        self.cipher_suite = Fernet(self.encryption_key)
    
    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key"""
        key_file = os.getenv('ENCRYPTION_KEY_FILE', '/app/keys/encryption.key')
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(key_file), exist_ok=True)
            
            # Save key with restricted permissions
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)  # Owner read/write only
            
            return key
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        if not data:
            return data
        
        encrypted_bytes = self.cipher_suite.encrypt(data.encode())
        return base64.b64encode(encrypted_bytes).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if not encrypted_data:
            return encrypted_data
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted_bytes = self.cipher_suite.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            raise SecurityException(f"Failed to decrypt data: {e}")

# Usage for sensitive data
class UserCredentials:
    def __init__(self, encryption: DataEncryption):
        self.encryption = encryption
    
    def store_api_key(self, user_id: str, api_key: str):
        """Store encrypted API key"""
        encrypted_key = self.encryption.encrypt_data(api_key)
        # Store encrypted_key in database
        pass
    
    def retrieve_api_key(self, user_id: str) -> str:
        """Retrieve and decrypt API key"""
        encrypted_key = "..."  # Retrieve from database
        return self.encryption.decrypt_data(encrypted_key)
```

#### Data Encryption in Transit
```python
# services/admin-api/src/ssl_config.py
import ssl
from fastapi import FastAPI

def configure_ssl():
    """Configure SSL/TLS for secure communications"""
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    
    # Load SSL certificates
    ssl_context.load_cert_chain(
        certfile=os.getenv('SSL_CERT_FILE', '/app/certs/server.crt'),
        keyfile=os.getenv('SSL_KEY_FILE', '/app/certs/server.key')
    )
    
    # Configure cipher suites
    ssl_context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
    
    # Enable certificate verification
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.check_hostname = True
    
    return ssl_context

# Apply SSL configuration
app = FastAPI()
ssl_context = configure_ssl()
```

### Password Security

#### Password Hashing
```python
# services/admin-api/src/password.py
import bcrypt
import secrets
import string

class PasswordManager:
    def __init__(self):
        self.bcrypt_rounds = 12
    
    def hash_password(self, password: str) -> str:
        """Hash password with bcrypt"""
        # Generate salt
        salt = bcrypt.gensalt(rounds=self.bcrypt_rounds)
        
        # Hash password
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False
    
    def generate_secure_password(self, length: int = 16) -> str:
        """Generate secure random password"""
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(characters) for _ in range(length))
        return password
    
    def validate_password_strength(self, password: str) -> dict:
        """Validate password strength"""
        issues = []
        
        if len(password) < 8:
            issues.append("Password must be at least 8 characters long")
        
        if not re.search(r'[A-Z]', password):
            issues.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            issues.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            issues.append("Password must contain at least one digit")
        
        if not re.search(r'[!@#$%^&*]', password):
            issues.append("Password must contain at least one special character")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }
```

## Network Security

### CORS Configuration

#### Secure CORS Setup
```python
# services/admin-api/src/cors.py
from fastapi.middleware.cors import CORSMiddleware

def configure_cors(app: FastAPI):
    """Configure CORS with security best practices"""
    
    # Define allowed origins
    allowed_origins = os.getenv('CORS_ORIGINS', '').split(',')
    
    # Remove empty strings and add localhost for development
    if not allowed_origins or allowed_origins == ['']:
        allowed_origins = ['http://localhost:3000']  # Development only
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "X-Client-Version"
        ],
        expose_headers=[
            "X-Request-ID",
            "X-Process-Time",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining"
        ]
    )
```

### Security Headers

#### Comprehensive Security Headers
```python
# services/admin-api/src/security_headers.py
from fastapi import FastAPI, Request, Response

def add_security_headers(app: FastAPI):
    """Add comprehensive security headers"""
    
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none';"
        )
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "speaker=()"
        )
        
        # Strict Transport Security (HTTPS only)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        return response
```

## Monitoring & Logging

### Security Event Logging

#### Comprehensive Security Logging
```python
# services/admin-api/src/security_logging.py
import logging
import json
from datetime import datetime
from typing import Dict, Any

class SecurityLogger:
    def __init__(self):
        self.logger = logging.getLogger('security')
        self.logger.setLevel(logging.INFO)
        
        # Create file handler for security logs
        handler = logging.FileHandler('/app/logs/security.log')
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_authentication_event(self, event_type: str, user_id: str = None, 
                                ip_address: str = None, success: bool = True, 
                                details: Dict[str, Any] = None):
        """Log authentication events"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "authentication",
            "sub_type": event_type,
            "user_id": user_id,
            "ip_address": ip_address,
            "success": success,
            "details": details or {}
        }
        
        self.logger.info(json.dumps(log_entry))
    
    def log_authorization_event(self, event_type: str, user_id: str, 
                               resource: str, permission: str, 
                               success: bool = True):
        """Log authorization events"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "authorization",
            "sub_type": event_type,
            "user_id": user_id,
            "resource": resource,
            "permission": permission,
            "success": success
        }
        
        self.logger.info(json.dumps(log_entry))
    
    def log_security_violation(self, violation_type: str, details: Dict[str, Any]):
        """Log security violations"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "security_violation",
            "violation_type": violation_type,
            "severity": "HIGH",
            "details": details
        }
        
        self.logger.warning(json.dumps(log_entry))

# Usage in authentication
class AuthenticationService:
    def __init__(self):
        self.security_logger = SecurityLogger()
    
    async def authenticate_user(self, username: str, password: str, 
                               ip_address: str) -> bool:
        """Authenticate user with logging"""
        try:
            # Authentication logic here
            success = self._verify_credentials(username, password)
            
            self.security_logger.log_authentication_event(
                event_type="login_attempt",
                user_id=username,
                ip_address=ip_address,
                success=success
            )
            
            if not success:
                self.security_logger.log_security_violation(
                    violation_type="failed_login",
                    details={
                        "username": username,
                        "ip_address": ip_address
                    }
                )
            
            return success
            
        except Exception as e:
            self.security_logger.log_security_violation(
                violation_type="authentication_error",
                details={
                    "username": username,
                    "ip_address": ip_address,
                    "error": str(e)
                }
            )
            return False
```

### Intrusion Detection

#### Basic Intrusion Detection
```python
# services/admin-api/src/intrusion_detection.py
from collections import defaultdict
from datetime import datetime, timedelta
import logging

class IntrusionDetector:
    def __init__(self):
        self.failed_attempts = defaultdict(list)
        self.blocked_ips = set()
        self.logger = logging.getLogger('intrusion_detection')
    
    def check_suspicious_activity(self, ip_address: str, user_id: str = None) -> bool:
        """Check for suspicious activity patterns"""
        now = datetime.utcnow()
        
        # Clean old failed attempts
        cutoff_time = now - timedelta(hours=1)
        self.failed_attempts[ip_address] = [
            attempt for attempt in self.failed_attempts[ip_address]
            if attempt > cutoff_time
        ]
        
        # Check for multiple failed attempts
        if len(self.failed_attempts[ip_address]) > 5:
            self._block_ip(ip_address, "Multiple failed login attempts")
            return True
        
        # Check for rapid requests
        if len(self.failed_attempts[ip_address]) > 10:
            self._block_ip(ip_address, "Rapid request pattern")
            return True
        
        return False
    
    def record_failed_attempt(self, ip_address: str, user_id: str = None):
        """Record failed authentication attempt"""
        self.failed_attempts[ip_address].append(datetime.utcnow())
    
    def _block_ip(self, ip_address: str, reason: str):
        """Block IP address"""
        self.blocked_ips.add(ip_address)
        self.logger.warning(f"Blocked IP {ip_address}: {reason}")
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP is blocked"""
        return ip_address in self.blocked_ips
```

## Security Testing

### Security Test Suite

#### Comprehensive Security Tests
```python
# tests/test_security.py
import pytest
from fastapi.testclient import TestClient
from services.admin-api.src.main import app

client = TestClient(app)

def test_sql_injection_protection():
    """Test SQL injection protection"""
    malicious_input = "'; DROP TABLE events; --"
    
    response = client.get(f"/api/v1/events?search={malicious_input}")
    
    # Should not return 500 error (SQL injection successful)
    assert response.status_code != 500
    
    # Should handle gracefully
    assert response.status_code in [200, 400, 422]

def test_xss_protection():
    """Test XSS protection"""
    xss_payload = "<script>alert('XSS')</script>"
    
    response = client.post("/api/v1/events", json={
        "entity_id": "sensor.test",
        "state": xss_payload,
        "attributes": {"description": xss_payload}
    })
    
    if response.status_code == 201:
        data = response.json()
        # Check that script tags are sanitized
        assert "<script>" not in data["data"]["state"]
        assert "<script>" not in str(data["data"]["attributes"])

def test_authentication_required():
    """Test that authentication is required for protected endpoints"""
    response = client.get("/api/v1/admin/users")
    
    assert response.status_code == 401
    assert "Authentication required" in response.json()["error"]["message"]

def test_rate_limiting():
    """Test rate limiting functionality"""
    # Make many requests quickly
    for _ in range(101):
        response = client.get("/api/v1/events")
    
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["error"]["message"]

def test_security_headers():
    """Test security headers are present"""
    response = client.get("/api/v1/health")
    
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "X-XSS-Protection" in response.headers
    assert "Content-Security-Policy" in response.headers

def test_input_validation():
    """Test input validation prevents malicious data"""
    malicious_data = {
        "entity_id": "../../etc/passwd",
        "state": "'; DROP TABLE events; --",
        "timestamp": "invalid_timestamp"
    }
    
    response = client.post("/api/v1/events", json=malicious_data)
    
    assert response.status_code == 422  # Validation error
    assert "validation" in response.json()["error"]["code"].lower()
```

These security standards ensure comprehensive protection across all layers of the Home Assistant Ingestor system, from network security to application-level protections.
