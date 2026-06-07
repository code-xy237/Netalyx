# gui/graph3d_tab.py — Onglet cartographie réseau 3D (Three.js via WebView embarquée)
# Remplace graph_tab.py (2D matplotlib) par une vue 3D futuriste full-WebGL
# Fallback automatique vers ouverture navigateur si tkinterweb non installé

import tkinter as tk
import ttkbootstrap as tb
import threading
import webbrowser
import os
import logging
from pathlib import Path

logger = logging.getLogger("netalyx.graph3d")

# Détection tkinterweb (WebView Chromium dans Tkinter)
try:
    import tkinterweb
    WEBVIEW_AVAILABLE = True
except ImportError:
    WEBVIEW_AVAILABLE = False
    logger.info("tkinterweb non installé — fallback navigateur (pip install tkinterweb)")

from common import resource_path


def get_3d_html_path() -> str:
    """Retourne le chemin absolu vers la page 3D."""
    base = getattr(__import__('sys'), '_MEIPASS', os.path.abspath('.'))
    return os.path.join(base, 'static', '3d', 'netalyx3d.html')


class Graph3DTab(tb.Frame):
    """
    Onglet de cartographie réseau 3D.
    - Si tkinterweb est installé : WebView Chromium embarquée directement dans Tkinter
    - Sinon : panneau de contrôle avec bouton pour ouvrir dans le navigateur système
    """

    def __init__(self, master, net_graph=None, bridge=None, voice_engine=None, gesture_engine=None):
        super().__init__(master, padding=0)
        self.ng = net_graph
        self.bridge = bridge
        self.ve = voice_engine
        self.ge = gesture_engine
        self._webview = None
        self._html_path = get_3d_html_path()

        if WEBVIEW_AVAILABLE:
            self._build_embedded()
        else:
            self._build_fallback()

    # ── Mode WebView embarquée ─────────────────────────────────────────────────
    def _build_embedded(self):
        """Embed Chromium directement dans le Tab Tkinter via tkinterweb."""
        # Barre de contrôle minimale
        ctrl = tb.Frame(self, padding=4)
        ctrl.pack(fill="x")

        tb.Label(ctrl, text="🌐 Vue 3D réseau",
                 font=("Segoe UI", 11, "bold")).pack(side="left")

        tb.Button(ctrl, text="↺ Recharger",
                  bootstyle="secondary-outline",
                  command=self._reload).pack(side="right", padx=4)
        tb.Button(ctrl, text="⊞ Ouvrir navigateur",
                  bootstyle="info-outline",
                  command=self._open_browser).pack(side="right", padx=4)

        # Status bridge
        self._bridge_lbl = tb.Label(ctrl, text="● Bridge: inactif",
                                     font=("Segoe UI", 9), foreground="#6b7280")
        self._bridge_lbl.pack(side="right", padx=8)

        # WebView
        frame = tb.Frame(self)
        frame.pack(fill="both", expand=True)

        try:
            self._webview = tkinterweb.HtmlFrame(frame, messages_enabled=False)
            self._webview.pack(fill="both", expand=True)
            self._load_3d()
        except Exception as e:
            logger.error(f"tkinterweb erreur: {e}")
            self._build_fallback_inner(frame)

        # Démarrer le monitoring du bridge
        self._monitor_bridge()

    def _load_3d(self):
        """Charge la page HTML 3D dans le WebView."""
        if not self._webview:
            return
        url = Path(self._html_path).as_uri()
        try:
            self._webview.load_url(url)
            logger.info(f"3D chargé: {url}")
        except Exception as e:
            logger.error(f"Erreur chargement 3D: {e}")

    def _reload(self):
        if self._webview:
            self._load_3d()

    def _open_browser(self):
        url = Path(self._html_path).as_uri()
        webbrowser.open(url)

    def _monitor_bridge(self):
        """Met à jour le statut du bridge toutes les 2s."""
        if self.bridge and hasattr(self.bridge, 'is_running'):
            if self.bridge.is_running:
                clients = getattr(self.bridge, 'client_count', 0)
                self._bridge_lbl.config(
                    text=f"● Bridge: actif ({clients} clients)",
                    foreground="#4ade80"
                )
            else:
                self._bridge_lbl.config(text="● Bridge: inactif", foreground="#6b7280")
        self.after(2000, self._monitor_bridge)

    # ── Mode fallback (navigateur externe) ────────────────────────────────────
    def _build_fallback(self):
        """Interface quand tkinterweb n'est pas disponible."""
        container = tb.Frame(self, padding=30)
        container.pack(fill="both", expand=True)

        # Header
        tb.Label(container, text="🌐 Cartographie Réseau 3D",
                 font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(0, 4))
        tb.Label(container,
                 text="Vue Three.js WebGL — Rendu futuriste temps réel",
                 font=("Segoe UI", 11), bootstyle="secondary").pack(anchor="w", pady=(0, 24))

        # Statut bridge
        status_card = tb.Labelframe(container, text="Statut Bridge WebSocket", padding=16,
                                     bootstyle="success")
        status_card.pack(fill="x", pady=(0, 16))

        self._status_row = tb.Frame(status_card)
        self._status_row.pack(fill="x")
        self._status_dot = tk.Canvas(self._status_row, width=14, height=14,
                                      bg="#0e0f12", highlightthickness=0)
        self._status_dot.create_oval(1, 1, 13, 13, fill="#555", tags="dot")
        self._status_dot.pack(side="left", padx=(0, 8))
        self._status_lbl = tb.Label(self._status_row, text="Bridge inactif",
                                     font=("Segoe UI", 11))
        self._status_lbl.pack(side="left")

        tb.Label(status_card,
                 text="ws://127.0.0.1:8765 — Connexion automatique depuis la page 3D",
                 font=("Consolas", 9), bootstyle="secondary").pack(anchor="w", pady=(6, 0))

        # Boutons d'action
        btns = tb.Frame(container)
        btns.pack(fill="x", pady=(0, 16))

        tb.Button(btns, text="🚀  Ouvrir la vue 3D dans le navigateur",
                  bootstyle="success",
                  command=self._open_browser,
                  width=36).pack(side="left", ipady=8)

        tb.Button(btns, text="📋  Copier l'URL",
                  bootstyle="secondary-outline",
                  command=self._copy_url).pack(side="left", padx=12, ipady=8)

        # Info install
        install_card = tb.Labelframe(container, text="Installer la vue embarquée",
                                      bootstyle="info", padding=16)
        install_card.pack(fill="x", pady=(0, 16))

        tb.Label(install_card,
                 text="Pour intégrer la vue 3D directement dans ce dashboard :\n\n"
                      "pip install tkinterweb\n\nPuis relancer Netalyx.",
                 font=("Consolas", 10)).pack(anchor="w")

        # Fonctionnalités
        feat_card = tb.Labelframe(container, text="Fonctionnalités 3D",
                                   bootstyle="secondary", padding=16)
        feat_card.pack(fill="x")
        features = [
            "🌐  Graphe réseau 3D interactif (Three.js ForceGraph3D)",
            "✨  Post-processing WebGL : bloom, glow, scanlines",
            "🎙  Commandes vocales → actions scène 3D",
            "✋  Gestes main → curseur holographique 3D",
            "🚨  Alertes IDS temps réel avec flash visuel",
            "👆  Sélection nœud par pointage gestuel",
            "💫  Particules de flux sur les connexions réseau",
            "📡  Synchronisation temps réel via WebSocket",
        ]
        for f in features:
            tb.Label(feat_card, text=f"  {f}", font=("Segoe UI", 10)).pack(anchor="w", pady=1)

        # Monitoring
        self._monitor_bridge_fallback()

    def _build_fallback_inner(self, parent):
        """Fallback dans le frame WebView si tkinterweb échoue."""
        tb.Label(parent,
                 text="Erreur WebView — Cliquez 'Ouvrir navigateur'",
                 font=("Segoe UI", 12), foreground="#f87171").pack(expand=True)

    def _open_browser(self):
        url = Path(self._html_path).as_uri()
        webbrowser.open(url)
        logger.info(f"Ouverture navigateur: {url}")

    def _copy_url(self):
        url = Path(self._html_path).as_uri()
        self.clipboard_clear()
        self.clipboard_append(url)

    def _monitor_bridge_fallback(self):
        if self.bridge and hasattr(self.bridge, 'is_running'):
            if self.bridge.is_running:
                self._status_dot.itemconfig("dot", fill="#4ade80")
                self._status_lbl.config(text="Bridge actif — En attente de connexion 3D",
                                         foreground="#4ade80")
            else:
                self._status_dot.itemconfig("dot", fill="#555")
                self._status_lbl.config(text="Bridge inactif", foreground="#6b7280")
        self.after(2000, self._monitor_bridge_fallback)
