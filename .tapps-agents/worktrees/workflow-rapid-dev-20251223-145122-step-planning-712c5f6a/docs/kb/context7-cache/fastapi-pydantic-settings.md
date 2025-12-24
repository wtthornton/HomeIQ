# FastAPI Pydantic Settings Management
**Context7 KB Cache**

**Source:** Context7 /fastapi/fastapi  
**Topic:** Environment variables, configuration, Pydantic Settings  
**Retrieved:** October 11, 2025  
**Trust Score:** 9.9  
**Snippets:** 883

---

## Pydantic Settings Pattern

### Basic Settings Class
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Application settings
    app_name: str = "Awesome API"
    admin_email: str
    items_per_user: int = 50
    
    # Database settings
    database_url: str
    database_timeout: int = 30
    
    # API keys
    api_key: str
    secret_key: str
    
    # Configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )
```

---

## Reading from .env Files

### .env File Example
```bash
# .env
APP_NAME="MyApp"
ADMIN_EMAIL="admin@example.com"
DATABASE_URL="postgresql://localhost/mydb"
API_KEY="secret-api-key-here"
SECRET_KEY="super-secret-key"
```

### Settings with .env
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str
    admin_email: str
    database_url: str
    api_key: str
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

# Automatically reads from .env
settings = Settings()
```

---

## Settings as Dependency

### Singleton Pattern with lru_cache
```python
from functools import lru_cache
from fastapi import Depends, FastAPI

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Only creates Settings once, then caches
    return Settings()

app = FastAPI()

@app.get("/")
def read_settings(settings: Settings = Depends(get_settings)):
    return {"app_name": settings.app_name}
```

**Benefits:**
- Settings loaded once
- Reused across requests
- Efficient file I/O
- Easy to test (can override)

---

## Testing with Override

### Override Settings in Tests
```python
from fastapi.testclient import TestClient

def get_settings_override():
    return Settings(
        app_name="TestApp",
        admin_email="test@example.com",
        api_key="test-key"
    )

app.dependency_overrides[get_settings] = get_settings_override

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.json()["app_name"] == "TestApp"
```

---

## Environment Variables

### Running with Env Vars
```bash
# Set env vars in command line
ADMIN_EMAIL="admin@example.com" APP_NAME="MyApp" fastapi run main.py

# Or use .env file
# Settings automatically reads from .env
```

### Multiple Environment Files
```python
class Settings(BaseSettings):
    app_name: str
    
    model_config = SettingsConfigDict(
        # Can specify multiple files
        env_file=(".env", ".env.local", ".env.production"),
        env_file_encoding="utf-8"
    )
```

---

## Type Validation

### Automatic Type Conversion
```python
class Settings(BaseSettings):
    # String
    app_name: str
    
    # Integer (auto-converts from env var string)
    port: int = 8000
    
    # Boolean (accepts true/false, 1/0, yes/no)
    debug: bool = False
    
    # Float
    timeout: float = 30.5
    
    # List (comma-separated in .env)
    allowed_hosts: list[str] = []
    
    # Optional
    api_key: str | None = None
```

### .env File for Above
```bash
APP_NAME=MyApp
PORT=8080
DEBUG=true
TIMEOUT=45.5
ALLOWED_HOSTS=localhost,127.0.0.1,example.com
API_KEY=optional-key
```

---

## Advanced Features

### Nested Settings
```python
class DatabaseSettings(BaseModel):
    url: str
    port: int = 5432
    username: str
    password: str

class Settings(BaseSettings):
    app_name: str
    database: DatabaseSettings
    
    model_config = SettingsConfigDict(env_file=".env")
```

### Field Aliases
```python
class Settings(BaseSettings):
    app_name: str = Field(alias="APPLICATION_NAME")
    api_url: str = Field(alias="EXTERNAL_API_URL")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        populate_by_name=True  # Allow both name and alias
    )
```

### Computed Fields
```python
class Settings(BaseSettings):
    base_url: str
    api_version: str = "v1"
    
    @property
    def full_api_url(self) -> str:
        return f"{self.base_url}/{self.api_version}"
```

---

## Best Practices

### 1. Use Type Hints
```python
class Settings(BaseSettings):
    port: int  # Not just 'port'
    debug: bool  # Not just 'debug'
    timeout: float  # Not just 'timeout'
```

### 2. Provide Defaults
```python
class Settings(BaseSettings):
    port: int = 8000  # Default if not in env
    timeout: int = 30  # Safe default
    debug: bool = False  # Secure default
```

### 3. Use Descriptive Names
```python
class Settings(BaseSettings):
    database_url: str  # Clear
    redis_host: str  # Clear
    api_key: str  # Clear
```

### 4. Validate Critical Settings
```python
from pydantic import field_validator

class Settings(BaseSettings):
    api_key: str
    
    @field_validator('api_key')
    def validate_api_key(cls, v):
        if len(v) < 32:
            raise ValueError('API key too short')
        return v
```

---

## Common Patterns

### Conditional OpenAPI
```python
class Settings(BaseSettings):
    openapi_url: str = "/openapi.json"
    
settings = Settings()

app = FastAPI(openapi_url=settings.openapi_url)

# Disable OpenAPI in production:
# OPENAPI_URL="" in .env
```

### Database Connection
```python
class Settings(BaseSettings):
    database_url: str
    database_pool_size: int = 5
    database_max_overflow: int = 10
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()

# Use in database connection
engine = create_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow
)
```

---

## Migration from Environment Variables

### Before (Manual)
```python
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/db")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
```

### After (Pydantic Settings)
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://localhost/db"
    port: int = 8000
    debug: bool = False
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
```

**Benefits:**
- Type validation automatic
- Better error messages
- Single source of truth
- Easy testing

---

## Error Handling

### Missing Required Fields
```python
# If required field missing in .env:
class Settings(BaseSettings):
    api_key: str  # Required!

# Raises ValidationError if API_KEY not in environment
```

### Invalid Types
```python
# If PORT=abc in .env:
class Settings(BaseSettings):
    port: int

# Raises ValidationError: "value is not a valid integer"
```

---

**Saved to KB:** 2025-10-11  
**Topics:** pydantic_settings, environment_variables, configuration  
**Use Case:** Application configuration management  
**Complexity:** Low (simple pattern)  
**Applied To:** HA Ingestor config management system

