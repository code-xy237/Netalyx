# security/threat_intel.py — Enrichissement IP via AbuseIPDB & VirusTotal
import requests
import threading
from common import CFG

_cache = {}
_lock  = threading.Lock()

ABUSEIPDB_URL  = "https://api.abuseipdb.com/api/v2/check"
VIRUSTOTAL_URL = "https://www.virustotal.com/api/v3/ip_addresses"

def check_abuseipdb(ip: str) -> dict:
    key = CFG.get("threat_intel", {}).get("abuseipdb_key", "")
    if not key:
        return {}
    try:
        r = requests.get(ABUSEIPDB_URL,
                         headers={"Key": key, "Accept": "application/json"},
                         params={"ipAddress": ip, "maxAgeInDays": 90},
                         timeout=5)
        if r.status_code == 200:
            d = r.json().get("data", {})
            return {
                "abuse_score":    d.get("abuseConfidenceScore", 0),
                "country":        d.get("countryCode", "?"),
                "total_reports":  d.get("totalReports", 0),
                "isp":            d.get("isp", "?"),
                "is_tor":         d.get("isTor", False),
            }
    except Exception:
        pass
    return {}

def check_virustotal(ip: str) -> dict:
    key = CFG.get("threat_intel", {}).get("virustotal_key", "")
    if not key:
        return {}
    try:
        r = requests.get(f"{VIRUSTOTAL_URL}/{ip}",
                         headers={"x-apikey": key},
                         timeout=5)
        if r.status_code == 200:
            stats = r.json().get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
            return {
                "vt_malicious":  stats.get("malicious", 0),
                "vt_suspicious": stats.get("suspicious", 0),
                "vt_harmless":   stats.get("harmless", 0),
            }
    except Exception:
        pass
    return {}

def enrich_ip(ip: str, callback=None):
    """Enrichit une IP en arrière-plan et appelle callback(ip, result)."""
    with _lock:
        if ip in _cache:
            if callback:
                callback(ip, _cache[ip])
            return

    def _run():
        result = {"ip": ip}
        result.update(check_abuseipdb(ip))
        result.update(check_virustotal(ip))
        result["threat_score"] = _compute_score(result)
        with _lock:
            _cache[ip] = result
        if callback:
            callback(ip, result)

    threading.Thread(target=_run, daemon=True).start()

def _compute_score(r: dict) -> str:
    abuse = r.get("abuse_score", 0)
    mal   = r.get("vt_malicious", 0)
    if abuse >= 80 or mal >= 5:  return "CRITIQUE"
    if abuse >= 40 or mal >= 2:  return "SUSPECT"
    if abuse >= 10 or mal >= 1:  return "FAIBLE"
    return "PROPRE"

def get_cached(ip: str) -> dict | None:
    with _lock:
        return _cache.get(ip)
