# security/incident_timeline.py — Timeline d'incidents multi-logs
import json
import os
from datetime import datetime
from common import CFG

def load_timeline(hours: int = 24) -> list:
    """
    Agrège alerts.log + devices.log + traffic.log sur les N dernières heures.
    Retourne une liste triée par timestamp.
    """
    events = []
    cutoff = datetime.utcnow().timestamp() - hours * 3600

    # Alertes IDS
    alerts_log = CFG["logging"]["alerts_log"]
    if os.path.exists(alerts_log):
        with open(alerts_log, encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line.strip())
                    ts  = datetime.fromisoformat(rec["time"]).timestamp()
                    if ts >= cutoff:
                        events.append({
                            "time":     ts,
                            "type":     "ALERTE",
                            "kind":     rec.get("kind", "?"),
                            "src":      rec.get("detail", {}).get("src", "?"),
                            "detail":   str(rec.get("detail", {}))[:120],
                            "severity": _severity(rec.get("kind", ""))
                        })
                except Exception:
                    pass

    # Nouveaux appareils
    devices_log = CFG["logging"]["devices_log"]
    if os.path.exists(devices_log):
        with open(devices_log, encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line.strip())
                    ts  = float(rec.get("time", 0))
                    if ts >= cutoff:
                        events.append({
                            "time":     ts,
                            "type":     "APPAREIL",
                            "kind":     "NEW_DEVICE",
                            "src":      rec.get("ip", "?"),
                            "detail":   f"MAC={rec.get('mac','?')} | {rec.get('hostname','?')} | Ports={rec.get('open_ports',[])}",
                            "severity": "INFO"
                        })
                except Exception:
                    pass

    return sorted(events, key=lambda x: x["time"])

def _severity(kind: str) -> str:
    if kind in ("CRITICAL_INCIDENT", "IP_BLOCKED"):
        return "CRITIQUE"
    if kind in ("HIGH_PACKET_RATE", "SYN_SCAN", "PORT_PROBING"):
        return "ÉLEVÉ"
    return "INFO"

def filter_timeline(events: list,
                    ip: str = None,
                    kind: str = None,
                    severity: str = None) -> list:
    out = events
    if ip:
        out = [e for e in out if ip in e.get("src", "")]
    if kind:
        out = [e for e in out if kind in e.get("kind", "")]
    if severity:
        out = [e for e in out if e.get("severity") == severity]
    return out
