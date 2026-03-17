#!/bin/bash
set -e
# Use af_packet for high-performance capture (built into core since v8.1.0)
# Falls back to libpcap if af_packet unavailable (e.g., non-Linux hosts)
exec zeek -i "af_packet::${ZEEK_INTERFACE:-eth0}" local
