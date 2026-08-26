FROM zeek/zeek:8.1.1

# af_packet is now built into core (v8.1.0+) — no separate install needed
# Install community packages for device fingerprinting and ML features
# Device fingerprinting packages
# Removed: KYD, zeek-flowmeter (repos unavailable), hassh (incompatible with Zeek 8.1.1)
#
# Both packages are pinned to a git ref instead of floating on the default
# branch HEAD -- an unpinned install breaks whenever upstream moves. ja4 in
# particular is pinned to v0.18.8, NOT the newest tag (v1.0.0): v1.0.0
# rewrote ja4 as a native C++20 plugin (build_command = cmake + make,
# requirements: "C++20 compiler, CMake 3.15+"), and this base image
# (zeek/zeek:8.1.1, Debian trixie) ships neither cmake nor a C++ compiler --
# confirmed locally (`which cmake` / `which gcc g++ clang++` all fail in the
# image). That is not a Zeek-version incompatibility; it is a missing build
# toolchain that would need to be added to this image regardless of which
# ja4 ref is chosen. v0.18.8 is the newest ja4 tag before that rewrite: a
# pure Zeek-script package (script_dir = zeek, no build_command, depends
# zeek >=5.0.0), which installs and loads cleanly against zeek 8.1.1 with
# the toolchain this image already has.
#
# salesforce/ja3 has no tags at all -- pinned to its current master commit
# so it stops floating too, on the same defect class.
RUN zkg autoconfig --force && \
    zkg install --force --version 502cc6395811c54743b0561419d61900a6df3ff7 https://github.com/salesforce/ja3 && \
    zkg install --force --version v0.18.8 https://github.com/FoxIO-LLC/ja4

# Copy custom Zeek configuration
COPY domains/data-collectors/zeek-network-service/zeek-config/local.zeek /usr/local/zeek/share/zeek/site/local.zeek
COPY domains/data-collectors/zeek-network-service/zeek-config/homeiq.zeek /usr/local/zeek/share/zeek/site/homeiq.zeek

# Entrypoint script for env var expansion
COPY domains/data-collectors/zeek-network-service/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Healthcheck script — process alive + log freshness (Epic 82)
COPY domains/data-collectors/zeek-network-service/healthcheck.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/healthcheck.sh

HEALTHCHECK --interval=60s --timeout=10s --retries=3 --start-period=120s \
    CMD /usr/local/bin/healthcheck.sh

# Zeek telemetry port — Prometheus metrics (Epic 86, no effect with host networking but documents the contract)
EXPOSE 9911

# Log output directory (zeek 8.1.1 runs as root; network capture requires CAP_NET_RAW)
RUN mkdir -p /zeek/logs
WORKDIR /zeek

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
