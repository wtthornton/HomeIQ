# Per-service integration configs (TAP-5447)

`data-api` serves `/api/v1/integrations/{service}/config` (the dashboard's
ConfigForm) from `.env.{service}` files in this directory, mounted at
`/app/infrastructure` in the container. Files here hold per-service settings
the dashboard edits; they are gitignored like every `.env*`.

Seed a service with its template keys (values filled via the dashboard form
or by hand):

    printf 'HA_URL=\nHA_TOKEN=\nHA_SSL_VERIFY=true\nHA_RECONNECT_DELAY=5\n' > .env.websocket
    printf 'WEATHER_API_KEY=\nWEATHER_LAT=\nWEATHER_LON=\n' > .env.weather

A service with no file here answers 404 ("not configured") — that is the
route's honest semantics, not a defect.
