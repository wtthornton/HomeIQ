# HomeIQ Zeek Configuration
# JSON output for all logs
redef LogAscii::use_json = T;

# Zeek 8.x native telemetry — Prometheus metrics on port 9911 (Epic 86)
@load frameworks/telemetry
redef Telemetry::metrics_port = 9911;

# Log rotation: 5 minutes (matches polling interval)
redef Log::default_rotation_interval = 5 min;

# Log directory
redef Log::default_logdir = "/zeek/logs";

# MQTT analyzer: not included in zeek/zeek:8.1.1 base image
# Uncomment if using a build with MQTT support compiled in
# @load protocols/mqtt

# Load community packages
@load packages

# Load HomeIQ custom scripts
@load homeiq.zeek

# Log::disable_rotation_ifaces removed in Zeek 8.x
