# Home Assistant Authentication Guidance

## Local NUC / On-Device Deployments (2025)

- **Token type:** Generate a Home Assistant *long-lived access token* from a local admin account. Short-lived UI tokens are not accepted by the device intelligence connector.
- **Scope:** Create a dedicated `homeiq-device-intelligence` user with `Administrator` privileges so registry update calls succeed without per-action prompts.
- **Rotation:** Regenerate the token quarterly. Update `HA_TOKEN` in the service secret store or `.env.websocket` via the Admin Console. Token refresh no longer requires container restarts—the service reconnects automatically.

## Connection Policy

- **Primary URL:** Point `HA_URL` to the local Home Assistant instance (e.g. `http://homeassistant.local:8123`). The WebSocket endpoint is derived automatically as `ws(s)://.../api/websocket`.
- **Fallback:** Configure `NABU_CASA_URL` only when remote access is required. On a single-site NUC, keep fallback empty to avoid routing private metadata through the cloud.
- **TLS:** When Home Assistant uses HTTPS with a self-signed certificate, store the CA in the container trust store and set `HA_SSL_VERIFY=true`. The WebSocket layer inherits the TLS verification flag.

## Reconnect Expectations

- **Backoff:** The client performs incremental backoff (`5s`, `10s`, `15s`, `20s`, `25s`). The schedule is capped at five retries per outage per Home Assistant guidance.
- **Session expiry:** When Home Assistant restarts, the connector automatically re-authenticates using the stored token and resumes registry subscriptions.
- **Observability:** Connection state transitions are logged at `INFO` level with emoji tags (`🔌`, `🔄`, `✅`). Monitor the `device-intelligence-service` logs if the analyzer stops producing findings.

## Security Checklist

- Store tokens using the Secure Secrets UI (Settings → Configuration). Files written through the UI are permissioned `600`.
- Restrict Docker host shell access; the token grants full Home Assistant privileges.
- Audit `device-intelligence-service` logs monthly for failed authentication or repeated reconnect attempts—these indicate stale tokens or network instability.

