# ids/alerts.py — Système d'alertes Netalyx PRO + Intégration BorIA #3
import json
import threading
from datetime import datetime
from common import CFG

ALERTS_LOG = CFG["logging"]["alerts_log"]
_lock = threading.Lock()

# Cache des alertes en mémoire pour résumé BorIA
_session_alerts = []
_alerts_lock    = threading.Lock()


def log_alert(kind: str, detail: dict):
    """Enregistre une alerte dans le fichier log et enrichit via BorIA."""
    rec = {
        "time":   datetime.utcnow().isoformat(),
        "kind":   kind,
        "detail": detail
    }

    # Enrichissement BorIA (Intégration #3)
    try:
        from boria_bridge import BorIABridge
        bridge = BorIABridge.get()
        if bridge.online:
            explication = bridge.analyze_alert({"kind": kind, **detail})
            rec["boria_explication"] = explication
    except Exception:
        pass

    # Persistance
    with _lock:
        with open(ALERTS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Stockage session
    with _alerts_lock:
        _session_alerts.append(rec)
        if len(_session_alerts) > 1000:
            _session_alerts.pop(0)


def get_session_alerts() -> list:
    """Retourne les alertes de la session en cours (pour rapport PDF)."""
    with _alerts_lock:
        return list(_session_alerts)


def get_boria_summary() -> str:
    """Génère un résumé IA de toutes les alertes de la session."""
    alerts = get_session_alerts()
    try:
        from boria_bridge import BorIABridge
        return BorIABridge.get().summarize_alerts(alerts)
    except Exception:
        n = len(alerts)
        return f"{n} alerte(s) enregistrée(s) durant cette session."
