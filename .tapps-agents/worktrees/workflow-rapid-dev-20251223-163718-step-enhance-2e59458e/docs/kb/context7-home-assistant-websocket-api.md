# Home Assistant WebSocket API Documentation (Context7)

## Overview
This document contains Home Assistant WebSocket API documentation retrieved from Context7, focusing on authentication, long-lived access tokens, and WebSocket communication.

## Authentication Flow

### WebSocket Authentication Sequence

1. **Server sends `auth_required`**:
```json
{
  "type": "auth_required",
  "ha_version": "2021.5.3"
}
```

2. **Client sends `auth` with access token**:
```json
{
  "type": "auth",
  "access_token": "ABCDEFGHIJKLMNOPQ"
}
```

3. **Server responds with `auth_ok`** (success):
```json
{
  "type": "auth_ok",
  "ha_version": "2021.5.3"
}
```

4. **Server responds with `auth_invalid`** (failure):
```json
{
  "type": "auth_invalid",
  "message": "Invalid password"
}
```

## Long-Lived Access Token Generation

### WebSocket Command: `auth/long_lived_access_token`

**Request**:
```json
{
  "id": 11,
  "type": "auth/long_lived_access_token",
  "client_name": "GPS Logger",
  "client_icon": null,
  "lifespan": 365
}
```

**Parameters**:
- `id`: (integer) A unique message ID
- `type`: (string) Must be "auth/long_lived_access_token"
- `client_name`: (string) A descriptive name for the client using the token
- `client_icon`: (string, optional) An icon for the client (can be null)
- `lifespan`: (integer, optional) The token's validity in days (default is 3650 for 10 years)

**Success Response**:
```json
{
  "id": 11,
  "type": "result",
  "success": true,
  "result": "ABCDEFGH"
}
```

**Error Conditions**:
- 401 Unauthorized: If the initial authentication fails

## Signed Path Generation

### WebSocket Command: `auth/sign_path`

Generate temporary, signed URLs for accessing Home Assistant resources:

**Request**:
```json
{
  "type": "auth/sign_path",
  "path": "/api/states",
  "expires": 20
}
```

**Response**:
```json
{
  "path": "/api/states?authSig=ABCDEFGH"
}
```

## HTTP Authentication Examples

### Synchronous Authentication (Python with requests)

```python
import requests

class Auth:
    """Class to make authenticated requests."""

    def __init__(self, host: str, access_token: str):
        """Initialize the auth."""
        self.host = host
        self.access_token = access_token

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make a request."""
        if headers := kwargs.pop("headers", {}):
            headers = dict(headers)
        headers["authorization"] = self.access_token

        return requests.request(
            method, f"{self.host}/{path}", **kwargs, headers=headers,
        )
```

**Usage**:
```python
from my_package import Auth

auth = Auth("http://example.com/api", "secret_access_token")

# This will fetch data from http://example.com/api/lights
resp = auth.request("get", "lights")
print("HTTP response status code", resp.status_code)
print("HTTP response JSON content", resp.json())
```

### Asynchronous Authentication (Python with aiohttp)

```python
from aiohttp import ClientSession, ClientResponse

class Auth:
    """Class to make authenticated requests."""

    def __init__(self, websession: ClientSession, host: str, access_token: str):
        """Initialize the auth."""
        self.websession = websession
        self.host = host
        self.access_token = access_token

    async def request(self, method: str, path: str, **kwargs) -> ClientResponse:
        """Make a request."""
        if headers := kwargs.pop("headers", {}):
            headers = dict(headers)
        headers["authorization"] = self.access_token

        return await self.websession.request(
            method, f"{self.host}/{path}", **kwargs, headers=headers,
        )
```

**Usage**:
```python
import asyncio
import aiohttp

from my_package import Auth

async def main():
    async with aiohttp.ClientSession() as session:
        auth = Auth(session, "http://example.com/api", "secret_access_token")

        # This will fetch data from http://example.com/api/lights
        resp = await auth.request("get", "lights")
        print("HTTP response status code", resp.status)
        print("HTTP response JSON content", await resp.json())

asyncio.run(main())
```

## OAuth2 Authentication

### Abstract OAuth2 Authentication Class

```python
from abc import ABC, abstractmethod

class AbstractAuth(ABC):
    """Abstract class to make authenticated requests."""

    def __init__(self, websession: ClientSession, host: str):
        """Initialize the auth."""
        self.websession = websession
        self.host = host

    @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return a valid access token."""

    async def request(self, method, url, **kwargs) -> ClientResponse:
        """Make a request."""
        if headers := kwargs.pop("headers", {}):
            headers = dict(headers)

        access_token = await self.async_get_access_token()
        headers["authorization"] = f"Bearer {access_token}"

        return await self.websession.request(
            method, f"{self.host}/{url}", **kwargs, headers=headers,
        )
```

## WebSocket API Security

### Securing WebSocket Endpoints

Use the `@websocket_api.require_admin` decorator to secure WebSocket endpoints:

```python
from homeassistant.components import websocket_api

async def async_setup(hass, config):
    websocket_api.async_register_command(hass, websocket_create)
    return True

@websocket_api.require_admin
@websocket_api.async_response
@websocket_api.websocket_command(
    {vol.Required("type"): "my-component/my-action",}
)
async def websocket_create(hass, connection, msg):
    """Create a user."""
    # Do action
```

## Configuration Examples

### WebSocket API Integration

```yaml
websocket_api:
```

### REST API with Authentication

```yaml
sensor:
  - platform: rest
    resource: http://IP_ADDRESS:5000/sensor
    username: ha1
    password: test1
    authentication: basic
    headers:
      User-Agent: Home Assistant
      Content-Type: application/json
```

### MQTT with Bearer Token

```bash
curl -X POST \
    -H "Authorization: Bearer ABCDEFGH" \
    -H "Content-Type: application/json" \
    -d '{"payload": "Test message from HA", "topic": "home/notification"}' \
    http://IP_ADDRESS:8123/api/services/mqtt/publish
```

## Authentication Providers

### Home Assistant Authentication

```yaml
homeassistant:
  auth_providers:
   - type: homeassistant
   # uncomment this to enable backwards compatible API password support
   # - type: legacy_api_password
```

### Trusted Networks Authentication

```yaml
homeassistant:
  auth_providers:
    - type: trusted_networks
      trusted_networks:
        - 192.168.0.0/24
        - 192.168.10.0/24
        - fd00::/8
      trusted_users:
        192.168.0.1: user1_id
        192.168.0.0/24:
          - user1_id
          - user2_id
        "fd00::/8":
          - user1_id
          - group: system-users
```

## External Authentication

### Frontend External Authentication

```javascript
// To be called by external app
window.externalAuthSetToken(true, {
  access_token: "qwere",
  expires_in: 1800
});

// If unable to get new access token
window.externalAuthSetToken(false);
```

## Prometheus Integration

### Prometheus Scrape Config with Long-Lived Token

```yaml
# Example Prometheus scrape_configs entry (For version 2.26+)
  - job_name: "hass"
    scrape_interval: 60s
    metrics_path: /api/prometheus

    # Long-Lived Access Token
    authorization:
      credentials: "your.longlived.token"

    scheme: https
    static_configs:
      - targets: ['HOSTNAME:8123']
```

## Key Points for HA Ingestor Implementation

1. **Long-lived access tokens** are required for persistent connections
2. **WebSocket authentication** follows a specific sequence: `auth_required` → `auth` → `auth_ok`/`auth_invalid`
3. **Bearer token format** is used for HTTP API requests: `Authorization: Bearer <token>`
4. **Token generation** can be done via WebSocket API or Home Assistant UI
5. **Signed paths** provide temporary access without full authentication
6. **Admin decorators** can secure WebSocket endpoints

## Sources

- Home Assistant Core: `/home-assistant/core`
- Home Assistant Documentation: `/home-assistant/home-assistant.io`
- Home Assistant Developer Docs: `/websites/developers_home-assistant_io`

## Last Updated

January 2025 - Retrieved from Context7 for HA Ingestor fallback implementation
