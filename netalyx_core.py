# netalyx_core.py — Orchestrateur central Netalyx
# Initialise et connecte tous les modules : bridge WS, voice, geste, adaptateur réseau
# S'intègre dans le Dashboard existant sans casser le code actuel

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger("netalyx.core")


class NetalyxCore:
    """
    Orchestrateur qui instancie et connecte :
    - WSBridge (serveur WebSocket)
    - NetworkEventAdapter (sync réseau → frontend 3D)
    - CommandDispatcher (voix/gestes → actions Netalyx)
    - VoiceEngine (reconnaissance vocale + TTS)
    - GestureEngine (MediaPipe + OpenCV)

    Usage minimal :
        core = NetalyxCore(net_graph=self.net_graph)
        core.start()
    """

    def __init__(self,
                 net_graph=None,
                 ws_host: str = "127.0.0.1",
                 ws_port: int = 8765,
                 auto_voice: bool = False,
                 auto_gesture: bool = False):
        self.ng = net_graph
        self.ws_host = ws_host
        self.ws_port = ws_port
        self.auto_voice = auto_voice
        self.auto_gesture = auto_gesture

        # Modules (initialisés dans start())
        self.bridge = None
        self.adapter = None
        self.dispatcher = None
        self.voice = None
        self.gesture = None

        self._started = False

    def start(self) -> bool:
        """Démarre tous les modules dans le bon ordre."""
        if self._started:
            return True
        logger.info("NetalyxCore: démarrage...")

        # ── 1. Bridge WebSocket ──────────────────────────────────────────────
        try:
            from bridge.ws_server import WSBridge
            self.bridge = WSBridge(host=self.ws_host, port=self.ws_port)
            ok = self.bridge.start()
            if ok:
                logger.info(f"Bridge WS démarré sur ws://{self.ws_host}:{self.ws_port}")
            else:
                logger.warning("Bridge WS non démarré (websockets manquant ?)")
        except Exception as e:
            logger.error(f"Bridge erreur: {e}")

        # ── 2. Command Dispatcher ────────────────────────────────────────────
        try:
            from bridge.event_adapter import CommandDispatcher
            self.dispatcher = CommandDispatcher(net_graph=self.ng, bridge=self.bridge)
            self._register_default_callbacks()
        except Exception as e:
            logger.error(f"Dispatcher erreur: {e}")

        # ── 3. Network Adapter (pousse snapshots réseau → frontend 3D) ──────
        if self.ng:
            try:
                from bridge.event_adapter import NetworkEventAdapter
                self.adapter = NetworkEventAdapter(
                    net_graph=self.ng,
                    bridge=self.bridge,
                    interval_ms=500
                )
                self.adapter.start()
                logger.info("NetworkEventAdapter démarré")
            except Exception as e:
                logger.error(f"Adapter erreur: {e}")

        # ── 4. Voice Engine ──────────────────────────────────────────────────
        try:
            from voice.engine import create_voice_engine
            self.voice = create_voice_engine(
                dispatcher=self.dispatcher,
                bridge=self.bridge
            )
            if self.auto_voice:
                self.voice.start()
                logger.info("VoiceEngine démarré automatiquement")
        except Exception as e:
            logger.warning(f"VoiceEngine non disponible: {e}")

        # ── 5. Gesture Engine ────────────────────────────────────────────────
        try:
            from gesture.engine import create_gesture_engine
            self.gesture = create_gesture_engine(
                bridge=self.bridge,
                dispatcher=self.dispatcher
            )
            if self.auto_gesture:
                self.gesture.start()
                logger.info("GestureEngine démarré automatiquement")
        except Exception as e:
            logger.warning(f"GestureEngine non disponible: {e}")

        # ── 6. Enregistrer les handlers de commandes entrantes (frontend → Python) ──
        if self.bridge:
            self.bridge.on("mark_suspect", self._on_mark_suspect)
            self.bridge.on("block_ip", self._on_block_ip)
            self.bridge.on("clear_graph", self._on_clear_graph)
            self.bridge.on("toggle_voice", self._on_toggle_voice)
            self.bridge.on("request_refresh", self._on_request_refresh)

        self._started = True
        logger.info("NetalyxCore: tous les modules démarrés")
        return True

    def stop(self):
        """Arrête proprement tous les modules."""
        if self.voice:
            try: self.voice.stop()
            except: pass
        if self.gesture:
            try: self.gesture.stop()
            except: pass
        if self.adapter:
            try: self.adapter.stop()
            except: pass
        logger.info("NetalyxCore: arrêté")

    # ── Callbacks entrants (frontend → Python) ────────────────────────────────
    def _on_mark_suspect(self, payload: dict):
        ip = payload.get("ip")
        if ip and self.ng:
            try:
                self.ng.mark_suspect(ip)
                logger.info(f"Marqué suspect via 3D: {ip}")
            except: pass

    def _on_block_ip(self, payload: dict):
        ip = payload.get("ip")
        if ip and self.ng:
            try:
                self.ng.mark_blocked(ip)
                logger.info(f"Bloqué via 3D: {ip}")
            except: pass

    def _on_clear_graph(self, payload: dict):
        if self.ng:
            try:
                self.ng.reset()
                logger.info("Graphe vidé via commande 3D")
            except: pass

    def _on_toggle_voice(self, payload: dict):
        if self.voice:
            if payload.get("active", False):
                self.voice.start()
            else:
                self.voice.stop()

    def _on_request_refresh(self, payload: dict):
        """Force un snapshot immédiat."""
        if self.adapter:
            threading.Thread(target=self.adapter._push_snapshot, daemon=True).start()

    # ── Callbacks par défaut du dispatcher ───────────────────────────────────
    def _register_default_callbacks(self):
        if not self.dispatcher:
            return
        self.dispatcher.register("show_alerts",
            lambda txt: self.bridge.broadcast("focus_alerts", {}) if self.bridge else None)
        self.dispatcher.register("fullscreen",
            lambda txt: self.bridge.broadcast("toggle_fullscreen", {}) if self.bridge else None)

    # ── Méthodes utilitaires publiques ────────────────────────────────────────
    def push_ids_alert(self, alert_type: str, details: dict, severity: str = "HIGH"):
        """Appelé par l'IDS pour notifier le frontend 3D d'une alerte."""
        if self.adapter:
            self.adapter.push_alert(alert_type, details, severity)

    def push_ml_event(self, event: dict):
        """Appelé par le ML IDS pour notifier le frontend."""
        if self.adapter:
            self.adapter.push_ml_event(event)

    def announce(self, text: str, priority: bool = False):
        """Synthèse vocale d'un message Netalyx."""
        if self.voice:
            self.voice.speak(text, priority=priority)

    @property
    def is_ready(self) -> bool:
        return self._started and (self.bridge is not None)

    @property
    def ws_url(self) -> str:
        return f"ws://{self.ws_host}:{self.ws_port}"

    def status_report(self) -> dict:
        return {
            "bridge_running": self.bridge.is_running if self.bridge else False,
            "voice_available": getattr(self.voice, 'available', False),
            "voice_running": getattr(self.voice, 'is_running', False),
            "gesture_available": getattr(self.gesture, 'available', False),
            "gesture_running": getattr(self.gesture, 'is_running', False),
            "ws_clients": getattr(self.bridge, 'client_count', 0),
            "adapter_running": self.adapter is not None,
        }
