# HomeIQ pre-provisioned Home Assistant image (TAP-6483).
#
# Every component the appliance needs is baked in at BUILD time. HACS is used to
# *source* these components during development and is deliberately absent from
# the shipped image: no Supervisor, no GitHub device-code prompt, and no network
# dependency on first boot.
#
# Build context is the REPO ROOT (it copies custom_components/homeiq and the ZHA
# quirk out of libs/):
#   docker build -f domains/core-platform/home-assistant/Dockerfile -t homeiq/home-assistant:<ver> .
#
# Versions here are the source of truth and are mirrored into
# infrastructure/ha-components.lock.json, which scripts/check-ha-component-manifest.py
# enforces in CI. Change one, change both, or CI fails.

# ---------------------------------------------------------------------------
# Stage 1 — fetch and unpack the vendored HACS components.
# Kept out of the final image so curl/tar never ship.
# ---------------------------------------------------------------------------
FROM alpine:3.22 AS vendor

ARG POWERCALC_VERSION=v1.25.1
ARG TEAMTRACKER_VERSION=v0.18.1

RUN apk add --no-cache curl tar

WORKDIR /vendor

# Powercalc — bramstroker/homeassistant-powercalc
RUN curl -fsSL --retry 3 \
      "https://github.com/bramstroker/homeassistant-powercalc/archive/refs/tags/${POWERCALC_VERSION}.tar.gz" \
      -o powercalc.tar.gz \
 && mkdir -p /vendor/out \
 && tar -xzf powercalc.tar.gz --strip-components=2 -C /vendor/out \
      "homeassistant-powercalc-${POWERCALC_VERSION#v}/custom_components/powercalc" \
 && test -f /vendor/out/powercalc/manifest.json

# Team Tracker — vasqued2/ha-teamtracker
RUN curl -fsSL --retry 3 \
      "https://github.com/vasqued2/ha-teamtracker/archive/refs/tags/${TEAMTRACKER_VERSION}.tar.gz" \
      -o teamtracker.tar.gz \
 && tar -xzf teamtracker.tar.gz --strip-components=2 -C /vendor/out \
      "ha-teamtracker-${TEAMTRACKER_VERSION#v}/custom_components/teamtracker" \
 && test -f /vendor/out/teamtracker/manifest.json

# Stamp the release tag into each vendored manifest.json.
#
# HACS rewrites `version` at install time; the upstream tarballs carry whatever
# placeholder the repo has (powercalc ships "0.1.1" regardless of the tag). Since
# we vendor from the tarball we must do the stamping ourselves, or the shipped
# image cannot say which version it shipped — the exact drift-invisibility this
# story exists to prevent.
RUN apk add --no-cache python3 \
 && python3 - "$POWERCALC_VERSION" "$TEAMTRACKER_VERSION" <<'PYSTAMP'
import json, sys, pathlib
for name, ver in (("powercalc", sys.argv[1]), ("teamtracker", sys.argv[2])):
    p = pathlib.Path("/vendor/out") / name / "manifest.json"
    m = json.loads(p.read_text())
    m["version"] = ver.lstrip("v")
    p.write_text(json.dumps(m, indent=2) + "\n")
    print(f"stamped {name} -> {m['version']}")
PYSTAMP

# ---------------------------------------------------------------------------
# Stage 2 — the shipped image.
# Pinned, never :stable. An appliance that follows a moving tag will eventually
# boot into a breaking release with nobody present to notice.
# ---------------------------------------------------------------------------
FROM ghcr.io/home-assistant/home-assistant:2026.8.3

# No USER instruction, deliberately. The upstream HA container runs as root
# because Home Assistant needs direct hardware access — ZHA talks to the Zigbee
# coordinator over /dev/ttyUSB*, and Bluetooth needs the host stack. Dropping to
# a non-root user breaks the Zigbee radio this appliance is built around. This is
# a considered exception to the usual non-root rule, not an oversight.

# HEALTHCHECK here as well as in compose, so a plain `docker run` is also
# observable. /manifest.json, not /api/: HA answers /api/ with 401 without a
# bearer token and `curl -f` fails on it, so an /api/ check can never pass.
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
  CMD curl -f http://localhost:8123/manifest.json || exit 1

LABEL org.opencontainers.image.title="HomeIQ Home Assistant" \
      org.opencontainers.image.description="Pre-provisioned HA with vendored components, no HACS at runtime" \
      org.opencontainers.image.source="https://github.com/wtthornton/HomeIQ"

# Vendored HACS components.
COPY --from=vendor /vendor/out/powercalc   /config/custom_components/powercalc
COPY --from=vendor /vendor/out/teamtracker /config/custom_components/teamtracker

# HomeIQ's own integration, straight from the repo.
COPY custom_components/homeiq /config/custom_components/homeiq

# The Aqara FP1E ZHA quirk. This is NOT a custom_component — zhaquirks.setup()
# only reads the directory named by `zha.custom_quirks_path`, which the seeded
# configuration.yaml points here. TAP-6483's acceptance text says
# custom_components/ for all four; that is wrong for this one file.
COPY libs/homeiq-ha/src/homeiq_ha/agent/quirks/aqara_fp1e.py \
     /config/custom_zha_quirks/aqara_fp1e.py

# Seed config. Without it HA writes a default configuration.yaml on first boot
# and the `zha:` block the quirk depends on would never exist.
COPY domains/core-platform/home-assistant/config/ /config/

# Build-time assertions. A silently-empty COPY would otherwise ship an image
# that starts fine and is missing the thing the story exists to deliver.
RUN set -eu; \
    for c in powercalc teamtracker homeiq; do \
      test -f "/config/custom_components/$c/manifest.json" \
        || { echo "FATAL: /config/custom_components/$c/manifest.json missing"; exit 1; }; \
    done; \
    test -f /config/custom_zha_quirks/aqara_fp1e.py \
      || { echo "FATAL: aqara_fp1e.py quirk missing"; exit 1; }; \
    test ! -e /config/custom_components/hacs \
      || { echo "FATAL: HACS present in a build-time-provisioned image"; exit 1; }; \
    echo "OK: 3 custom_components + 1 zha quirk, no HACS"
