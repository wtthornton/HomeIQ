# HomeIQ-specific Zeek scripts

module HomeIQ;

# Track local network (configurable)
redef Site::local_nets += { 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12 };

# Increase connection tracking for long-lived IoT connections
redef tcp_inactivity_timeout = 30 min;
redef udp_inactivity_timeout = 10 min;

# Scan detection thresholds removed — Scan module API changed in Zeek 8.x
# Notice::policy redef removed — not &redef in Zeek 8.x
