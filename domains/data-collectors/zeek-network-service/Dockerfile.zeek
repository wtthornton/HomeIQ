FROM zeek/zeek:8.1.1

# af_packet is now built into core (v8.1.0+) — no separate install needed
# Install community packages for device fingerprinting and ML features
# Device fingerprinting packages
# Removed: KYD, zeek-flowmeter (repos unavailable), hassh (incompatible with Zeek 8.1.1)
RUN zkg autoconfig --force && \
    zkg install --force https://github.com/salesforce/ja3 && \
    zkg install --force https://github.com/FoxIO-LLC/ja4

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

# Log output directory (zeek 8.1.1 runs as root; network capture requires CAP_NET_RAW)
RUN mkdir -p /zeek/logs
WORKDIR /zeek

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
