# gui/dashboard_v3.py — Dashboard Netalyx v3.0 avec voix, gestes et 3D
# Extension du Dashboard existant — ajoute les nouveaux onglets sans casser l'existant

import tkinter as tk
import ttkbootstrap as tb
from queue import Queue
import time
import logging
from collections import deque

logger = logging.getLogger("netalyx.dashboard")


def patch_dashboard(dashboard_class):
    """
    Patch non-destructif du Dashboard existant.
    Ajoute : onglet 3D, panneau voix, panneau geste, orchestrateur core.
    
    Usage dans dashboard.py :
        from gui.dashboard_v3 import patch_dashboard
        Dashboard = patch_dashboard(Dashboard)
    """
    original_init = dashboard_class.__init__

    def new_init(self, master, username: str):
        # Init originale d'abord
        original_init(self, master, username)

        # Récupérer le net_graph créé par l'init originale
        net_graph = getattr(self, 'net_graph', None)

        # ── Démarrer l'orchestrateur core ────────────────────────────────────
        from netalyx_core import NetalyxCore
        self.core = NetalyxCore(
            net_graph=net_graph,
            auto_voice=False,   # L'utilisateur active manuellement
            auto_gesture=False
        )
        try:
            self.core.start()
        except Exception as e:
            logger.error(f"Core start error: {e}")

        # ── Ajouter l'onglet 3D ───────────────────────────────────────────────
        try:
            from gui.graph3d_tab import Graph3DTab
            self.graph3d_tab = Graph3DTab(
                self.nb,
                net_graph=net_graph,
                bridge=self.core.bridge,
                voice_engine=self.core.voice,
                gesture_engine=self.core.gesture
            )
            self.nb.add(self.graph3d_tab, text="🌐  3D Réseau")
        except Exception as e:
            logger.error(f"Graph3DTab erreur: {e}")

        # ── Ajouter l'onglet Interaction (voix + gestes) ──────────────────────
        try:
            interaction_tab = tb.Frame(self.nb, padding=12)
            self.nb.add(interaction_tab, text="🎙  Interaction")
            self._build_interaction_tab(interaction_tab)
        except Exception as e:
            logger.error(f"Interaction tab erreur: {e}")

        # ── Patcher le callback IDS pour notifier le frontend 3D ─────────────
        self._patch_ids_alerts()

        logger.info("Dashboard v3 patché avec succès")

    def _build_interaction_tab(self, parent):
        """Construit l'onglet voix + gestes combiné."""
        cols = tb.Frame(parent)
        cols.pack(fill="both", expand=True)

        # Colonne gauche: Voix
        left = tb.Frame(cols)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        try:
            from gui.voice_panel import VoicePanel
            vp = VoicePanel(left, voice_engine=self.core.voice)
            vp.pack(fill="both", expand=True)
        except Exception as e:
            tb.Label(left, text=f"Panel voix: {e}", foreground="red").pack()

        # Colonne droite: Gestes
        right = tb.Frame(cols)
        right.pack(side="right", fill="both", expand=True)

        try:
            from gui.gesture_panel import GesturePanel
            gp = GesturePanel(right, gesture_engine=self.core.gesture)
            gp.pack(fill="both", expand=True)
        except Exception as e:
            tb.Label(right, text=f"Panel geste: {e}", foreground="red").pack()

        # Statut core en bas
        status_frame = tb.Labelframe(parent, text="Statut Système",
                                      bootstyle="secondary", padding=10)
        status_frame.pack(fill="x", pady=(8, 0))
        self._status_lbl = tb.Label(status_frame, text="Chargement...",
                                     font=("Consolas", 9))
        self._status_lbl.pack(anchor="w")
        self._update_core_status()

    def _update_core_status(self):
        """Met à jour le statut système toutes les 3s."""
        try:
            if hasattr(self, 'core'):
                s = self.core.status_report()
                ws_icon = "🟢" if s['bridge_running'] else "🔴"
                v_icon  = "🟢" if s['voice_running'] else ("🟡" if s['voice_available'] else "🔴")
                g_icon  = "🟢" if s['gesture_running'] else ("🟡" if s['gesture_available'] else "🔴")
                self._status_lbl.config(
                    text=f"{ws_icon} WS: {'actif' if s['bridge_running'] else 'inactif'} "
                         f"({s['ws_clients']} clients)  "
                         f"{v_icon} Voix  "
                         f"{g_icon} Gestes"
                )
        except: pass
        self.after(3000, self._update_core_status)

    def _patch_ids_alerts(self):
        """Intercepte les alertes IDS pour les pousser aussi au frontend 3D."""
        original_on_alert = getattr(self, '_on_ids_alert', None)

        def patched_alert(alert_dict):
            # Appel original
            if original_on_alert:
                original_on_alert(alert_dict)
            # Notification 3D
            if hasattr(self, 'core'):
                self.core.push_ids_alert(
                    alert_type=alert_dict.get('type', 'ALERTE'),
                    details=alert_dict,
                    severity=alert_dict.get('severity', 'HIGH')
                )
                # Annonce vocale pour alertes critiques
                if alert_dict.get('severity') == 'CRITICAL':
                    ip = alert_dict.get('ip', '')
                    self.core.announce(f"Alerte critique. I.P. {ip} détectée.", priority=True)

        if original_on_alert:
            self._on_ids_alert = patched_alert

    # Injecter les nouvelles méthodes
    dashboard_class.__init__ = new_init
    dashboard_class._build_interaction_tab = _build_interaction_tab
    dashboard_class._update_core_status = _update_core_status
    dashboard_class._patch_ids_alerts = _patch_ids_alerts
    return dashboard_class
