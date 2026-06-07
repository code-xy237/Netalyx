# boria_bridge.py — Pont Python ↔ BorIA (Java) via REST
# Lance BorIA comme sous-processus et expose une API simple.
import subprocess
import threading
import time
import logging
import os
import requests
from typing import Optional

logger = logging.getLogger("netalyx.boria")

BORIA_JAR  = os.path.join(os.path.dirname(__file__), "boria", "boria-ai-1.0.0.jar")
BORIA_HOST = "http://localhost"
BORIA_PORT = 8765
BORIA_URL  = f"{BORIA_HOST}:{BORIA_PORT}"
TIMEOUT    = 1.5   # secondes — BorIA offline ne doit jamais bloquer NETALYX


class BorIABridge:
    """
    Pont singleton vers le moteur BorIA.

    Utilisation :
        bridge = BorIABridge.get()
        reply  = bridge.chat("Explique cette alerte SYN scan")
        score  = bridge.predict_anomaly([0.8, 0.2, 1.0, 0.0, 120])
        summ   = bridge.summarize_alerts(alerts_list)
    """

    _instance: Optional["BorIABridge"] = None

    @classmethod
    def get(cls) -> "BorIABridge":
        if cls._instance is None:
            cls._instance = BorIABridge()
        return cls._instance

    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._online  = False
        self._lock    = threading.Lock()
        self._thread  = threading.Thread(target=self._heartbeat,
                                         daemon=True, name="BorIA-HB")
        self._thread.start()

    # ── Démarrage optionnel du JAR ─────────────────────────────────────
    def start_jar(self):
        """Lance le JAR BorIA si disponible. Silencieux sinon."""
        if not os.path.exists(BORIA_JAR):
            logger.info("BorIA JAR non trouvé — mode API-only (serveur externe attendu)")
            return
        try:
            self._proc = subprocess.Popen(
                ["java", "-jar", BORIA_JAR, "--port", str(BORIA_PORT)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            logger.info(f"BorIA JAR lancé (PID {self._proc.pid})")
        except FileNotFoundError:
            logger.warning("Java non trouvé — BorIA désactivé")

    def stop(self):
        if self._proc:
            self._proc.terminate()
            self._proc = None

    # ── Heartbeat ──────────────────────────────────────────────────────
    def _heartbeat(self):
        while True:
            try:
                r = requests.get(f"{BORIA_URL}/health", timeout=TIMEOUT)
                self._online = r.status_code == 200
            except Exception:
                self._online = False
            time.sleep(5)

    @property
    def online(self) -> bool:
        return self._online

    # ── API publique ───────────────────────────────────────────────────

    def chat(self, message: str) -> str:
        """Envoie un message texte à BorIA et retourne la réponse."""
        return self._post("/chat", {"message": message},
                          fallback=f"[BorIA hors ligne] {message}")

    def predict_anomaly(self, features: list) -> float:
        """Score d'anomalie ML (0.0 = normal, 1.0 = très suspect)."""
        result = self._post("/predict", {"features": features}, fallback=None)
        if result is None:
            return 0.0
        try:
            return float(result.get("score", 0.0))
        except Exception:
            return 0.0

    def analyze_alert(self, alert: dict) -> str:
        """Retourne une explication textuelle d'une alerte réseau."""
        return self._post(
            "/analyze-alert", alert,
            fallback=f"Alerte {alert.get('kind','?')} détectée depuis {alert.get('src','?')}."
        )

    def summarize_alerts(self, alerts: list) -> str:
        """Génère un résumé narratif d'une liste d'alertes (pour PDF)."""
        return self._post(
            "/summarize", {"incidents": alerts},
            fallback=self._local_summary(alerts)
        )

    def nlp_process(self, text: str) -> str:
        """Normalise et enrichit un texte via le NLP BorIA."""
        return self._post("/nlp", {"text": text}, fallback=text)

    # ── Interne ────────────────────────────────────────────────────────

    def _post(self, endpoint: str, payload: dict, fallback):
        if not self._online:
            return fallback
        try:
            with self._lock:
                r = requests.post(f"{BORIA_URL}{endpoint}",
                                  json=payload, timeout=TIMEOUT)
            data = r.json()
            # Cherche "reply", "text", "summary", "result" ou retourne le dict
            for key in ("reply", "text", "summary", "result"):
                if key in data:
                    return data[key]
            return str(data)
        except Exception as e:
            logger.debug(f"BorIA {endpoint} erreur : {e}")
            return fallback

    @staticmethod
    def _local_summary(alerts: list) -> str:
        """Résumé local si BorIA est hors ligne."""
        n = len(alerts)
        if n == 0:
            return "Aucune alerte enregistrée durant cette session."
        kinds = {}
        for a in alerts:
            k = a.get("kind", "UNKNOWN")
            kinds[k] = kinds.get(k, 0) + 1
        detail = ", ".join(f"{v}× {k}" for k, v in kinds.items())
        return (f"{n} alerte(s) enregistrée(s) durant la session : {detail}. "
                f"Consultez le journal pour plus de détails.")
