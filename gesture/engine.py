# gesture/engine.py — Moteur de détection gestuelle MediaPipe + OpenCV
# Détecte les gestes de la main et les envoie au bridge WebSocket
# Mapping: pinch → zoom, swipe → rotation, pointage → sélection nœud

import threading
import time
import math
import logging
from typing import Optional, List, Tuple, Callable

logger = logging.getLogger("netalyx.gesture")

# ── Détection des dépendances ─────────────────────────────────────────────────
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV non installé (pip install opencv-python)")

try:
    import mediapipe as mp
    MP_AVAILABLE = True
except ImportError:
    MP_AVAILABLE = False
    logger.warning("MediaPipe non installé (pip install mediapipe)")


class GestureEngine:
    """
    Moteur de détection gestuelle temps réel.
    - Capture webcam via OpenCV
    - Détection main/doigts via MediaPipe Hands
    - Classification des gestes
    - Envoi des landmarks 3D au frontend pour curseur holographique
    """

    # Seuils de détection
    PINCH_THRESHOLD    = 0.06   # distance normalisée pouce-index pour pinch
    SWIPE_MIN_SPEED    = 0.4    # vitesse min pour swipe (unités norm/s)
    POINT_THRESHOLD    = 0.12   # index tendu, autres repliés

    # Délai entre gestes pour éviter les répétitions
    GESTURE_COOLDOWN   = 0.4    # secondes

    def __init__(self, bridge=None, dispatcher=None, camera_index: int = 0):
        self.bridge = bridge
        self.dispatcher = dispatcher
        self.camera_index = camera_index
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cap = None
        self._hands = None
        self._last_gesture_time = 0
        self._last_gesture = None
        self._prev_wrist_pos = None
        self._prev_time = 0
        self._on_gesture: Optional[Callable] = None
        self._landmark_history: List = []
        self._preview_window = False   # afficher fenêtre OpenCV de debug

    # ── Démarrage ─────────────────────────────────────────────────────────────
    def start(self, preview: bool = False):
        if not CV2_AVAILABLE or not MP_AVAILABLE:
            logger.warning("OpenCV ou MediaPipe non disponible")
            return False
        self._preview_window = preview
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="GestureEngine")
        self._thread.start()
        logger.info("GestureEngine démarré")
        if self.bridge:
            self.bridge.broadcast("gesture_status", {"active": True})
        return True

    def stop(self):
        self._running = False
        if self._cap:
            self._cap.release()
        if self._preview_window:
            cv2.destroyAllWindows()
        logger.info("GestureEngine arrêté")
        if self.bridge:
            self.bridge.broadcast("gesture_status", {"active": False})

    # ── Boucle principale ─────────────────────────────────────────────────────
    def _loop(self):
        if not self._init_camera():
            return

        mp_hands = mp.solutions.hands
        with mp_hands.Hands(
            model_complexity=0,       # 0=lite, 1=full — lite = plus rapide
            min_detection_confidence=0.7,
            min_tracking_confidence=0.6,
            max_num_hands=1
        ) as hands:
            self._hands = hands
            logger.info(f"MediaPipe Hands initialisé (camera {self.camera_index})")

            while self._running:
                ret, frame = self._cap.read()
                if not ret:
                    time.sleep(0.01)
                    continue

                # Miroir + conversion BGR→RGB
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                rgb.flags.writeable = False

                results = hands.process(rgb)

                rgb.flags.writeable = True
                frame = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

                if results.multi_hand_landmarks:
                    landmarks = results.multi_hand_landmarks[0].landmark
                    lm_list = [(lm.x, lm.y, lm.z) for lm in landmarks]

                    # Envoyer landmarks au frontend (curseur holographique)
                    self._push_landmarks(lm_list)

                    # Classifier le geste
                    gesture, data = self._classify_gesture(lm_list)
                    if gesture:
                        self._emit_gesture(gesture, data)

                    # Dessin debug
                    if self._preview_window:
                        mp_draw = mp.solutions.drawing_utils
                        mp_draw.draw_landmarks(
                            frame, results.multi_hand_landmarks[0],
                            mp.solutions.hands.HAND_CONNECTIONS
                        )
                else:
                    # Aucune main détectée
                    if self.bridge:
                        self.bridge.broadcast("hand_landmarks", {"landmarks": []})

                if self._preview_window:
                    cv2.imshow("Netalyx Gesture (debug)", frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

                time.sleep(0.033)   # ~30 FPS

        if self._cap:
            self._cap.release()

    def _init_camera(self) -> bool:
        try:
            self._cap = cv2.VideoCapture(self.camera_index)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self._cap.set(cv2.CAP_PROP_FPS, 30)
            if not self._cap.isOpened():
                logger.warning(f"Camera {self.camera_index} non disponible")
                return False
            logger.info(f"Camera {self.camera_index} ouverte")
            return True
        except Exception as e:
            logger.error(f"Erreur init camera: {e}")
            return False

    # ── Classification des gestes ─────────────────────────────────────────────
    def _classify_gesture(self, lm: List[Tuple]) -> Tuple[Optional[str], dict]:
        """
        Analyse les 21 landmarks et retourne (gesture_name, data_dict) ou (None, {}).
        Landmarks MediaPipe: 0=poignet, 4=pouce, 8=index, 12=majeur, 16=annulaire, 20=auriculaire
        """
        now = time.time()
        if now - self._last_gesture_time < self.GESTURE_COOLDOWN:
            return None, {}

        # Distances clés
        d_thumb_index = self._dist(lm[4], lm[8])   # pinch
        d_thumb_middle = self._dist(lm[4], lm[12])

        # ── PINCH (pouce + index proches) ─────────────────────────────────────
        if d_thumb_index < self.PINCH_THRESHOLD:
            strength = 1.0 - (d_thumb_index / self.PINCH_THRESHOLD)
            return self._record("pinch", {
                "strength": round(strength, 3),
                "x": lm[8][0],
                "y": lm[8][1],
                "zoom_factor": 1.0 + strength * 2.0
            })

        # ── POINTAGE (index tendu, autres repliés) ────────────────────────────
        fingers_up = self._count_fingers_up(lm)
        if fingers_up == [False, True, False, False, False]:  # index seul
            return self._record("point", {
                "x": lm[8][0],
                "y": lm[8][1],
                "z": lm[8][2],
                "tip": [lm[8][0], lm[8][1], lm[8][2]]
            })

        # ── OPEN HAND (5 doigts) → reset vue ─────────────────────────────────
        if fingers_up == [True, True, True, True, True]:
            return self._record("open_hand", {"action": "reset_view"})

        # ── SWIPE (mouvement rapide du poignet) ───────────────────────────────
        wrist = lm[0]
        if self._prev_wrist_pos and self._prev_time:
            dt = now - self._prev_time
            if dt > 0:
                dx = (wrist[0] - self._prev_wrist_pos[0]) / dt
                dy = (wrist[1] - self._prev_wrist_pos[1]) / dt
                speed = math.sqrt(dx**2 + dy**2)
                if speed > self.SWIPE_MIN_SPEED:
                    direction = self._swipe_direction(dx, dy)
                    self._prev_wrist_pos = wrist
                    self._prev_time = now
                    return self._record(f"swipe_{direction}", {
                        "direction": direction,
                        "speed": round(speed, 3),
                        "dx": round(dx, 3),
                        "dy": round(dy, 3),
                    })

        self._prev_wrist_pos = wrist
        self._prev_time = now
        return None, {}

    def _record(self, gesture: str, data: dict) -> Tuple[str, dict]:
        """Enregistre le geste et reset le cooldown."""
        self._last_gesture = gesture
        self._last_gesture_time = time.time()
        return gesture, data

    # ── Utilitaires géométriques ──────────────────────────────────────────────
    @staticmethod
    def _dist(a: Tuple, b: Tuple) -> float:
        return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

    @staticmethod
    def _count_fingers_up(lm: List[Tuple]) -> List[bool]:
        """
        Retourne [pouce, index, majeur, annulaire, auriculaire] True si tendu.
        Utilise les positions relatives des articulations.
        """
        fingers = []
        # Pouce (comparaison horizontale)
        fingers.append(lm[4][0] > lm[3][0])
        # Autres doigts (tip > PIP → tendu)
        for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            fingers.append(lm[tip][1] < lm[pip][1])
        return fingers

    @staticmethod
    def _swipe_direction(dx: float, dy: float) -> str:
        if abs(dx) > abs(dy):
            return "right" if dx > 0 else "left"
        return "up" if dy < 0 else "down"

    # ── Émission des événements ───────────────────────────────────────────────
    def _push_landmarks(self, lm_list: List[Tuple]):
        """Envoie les 21 landmarks au frontend pour le curseur holographique."""
        if self.bridge:
            # Formatter pour Three.js (x, y, z normalisés 0-1)
            formatted = [{"x": x, "y": y, "z": z} for x, y, z in lm_list]
            self.bridge.emit_hand_landmarks(formatted)

    def _emit_gesture(self, gesture: str, data: dict):
        """Envoie le geste détecté au bridge et dispatch Python."""
        logger.debug(f"Geste: {gesture} — {data}")

        if self.bridge:
            self.bridge.emit_gesture(gesture, data)

        if self._on_gesture:
            self._on_gesture(gesture, data)

        # Dispatch vers commandes Python si dispatcher disponible
        if self.dispatcher:
            gesture_cmd_map = {
                "pinch":       "zoom",
                "open_hand":   "reset",
                "swipe_left":  "rotate",
                "swipe_right": "rotate",
                "swipe_up":    "refresh",
            }
            cmd = gesture_cmd_map.get(gesture)
            if cmd:
                self.dispatcher.dispatch(cmd)

    def set_on_gesture(self, callback: Callable):
        """Callback appelé à chaque geste détecté (pour l'UI)."""
        self._on_gesture = callback

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def available(self) -> bool:
        return CV2_AVAILABLE and MP_AVAILABLE


class GestureEngineStub:
    """Stub pour environnements sans webcam."""
    def start(self, preview=False): return False
    def stop(self): pass
    def set_on_gesture(self, cb): pass
    is_running = False
    available = False


def create_gesture_engine(bridge=None, dispatcher=None, camera_index=0) -> GestureEngine:
    engine = GestureEngine(bridge=bridge, dispatcher=dispatcher, camera_index=camera_index)
    if not engine.available:
        logger.warning("MediaPipe/OpenCV non dispo → mode stub")
        return GestureEngineStub()
    return engine
