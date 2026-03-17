# HomeIQ Zeek Configuration
# JSON output for all logs
redef LogAscii::use_json = T;

# Log rotation: 5 minutes (matches polling interval)
redef Log::default_rotation_interval = 5 min;

# Log directory
redef Log::default_logdir = "/zeek/logs";

# Enable MQTT analyzer
@load protocols/mqtt

# Load community packages
@load packages

# Load HomeIQ custom scripts
@load homeiq.zeek

# Reduce noise: disable rarely-needed logs for home networks
redef Log::disable_rotation_ifaces = set("reporter");
