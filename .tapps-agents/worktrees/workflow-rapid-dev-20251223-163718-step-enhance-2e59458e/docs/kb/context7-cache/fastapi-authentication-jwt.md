# FastAPI Authentication & JWT Patterns
**Context7 KB Cache**

**Source:** Context7 /fastapi/fastapi  
**Topic:** Authentication, JWT tokens, API keys, OAuth2  
**Retrieved:** October 11, 2025  
**Trust Score:** 9.9  
**Snippets:** 883

---

## JWT Token Authentication

### Generate JWT Tokens
```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire, "sub": "user_id"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

### Verify JWT Tokens
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username
```

### Token Endpoint
```python
from fastapi.security import OAuth2PasswordRequestForm

@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
```

---

## API Key Authentication

### Simple API Key Schemes
```python
from fastapi.security import (
    APIKeyCookie,
    APIKeyHeader,
    APIKeyQuery,
    HTTPBearer
)

# Header-based API key
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Query parameter API key
api_key_query = APIKeyQuery(name="api_key", auto_error=False)

# Cookie-based API key
api_key_cookie = APIKeyCookie(name="api_key", auto_error=False)

# Bearer token
http_bearer = HTTPBearer(auto_error=False)
```

### Using API Keys
```python
from fastapi import Depends, HTTPException
import secrets

def verify_api_key(api_key: str = Depends(api_key_header)):
    if not api_key:
        raise HTTPException(401, "API key required")
    if not secrets.compare_digest(api_key, EXPECTED_API_KEY):
        raise HTTPException(401, "Invalid API key")
    return api_key

@app.get("/protected")
def protected_endpoint(api_key: str = Depends(verify_api_key)):
    return {"message": "Access granted"}
```

---

## Password Hashing

### Setup Password Context
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)
```

---

## OAuth2 with Scopes

### Token with Scopes
```python
@app.post("/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    # ... authentication logic ...
    access_token = create_access_token(
        data={"sub": form_data.username, "scopes": form_data.scopes}
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "scopes": form_data.scopes
    }
```

---

## Security Best Practices

### 1. Secret Key Generation
```python
import secrets

# Generate secure random key
SECRET_KEY = secrets.token_hex(32)
```

### 2. Token Expiration
- Access tokens: 15-30 minutes
- Refresh tokens: 7-30 days
- Always set expiration

### 3. Secure Storage
- Never commit secrets to git
- Use environment variables
- Use secure key management

### 4. Password Handling
- Never store plaintext passwords
- Always hash with bcrypt/argon2
- Use secure comparison (secrets.compare_digest)

---

## Dependencies

### Required Packages
```bash
pip install python-jose[cryptography]
pip install passlib[bcrypt]
pip install python-multipart
```

---

## Use Cases

### When to Use JWT
- Stateless authentication needed
- Microservices architecture
- Mobile/SPA applications
- Cross-domain auth

### When to Use API Keys
- Service-to-service auth
- Simple authentication
- Public API access
- Machine-to-machine

### When to Use OAuth2
- Third-party integrations
- Social login
- Delegated authorization
- Industry standard required

---

**Saved to KB:** 2025-10-11  
**Topics:** authentication, jwt, api_keys, oauth2, security  
**Use Case:** Secure FastAPI applications  
**Complexity:** Medium

