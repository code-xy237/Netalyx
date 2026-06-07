# bridge/event_adapter.py — Adaptateur : connecte les modules Netalyx existants au bridge WS
# Injecte les événements réseau, IDS, ML vers le frontend 3D sans modifier le code existant

import threading
import time
import json
import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from security.network_graph import NetworkGraph
    from bridge.ws_server import WSBridge

logger = logging.getLogger("netalyx.adapter")


class NetworkEventAdapter:
    """
    Écoute les changements du NetworkGraph existant et les broadcast via WSBridge.
    S'installe en overlay transparent — aucune modification des fichiers existants.
    """

    def __init__(self, net_graph, bridge, interval_ms: int = 500):
        self.ng = net_graph
        self.bridge = bridge
        self.interval = interval_ms / 1000.0
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_node_count = 0
        self._last_edge_count = 0

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="NetAdapter")
        self._thread.start()
        logger.info("NetworkEventAdapter démarré")

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            try:
                self._push_snapshot()
            except Exception as e:
                logger.warning(f"Adapter loop erreur: {e}")
            time.sleep(self.interval)

    def _push_snapshot(self):
        snap = self.ng.snapshot()
        nc = snap.get("node_count", 0)
        ec = snap.get("edge_count", 0)

        # Toujours envoyer pour le rendu 3D (le frontend gère le delta)
        nodes_3d = []
        for n in snap.get("nodes", []):
            nodes_3d.append({
                "id": n["id"],
                "color": n.get("color", "#4CAF50"),
                "status": n.get("status", "normal"),
                "volume": n.get("volume", 1),
                "label": n["id"],
                "x": None,  # position gérée par ForceGraph3D
                "y": None,
                "z": None,
            })

        links_3d = []
        for e in snap.get("edges", []):
            links_3d.append({
                "source": e["src"],
                "target": e["dst"],
                "weight": e.get("weight", 1),
                "proto": e.get("proto", "?"),
                "dport": e.get("dport", 0),
            })

        payload = {
            "nodes": nodes_3d,
            "links": links_3d,
            "node_count": nc,
            "edge_count": ec,
            "top_ips": snap.get("top_ips", []),
            "timestamp": time.time(),
        }

        self.bridge.broadcast("network_snapshot", payload)
        self._last_node_count = nc
        self._last_edge_count = ec

    def push_alert(self, alert_type: str, details: dict, severity: str = "HIGH"):
        """Appel explicite depuis l'IDS pour pousser une alerte immédiatement."""
        payload = {
            "alert_type": alert_type,
            "severity": severity,
            "details": details,
            "timestamp": time.time(),
        }
        self.bridge.emit_alert(payload)
        logger.info(f"Alert pushée: {alert_type} ({severity})")

    def push_ml_event(self, event: dict):
        """Pousse un événement ML-IDS vers le frontend."""
        self.bridge.broadcast("ml_event", {**event, "timestamp": time.time()})


class CommandDispatcher:
    """
    Reçoit les commandes vocales (str) et les mappe vers les fonctions Netalyx existantes.
    Fuzzy matching pour tolérer les variations de formulation.
    """

    COMMAND_MAP = {
        # Commandes réseau
        "zoom": ["zoom", "zoomer", "agrandir"],
        "reset": ["reset", "réinitialiser", "effacer", "vider", "clear"],
        "rotate": ["tourner", "rotation", "rotate", "pivoter"],
        "stop": ["stop", "arrêter", "pause", "stopper"],
        "refresh": ["rafraîchir", "actualiser", "refresh", "mettre à jour"],
        # Commandes sécurité
        "block_ip": ["bloquer", "block", "ban", "bannir"],
        "suspect_ip": ["suspect", "marquer suspect", "signaler"],
        "show_alerts": ["alertes", "alerts", "voir les alertes", "afficher alertes"],
        # Navigation
        "focus_node": ["sélectionner", "select", "focus", "cibler"],
        "show_stats": ["statistiques", "stats", "données", "infos"],
        "fullscreen": ["plein écran", "fullscreen", "agrandir vue"],
    }

    def __init__(self, net_graph=None, bridge=None):
        self.ng = net_graph
        self.bridge = bridge
        self._callbacks: dict = {}

    def register(self, command: str, callback):
        """Enregistre un callback Python pour une commande vocale."""
        self._callbacks[command] = callback

    def dispatch(self, raw_text: str) -> Optional[str]:
        """
        Analyse le texte brut et dispatch la commande correspondante.
        Retourne le nom de la commande trouvée ou None.
        """
        text = raw_text.lower().strip()

        for cmd, keywords in self.COMMAND_MAP.items():
            if any(kw in text for kw in keywords):
                # Notifier le frontend
                if self.bridge:
                    self.bridge.emit_voice_command(cmd, confidence=0.9)

                # Exécuter le callback Python si enregistré
                if cmd in self._callbacks:
                    try:
                        self._callbacks[cmd](text)
                    except Exception as e:
                        logger.warning(f"Callback {cmd} erreur: {e}")

                # Actions directes sur le graph
                if self.ng:
                    self._exec_graph_action(cmd, text)

                logger.info(f"Commande vocale: '{raw_text}' → {cmd}")
                return cmd

        logger.debug(f"Commande non reconnue: '{raw_text}'")
        return None

    def _exec_graph_action(self, cmd: str, text: str):
        try:
            if cmd == "reset":
                self.ng.reset()
            elif cmd == "suspect_ip":
                # Extraire l'IP du texte si présente
                import re
                ips = re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", text)
                if ips:
                    self.ng.mark_suspect(ips[0])
            elif cmd == "block_ip":
                import re
                ips = re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", text)
                if ips:
                    self.ng.mark_blocked(ips[0])
        except Exception as e:
            logger.warning(f"Graph action {cmd} erreur: {e}")
