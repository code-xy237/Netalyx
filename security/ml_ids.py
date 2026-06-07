# security/ml_ids.py — ML IDS Netalyx PRO + Intégration BorIA #1
# Double moteur : Isolation Forest (sklearn) + Réseau neuronal BorIA
import threading
import time
import logging
from collections import deque
from typing import Callable, Optional

logger = logging.getLogger("netalyx.mlids")

try:
    import numpy as np
    from sklearn.ensemble import IsolationForest
    SK_AVAILABLE = True
except ImportError:
    SK_AVAILABLE = False
    logger.warning("scikit-learn non dispo — ML IDS limité")


# ══════════════════════════════════════════════════════════════════════
#  EXTRACTEUR DE FEATURES
# ══════════════════════════════════════════════════════════════════════
def extract_features(pkt: dict) -> Optional[list]:
    """Extrait un vecteur de 6 features d'un paquet réseau."""
    try:
        proto_map = {"TCP": 1, "UDP": 2, "ICMP": 3, "ARP": 4, "OTHER": 5}
        proto  = proto_map.get(str(pkt.get("proto", "")).upper(), 0)
        dport  = int(pkt.get("dport") or 0)
        sport  = int(pkt.get("sport") or 0)
        length = int(pkt.get("length") or 0)
        flags  = int(pkt.get("flags")  or 0)
        ttl    = int(pkt.get("ttl")    or 64)
        return [proto, dport / 65535, sport / 65535,
                min(length, 65535) / 65535, flags / 255, ttl / 255]
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════
#  SERVICE ML IDS
# ══════════════════════════════════════════════════════════════════════
class MLIDSService:
    """
    Détecteur d'anomalies ML :
    - Buffer de 500 paquets pour entraînement initial
    - Isolation Forest (sklearn) comme moteur primaire
    - Score BorIA comme moteur secondaire (vote pondéré)
    - Réentraînement périodique toutes les 5 min
    """

    TRAIN_SIZE    = 500
    RETRAIN_EVERY = 300   # secondes
    ANOMALY_THR   = 0.65  # seuil vote combiné pour déclencher alerte

    def __init__(self, alert_sink: Callable):
        self._sink      = alert_sink
        self._buffer    = deque(maxlen=2000)
        self._model     = None
        self._trained   = False
        self._lock      = threading.Lock()
        self._last_train = 0.0
        self._scores    = deque(maxlen=200)
        self._thread    = threading.Thread(target=self._train_loop,
                                           daemon=True, name="MLIDS-Train")
        self._thread.start()

    # ── Alimentation ───────────────────────────────────────────────────
    def feed(self, pkt: dict):
        feat = extract_features(pkt)
        if feat is None:
            return
        with self._lock:
            self._buffer.append(feat)

        if self._trained:
            self._score_packet(pkt, feat)

    # ── Scoring temps réel ─────────────────────────────────────────────
    def _score_packet(self, pkt: dict, feat: list):
        score_sk = self._isolation_score(feat)
        score_bo = self._boria_score(feat)

        # Vote pondéré : 60% IsolationForest, 40% BorIA
        combined = score_sk * 0.6 + score_bo * 0.4
        self._scores.append(combined)

        if combined >= self.ANOMALY_THR:
            self._sink("ANOMALY_DETECTED", {
                "src":    pkt.get("src", "?"),
                "dst":    pkt.get("dst", "?"),
                "proto":  pkt.get("proto", "?"),
                "dport":  pkt.get("dport", "?"),
                "score":  round(combined, 3),
                "detail": f"Score anomalie : {combined:.2%} (IF:{score_sk:.2f} BorIA:{score_bo:.2f})"
            })

    def _isolation_score(self, feat: list) -> float:
        if not SK_AVAILABLE or self._model is None:
            return 0.0
        try:
            import numpy as np
            arr = np.array(feat).reshape(1, -1)
            raw = self._model.score_samples(arr)[0]
            # score_samples : plus négatif = plus anormal → normaliser [0,1]
            return max(0.0, min(1.0, -raw / 0.5))
        except Exception:
            return 0.0

    def _boria_score(self, feat: list) -> float:
        """Intégration BorIA #1 — score anomalie via REST."""
        try:
            from boria_bridge import BorIABridge
            return BorIABridge.get().predict_anomaly(feat)
        except Exception:
            return 0.0

    # ── Entraînement ───────────────────────────────────────────────────
    def _train_loop(self):
        while True:
            time.sleep(10)
            with self._lock:
                buf_len = len(self._buffer)
            if buf_len >= self.TRAIN_SIZE:
                now = time.time()
                if now - self._last_train >= self.RETRAIN_EVERY or not self._trained:
                    self._train()
                    self._last_train = now

    def _train(self):
        if not SK_AVAILABLE:
            return
        try:
            import numpy as np
            with self._lock:
                data = list(self._buffer)
            X = np.array(data)
            model = IsolationForest(n_estimators=120, contamination=0.05,
                                    random_state=42, n_jobs=-1)
            model.fit(X)
            with self._lock:
                self._model   = model
                self._trained = True
            self._sink("ML_MODEL_READY", {
                "message": f"Modèle entraîné sur {len(data)} paquets"
            })
            logger.info(f"Isolation Forest entraîné sur {len(data)} paquets")
        except Exception as e:
            self._sink("ML_TRAIN_ERROR", {"error": str(e)})
            logger.error(f"Erreur entraînement : {e}")

    # ── Stats ──────────────────────────────────────────────────────────
    def stats(self) -> dict:
        with self._lock:
            buf = len(self._buffer)
        avg = (sum(self._scores) / len(self._scores)) if self._scores else 0.0
        return {
            "trained":    self._trained,
            "buffer":     buf,
            "avg_score":  round(avg, 4),
            "model":      "IsolationForest+BorIA" if self._trained else "En attente"
        }
