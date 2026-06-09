# security/ml_ids.py — ML IDS Netalyx PRO + Intégration BorIA
# Double moteur : Isolation Forest (sklearn) + Réseau neuronal BorIA
import os
import threading
import time
import logging
from collections import deque
from typing import Callable, Optional

logger = logging.getLogger("netalyx.mlids")

MODEL_PATH  = os.path.join("logs", "ml_model.joblib")
SCALER_PATH = os.path.join("logs", "ml_scaler.joblib")

try:
    import numpy as np
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    import joblib
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
    Détecteur d'anomalies ML avec gestion de phases :
      mode == 'idle'      : en attente
      mode == 'training'  : collecte de paquets normaux
      mode == 'detecting' : détection active d'anomalies
    """

    ANOMALY_THR = 0.65

    def __init__(self, alert_sink: Callable):
        self._sink          = alert_sink
        self._lock          = threading.Lock()

        # État machine
        self._mode          = "idle"   # 'idle' | 'training' | 'detecting'

        # Collecte / modèle
        self._train_buffer  = deque(maxlen=50000)
        self._model         = None
        self._scaler        = None
        self._loaded        = False

        # Stats
        self._total_seen    = 0
        self._total_anomaly = 0
        self._recent        = deque(maxlen=500)   # pour recent_anomalies()
        self._scores        = deque(maxlen=200)

        # Référence pour _delete_model dans ml_tab
        self.detector       = self   # ml_tab fait self.ml.detector._loaded

        # Tenter de charger un modèle persisté
        self._try_load_model()

    # ── Propriété mode (lecture seule) ─────────────────────────────────
    @property
    def mode(self) -> str:
        return self._mode

    # ── Propriété sample_count ─────────────────────────────────────────
    @property
    def sample_count(self) -> int:
        return len(self._train_buffer)

    # ── Phase 1 : apprentissage ────────────────────────────────────────
    def start_training(self):
        with self._lock:
            self._train_buffer.clear()
            self._mode = "training"
        logger.info("ML IDS : phase d'apprentissage démarrée")

    def stop_training_and_fit(self, contamination: float = 0.05) -> str:
        """Arrête la collecte et entraîne le modèle. Retourne un message."""
        with self._lock:
            data = list(self._train_buffer)
            self._mode = "idle"

        if not SK_AVAILABLE:
            return "✗ scikit-learn non disponible — entraînement impossible."
        if len(data) < 50:
            return f"✗ Pas assez de données ({len(data)} paquets, minimum 50)."

        try:
            X = np.array(data)
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            model = IsolationForest(
                n_estimators=120,
                contamination=contamination,
                random_state=42,
                n_jobs=-1
            )
            model.fit(X_scaled)

            with self._lock:
                self._model   = model
                self._scaler  = scaler
                self._loaded  = True

            # Sauvegarde sur disque
            os.makedirs("logs", exist_ok=True)
            joblib.dump(model,  MODEL_PATH)
            joblib.dump(scaler, SCALER_PATH)

            msg = f"✓ Modèle entraîné sur {len(data)} paquets (contamination={contamination:.0%})"
            logger.info(msg)
            self._sink("ML_MODEL_READY", {"message": msg})
            return msg
        except Exception as e:
            logger.error(f"Erreur entraînement : {e}")
            self._sink("ML_TRAIN_ERROR", {"error": str(e)})
            return f"✗ Erreur : {e}"

    # ── Phase 2 : détection ────────────────────────────────────────────
    def set_detecting(self) -> bool:
        """Active la détection. Retourne False si aucun modèle disponible."""
        if not self._loaded:
            return False
        with self._lock:
            self._mode = "detecting"
        logger.info("ML IDS : détection activée")
        return True

    def stop(self):
        with self._lock:
            self._mode = "idle"
        logger.info("ML IDS : arrêté")

    # ── Alimentation par paquets ───────────────────────────────────────
    def feed(self, pkt: dict):
        feat = extract_features(pkt)
        if feat is None:
            return

        with self._lock:
            mode = self._mode
            self._total_seen += 1

        if mode == "training":
            with self._lock:
                self._train_buffer.append(feat)

        elif mode == "detecting":
            self._score_packet(pkt, feat)

    # ── Scoring temps réel ─────────────────────────────────────────────
    def _score_packet(self, pkt: dict, feat: list):
        score_sk = self._isolation_score(feat)
        score_bo = self._boria_score(feat)

        # Vote pondéré : 60% IsolationForest, 40% BorIA
        combined = score_sk * 0.6 + score_bo * 0.4
        self._scores.append(combined)

        if combined >= self.ANOMALY_THR:
            with self._lock:
                self._total_anomaly += 1
            entry = {
                "src":    pkt.get("src", "?"),
                "dst":    pkt.get("dst", "?"),
                "proto":  pkt.get("proto", "?"),
                "dport":  pkt.get("dport", "?"),
                "score":  round(combined, 3),
                "detail": f"Score anomalie : {combined:.2%} (IF:{score_sk:.2f} BorIA:{score_bo:.2f})",
                "ts":     time.time(),
            }
            with self._lock:
                self._recent.append(entry)
            self._sink("ANOMALY_DETECTED", entry)

    def _isolation_score(self, feat: list) -> float:
        if not SK_AVAILABLE or self._model is None or self._scaler is None:
            return 0.0
        try:
            arr = np.array(feat).reshape(1, -1)
            arr_scaled = self._scaler.transform(arr)
            raw = self._model.score_samples(arr_scaled)[0]
            return max(0.0, min(1.0, -raw / 0.5))
        except Exception:
            return 0.0

    def _boria_score(self, feat: list) -> float:
        try:
            from boria_bridge import BorIABridge
            return BorIABridge.get().predict_anomaly(feat)
        except Exception:
            return 0.0

    # ── Chargement modèle persisté ─────────────────────────────────────
    def _try_load_model(self):
        if not SK_AVAILABLE:
            return
        try:
            if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
                self._model  = joblib.load(MODEL_PATH)
                self._scaler = joblib.load(SCALER_PATH)
                self._loaded = True
                logger.info("ML IDS : modèle chargé depuis le disque")
        except Exception as e:
            logger.warning(f"ML IDS : impossible de charger le modèle ({e})")

    # ── Stats (attendues par ml_tab._ui_tick) ──────────────────────────
    def stats(self) -> dict:
        with self._lock:
            total_seen    = self._total_seen
            total_anomaly = self._total_anomaly
        rate = round(total_anomaly / total_seen * 100, 2) if total_seen else 0.0
        return {
            "total_seen":    total_seen,
            "total_anomaly": total_anomaly,
            "anomaly_rate":  rate,
            "model_on_disk": os.path.exists(MODEL_PATH),
        }

    # ── Anomalies récentes (attendu par ml_tab._ui_tick) ───────────────
    def recent_anomalies(self, last_n_seconds: float = 60) -> list:
        cutoff = time.time() - last_n_seconds
        with self._lock:
            return [r for r in self._recent if r.get("ts", 0) >= cutoff]
