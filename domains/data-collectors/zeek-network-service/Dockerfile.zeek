FROM zeek/zeek:8.1.1

# af_packet is now built into core (v8.1.0+) — no separate install needed
# Install community packages for device fingerprinting and ML features
RUN zkg autoconfig && \
    zkg install --force \
        zeek/ja3 \
        foxio-n/ja4 \
        salesforce/hassh \
        corelight/KYD \
        SuperCowPowers/zeek-flowmeter

# Copy custom Zeek configuration
COPY domains/data-collectors/zeek-network-service/zeek-config/local.zeek /usr/local/zeek/share/zeek/site/local.zeek
COPY domains/data-collectors/zeek-network-service/zeek-config/homeiq.zeek /usr/local/zeek/share/zeek/site/homeiq.zeek

# Entrypoint script for env var expansion
COPY domains/data-collectors/zeek-network-service/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Log output directory
RUN mkdir -p /zeek/logs && chown -R zeek:zeek /zeek

USER zeek
WORKDIR /zeek

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
