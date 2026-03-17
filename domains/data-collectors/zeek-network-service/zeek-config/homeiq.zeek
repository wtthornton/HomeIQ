# HomeIQ-specific Zeek scripts

module HomeIQ;

# Track local network (configurable)
redef Site::local_nets += { 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12 };

# Increase connection tracking for long-lived IoT connections
redef tcp_inactivity_timeout = 30 min;
redef udp_inactivity_timeout = 10 min;

# Lower thresholds for scan detection (home networks are small)
redef Scan::addr_scan_threshold = 10;
redef Scan::port_scan_threshold = 15;

# Enable notices for new connections to external IPs
# (useful for detecting devices phoning home)
redef Notice::policy += {
    [$action = Notice::ACTION_LOG,
     $pred(n: Notice::Info) = { return n$note == Weird::Activity; }]
};
