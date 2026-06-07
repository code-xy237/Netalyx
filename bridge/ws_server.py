# bridge/ws_server.py — Serveur WebSocket async (FastAPI-free, pur asyncio)
# Reçoit les événements Python (sniffer, IDS, voix, gestes) et les broadcast au frontend 3D

import asyncio
import json
import threading
import time
import logging
from typing import Set, Callable, Optional

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False

logger = logging.getLogger("netalyx.bridge")

# ── Singleton global ──────────────────────────────────────────────────────────
_instance: Optional["WSBridge"] = None

def get_bridge() -> "WSBridge":
    global _instance
    if _instance is None:
        _instance = WSBridge()
    return _instance


class WSBridge:
    """
    Bus d'événements WebSocket bidirectionnel.
    - Côté Python : appeler broadcast(event_type, payload) depuis n'importe quel thread
    - Côté JS     : ws.send(JSON) → dispatché aux handlers Python enregistrés
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self._clients: Set[WebSocketServerProtocol] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._handlers: dict[str, list[Callable]] = {}
        self._queue: asyncio.Queue = None  # initialisé dans le loop

    # ── Démarrage ─────────────────────────────────────────────────────────────
    def start(self):
        """Lance le serveur WS dans un thread daemon séparé."""
        if not WS_AVAILABLE:
            logger.warning("websockets non installé — bridge désactivé")
            return False
        if self._running:
            return True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="WSBridge")
        self._thread.start()
        # Attendre que le loop soit prêt
        for _ in range(50):
            if self._running:
                return True
            time.sleep(0.05)
        return False

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._queue = asyncio.Queue()
        self._loop.run_until_complete(self._serve())

    async def _serve(self):
        self._running = True
        logger.info(f"WSBridge démarré sur ws://{self.host}:{self.port}")
        try:
            async with websockets.serve(self._handler, self.host, self.port,
                                        ping_interval=20, ping_timeout=10):
                await self._dispatch_loop()
        except Exception as e:
            logger.error(f"WSBridge erreur: {e}")
        finally:
            self._running = False

    # ── Gestion des clients ───────────────────────────────────────────────────
    async def _handler(self, ws: WebSocketServerProtocol, path: str = "/"):
        self._clients.add(ws)
        logger.debug(f"Client connecté ({len(self._clients)} total)")
        try:
            # Envoyer état initial
            await ws.send(json.dumps({"type": "connected", "payload": {"version": "2.0"}}))
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                    await self._dispatch_incoming(msg)
                except json.JSONDecodeError:
                    pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self._clients.discard(ws)
            logger.debug(f"Client déconnecté ({len(self._clients)} restants)")

    async def _dispatch_incoming(self, msg: dict):
        """Dispatch les messages reçus du frontend vers les handlers Python."""
        event_type = msg.get("type", "")
        payload = msg.get("payload", {})
        handlers = self._handlers.get(event_type, [])
        for fn in handlers:
            try:
                fn(payload)
            except Exception as e:
                logger.warning(f"Handler {event_type} erreur: {e}")

    # ── Loop de dispatch sortant ──────────────────────────────────────────────
    async def _dispatch_loop(self):
        """Envoie les messages mis en queue vers tous les clients."""
        while True:
            msg = await self._queue.get()
            if not self._clients:
                continue
            dead = set()
            for ws in list(self._clients):
                try:
                    await ws.send(msg)
                except Exception:
                    dead.add(ws)
            self._clients -= dead

    # ── API publique (thread-safe) ────────────────────────────────────────────
    def broadcast(self, event_type: str, payload: dict):
        """Envoie un événement à tous les clients connectés (thread-safe)."""
        if not self._running or self._loop is None:
            return
        msg = json.dumps({"type": event_type, "payload": payload, "ts": time.time()})
        asyncio.run_coroutine_threadsafe(self._queue.put(msg), self._loop)

    def on(self, event_type: str, handler: Callable):
        """Enregistre un handler pour un type d'événement entrant."""
        self._handlers.setdefault(event_type, []).append(handler)

    def emit_network_snapshot(self, snapshot: dict):
        """Raccourci : envoie un snapshot réseau complet."""
        self.broadcast("network_snapshot", snapshot)

    def emit_alert(self, alert: dict):
        """Raccourci : envoie une alerte IDS/cybersec."""
        self.broadcast("security_alert", alert)

    def emit_voice_command(self, command: str, confidence: float = 1.0):
        """Raccourci : notifie le frontend d'une commande vocale reconnue."""
        self.broadcast("voice_command", {"command": command, "confidence": confidence})

    def emit_gesture(self, gesture: str, data: dict):
        """Raccourci : envoie un geste détecté au frontend."""
        self.broadcast("gesture_event", {"gesture": gesture, **data})

    def emit_hand_landmarks(self, landmarks: list):
        """Envoie les 21 landmarks de la main pour le curseur 3D holographique."""
        self.broadcast("hand_landmarks", {"landmarks": landmarks})

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def client_count(self) -> int:
        return len(self._clients)
