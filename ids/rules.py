# ids/rules.py
from common import CFG

class IDSConfig:
    packet_rate_threshold  = CFG["ids"]["packet_rate_threshold"]
    syn_scan_threshold     = CFG["ids"]["syn_scan_threshold"]
    port_probe_threshold   = CFG["ids"]["port_probe_threshold"]
    burst_window_seconds   = CFG["ids"]["burst_window_seconds"]
    alert_cooldown_seconds = CFG["ids"].get("alert_cooldown_seconds", 30)
