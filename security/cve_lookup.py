# security/cve_lookup.py — Corrélation CVE via API NVD (gratuite, sans clé)
import re
import requests

NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"

# Mots-clés extraits des bannières -> terme de recherche NVD
SERVICE_PATTERNS = [
    (r"OpenSSH[_\s/]?([\d.]+)", "OpenSSH"),
    (r"Apache[/\s]([\d.]+)", "Apache HTTP Server"),
    (r"nginx[/\s]([\d.]+)", "nginx"),
    (r"vsftpd\s*([\d.]+)", "vsftpd"),
    (r"ProFTPD\s*([\d.]+)", "ProFTPD"),
    (r"Microsoft-IIS[/\s]([\d.]+)", "Microsoft IIS"),
    (r"Postfix\s*([\d.]+)", "Postfix"),
    (r"MySQL\s*([\d.]+)", "MySQL"),
    (r"MariaDB\s*([\d.]+)", "MariaDB"),
    (r"Redis\s*([\d.]+)", "Redis"),
]

def parse_service_version(banner: str) -> tuple[str, str] | None:
    """Extrait (nom_service, version) depuis une bannière."""
    if not banner:
        return None
    for pattern, name in SERVICE_PATTERNS:
        m = re.search(pattern, banner, re.IGNORECASE)
        if m:
            return name, m.group(1)
    return None

def lookup_cves(service: str, version: str, max_results: int = 5) -> list:
    """Interroge l'API NVD et retourne les CVEs les plus critiques."""
    try:
        params = {
            "keywordSearch": f"{service} {version}",
            "resultsPerPage": max_results,
            "sortBy": "score",
            "sortOrder": "dsc"
        }
        r = requests.get(NVD_API, params=params, timeout=8)
        if r.status_code != 200:
            return []
        data = r.json()
        cves = []
        for item in data.get("vulnerabilities", []):
            cve = item.get("cve", {})
            cve_id = cve.get("id", "?")
            desc = next(
                (d["value"] for d in cve.get("descriptions", []) if d["lang"] == "en"),
                "Aucune description"
            )
            metrics = cve.get("metrics", {})
            score = None
            severity = "UNKNOWN"
            for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                if key in metrics and metrics[key]:
                    cvss = metrics[key][0].get("cvssData", {})
                    score = cvss.get("baseScore")
                    severity = cvss.get("baseSeverity", "?")
                    break
            cves.append({"id": cve_id, "score": score, "severity": severity, "desc": desc[:200]})
        return cves
    except Exception:
        return []

def enrich_banner(banner: str) -> dict:
    """Pipeline complet : bannière -> service/version -> CVEs."""
    result = {"service": None, "version": None, "cves": []}
    parsed = parse_service_version(banner)
    if not parsed:
        return result
    service, version = parsed
    result["service"] = service
    result["version"] = version
    result["cves"] = lookup_cves(service, version)
    return result
