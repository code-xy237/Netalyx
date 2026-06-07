# gui/web_tab.py — Onglet contrôle du serveur web Flask
import tkinter as tk
import ttkbootstrap as tb
import threading
import socket
import webbrowser
from web.server import start_server, is_running


def get_local_ip() -> str:
    """Récupère l'IP locale de la machine sur le réseau."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


class WebTab(tb.Frame):
    """Onglet de contrôle du serveur web embarqué."""

    def __init__(self, master):
        super().__init__(master, padding=20)
        self._port = tk.IntVar(value=5000)
        self._host = tk.StringVar(value="0.0.0.0")
        self._build_ui()

    def _build_ui(self):
        # Titre
        tb.Label(self, text="Interface Web embarquée",
                 font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 4))
        tb.Label(self,
                 text="Accède au dashboard depuis n'importe quel appareil du réseau local.",
                 font=("Segoe UI", 10), bootstyle="secondary").pack(anchor="w", pady=(0, 20))

        # Config
        cfg = tb.Labelframe(self, text="Configuration", bootstyle="primary", padding=16)
        cfg.pack(fill="x", pady=(0, 16))

        row1 = tb.Frame(cfg)
        row1.pack(fill="x", pady=(0, 8))
        tb.Label(row1, text="Port :", width=10).pack(side="left")
        tb.Entry(row1, textvariable=self._port, width=8).pack(side="left", padx=8)
        tb.Label(row1, text="(défaut : 5000)", bootstyle="secondary",
                 font=("Segoe UI", 9)).pack(side="left")

        row2 = tb.Frame(cfg)
        row2.pack(fill="x")
        tb.Label(row2, text="Écoute :", width=10).pack(side="left")
        tb.Radiobutton(row2, text="Réseau local (0.0.0.0)",
                       variable=self._host, value="0.0.0.0",
                       bootstyle="success").pack(side="left", padx=8)
        tb.Radiobutton(row2, text="Localhost uniquement",
                       variable=self._host, value="127.0.0.1",
                       bootstyle="secondary").pack(side="left")

        # Boutons
        btn_row = tb.Frame(self)
        btn_row.pack(fill="x", pady=(0, 16))

        self._btn_start = tb.Button(btn_row, text="🌐  Démarrer le serveur web",
                                     bootstyle="success", command=self._start,
                                     width=28)
        self._btn_start.pack(side="left", ipady=6)

        self._btn_open = tb.Button(btn_row, text="↗  Ouvrir dans le navigateur",
                                    bootstyle="info-outline", command=self._open_browser,
                                    state="disabled", width=26)
        self._btn_open.pack(side="left", padx=12, ipady=6)

        # Status
        status_card = tb.Labelframe(self, text="Statut", bootstyle="secondary", padding=16)
        status_card.pack(fill="x", pady=(0, 16))

        self._lbl_status = tb.Label(status_card,
                                     text="⏸  Serveur arrêté",
                                     font=("Segoe UI", 13, "bold"),
                                     bootstyle="secondary")
        self._lbl_status.pack(anchor="w")

        self._lbl_url = tb.Label(status_card, text="",
                                  font=("Consolas", 12), bootstyle="info")
        self._lbl_url.pack(anchor="w", pady=(6, 0))

        self._lbl_ip = tb.Label(status_card,
                                 text=f"IP locale de cette machine : {get_local_ip()}",
                                 font=("Segoe UI", 10), bootstyle="secondary")
        self._lbl_ip.pack(anchor="w", pady=(4, 0))

        # Infos
        info = tb.Labelframe(self, text="Fonctionnalités du dashboard web",
                              bootstyle="info", padding=16)
        info.pack(fill="x")

        features = [
            "📡  Trafic réseau en temps réel (WebSocket)",
            "🚨  Alertes IDS avec badge de criticité",
            "🧬  Statistiques ML IDS (mode, taux d'anomalie)",
            "🕸  Cartographie réseau (graphe canvas interactif)",
            "💻  Appareils détectés sur le réseau",
            "📈  Graphique Paquets/seconde (Chart.js)",
            "🔔  Flash visuel sur alerte critique",
            "📱  Interface responsive (mobile, tablette, PC)",
        ]
        for f in features:
            tb.Label(info, text=f"  {f}",
                     font=("Segoe UI", 10)).pack(anchor="w", pady=1)

    def _start(self):
        if is_running():
            self._lbl_status.config(text="⚠  Le serveur est déjà en cours d'exécution.",
                                     bootstyle="warning")
            return
        port = self._port.get()
        host = self._host.get()
        ok   = start_server(host=host, port=port)
        if ok:
            ip  = get_local_ip()
            url = f"http://{ip}:{port}"
            self._lbl_status.config(text="✓  Serveur web actif", bootstyle="success")
            self._lbl_url.config(text=url)
            self._btn_start.config(state="disabled")
            self._btn_open.config(state="normal")
        else:
            self._lbl_status.config(text="✗  Erreur de démarrage", bootstyle="danger")

    def _open_browser(self):
        ip   = get_local_ip()
        port = self._port.get()
        webbrowser.open(f"http://{ip}:{port}")
