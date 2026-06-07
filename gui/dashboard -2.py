import tkinter as tk
import ttkbootstrap as tb
from queue import Queue
import json
import time
from sniffer.capture import SnifferService
from sniffer.analyzer import RecentPackets
from ids.detector import IDSService
from network.monitor import NetworkMonitor
from gui.components import Carousel, LogList
from common import resource_path

# --- Graphique en temps réel ---
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque

with open(resource_path("config.json"), "r", encoding="utf-8") as f:
    CFG = json.load(f)

class Dashboard(tb.Frame):
    """
    Tableau de bord principal DexTrack.
    Interface professionnelle avec KPI, logs et graphique en temps réel.
    """
    def __init__(self, master, username: str):
        super().__init__(master, padding=12, style="secondary.TFrame")
        self.username = username

        # ===== HEADER ========================================================
        header = tb.Frame(self, style="dark.TFrame")
        header.pack(fill="x", pady=(0, 8))
        tb.Label(header,
                 text=f"Bienvenue, {username}",
                 font=("Segoe UI", 20, "bold"),
                 bootstyle="inverse-primary").pack(side="left")
        tb.Label(header,
                 text="DexTrack",
                 font=("Segoe UI", 14),
                 bootstyle="secondary").pack(side="right")

        # ===== BARRE D'ACTIONS ===============================================
        actions = tb.Frame(self)
        actions.pack(fill="x", pady=(0, 10))
        self.btn_sniff = tb.Button(actions, text="Démarrer Sniffer",
                                   bootstyle="success-outline",
                                   command=self.toggle_sniffer)
        self.btn_sniff.pack(side="left", padx=5)
        self.btn_ids = tb.Button(actions, text="Activer IDS",
                                 bootstyle="info-outline",
                                 command=self.toggle_ids,
                                 state="disabled")
        self.btn_ids.pack(side="left", padx=5)
        self.btn_mon = tb.Button(actions, text="Surveiller Réseau (ARP)",
                                 bootstyle="warning-outline",
                                 command=self.toggle_monitor)
        self.btn_mon.pack(side="left", padx=5)

        # ===== KPI / CAROUSEL ===============================================
        self.kpis = [("Paquets/min", "0"),
                     ("Alertes IDS", "0"),
                     ("Nouveaux appareils", "0")]
        self.carousel = Carousel(self, self.kpis)
        self.carousel.pack(fill="x", pady=6)

        # ===== COLONNES PRINCIPALES ==========================================
        body = tb.Frame(self)
        body.pack(fill="both", expand=True)

        # ---- Gauche : Logs + Graph ----
        left = tb.Frame(body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.log_packets = LogList(left,
                                   title="Trafic Réseau (récent)",
                                   height=16)
        self.log_packets.pack(fill="both", expand=True, pady=(0, 8))

        # Graphique temps réel
        graph_frame = tb.Labelframe(left,
                                    text="Paquets / minute",
                                    bootstyle="primary")
        graph_frame.pack(fill="both", expand=False)
        self.fig = Figure(figsize=(5, 2.5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#1e1e1e")
        self.ax.tick_params(colors="white")
        self.ax.set_ylabel("Paquets/min", color="white")
        self.ax.set_xlabel("Temps (s)", color="white")
        self.line, = self.ax.plot([], [], color="#4CAF50", lw=2)
        self.data_x = deque(maxlen=60)
        self.data_y = deque(maxlen=60)
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # ---- Droite : Alertes & Appareils ----
        right = tb.Frame(body, width=360)
        right.pack(side="right", fill="y")

        self.log_alerts = LogList(right, title="Alertes IDS", height=10)
        self.log_alerts.pack(fill="both", expand=False, pady=(0, 8))
        self.log_devices = LogList(right, title="Nouveaux Appareils", height=10)
        self.log_devices.pack(fill="both", expand=True)

        # ===== SERVICES ======================================================
        self.gui_queue = Queue()
        self.ids_queue = Queue()
        self.sniffer = SnifferService(self.gui_queue, self.ids_queue)
        self.recent = RecentPackets()
        self.ids = IDSService(self.ids_queue, alert_sink=self._on_alert)
        self.monitor = NetworkMonitor(
            CFG["ip_range"],
            CFG["port_scan_list"],
            on_new_device=self._on_new_device
        )

        self.running_sniffer = False
        self.running_ids = False
        self.running_monitor = False

        self._packets_last_count = 0
        self.start_time = time.time()
        self.after(500, self._ui_tick)

    # ===== CALLBACKS ========================================================
    def _on_alert(self, kind: str, detail: dict):
        self.log_alerts.append(f"[{kind}] {detail}")

    def _on_new_device(self, ip: str, mac: str, open_ports: list, hostname: str):
        self.log_devices.append(
            f"Nouvel appareil: {hostname} | IP={ip} | MAC={mac} | Ports={open_ports}"
        )
        count = int(self.kpis[2][1]) + 1
        self.kpis[2] = ("Nouveaux appareils", str(count))

    # ===== COMMANDES BOUTONS ===============================================
    def toggle_sniffer(self):
        if not self.running_sniffer:
            self.sniffer.start()
            self.running_sniffer = True
            self.btn_sniff.config(text="Arrêter Sniffer", bootstyle="danger-outline")
            self.btn_ids.config(state="normal")
        else:
            self.sniffer.stop()
            self.running_sniffer = False
            self.btn_sniff.config(text="Démarrer Sniffer", bootstyle="success-outline")

    def toggle_ids(self):
        if not self.running_ids:
            self.ids.start()
            self.running_ids = True
            self.btn_ids.config(text="Désactiver IDS", bootstyle="secondary-outline")
        else:
            self.ids.stop()
            self.running_ids = False
            self.btn_ids.config(text="Activer IDS", bootstyle="info-outline")

    def toggle_monitor(self):
        if not self.running_monitor:
            self.monitor.start()
            self.running_monitor = True
            self.btn_mon.config(text="Arrêter Surveillance", bootstyle="danger-outline")
        else:
            self.monitor.stop()
            self.running_monitor = False
            self.btn_mon.config(text="Surveiller Réseau (ARP)", bootstyle="warning-outline")

    # ===== RAFRAÎCHISSEMENT UI ==============================================
    def _ui_tick(self):
        self.ids.poll()

        drained = 0
        while not self.gui_queue.empty() and drained < 40:
            rec = self.gui_queue.get_nowait()
            drained += 1
            self.recent.push(rec)
            proto = rec.get('proto')
            sport = rec.get('sport')
            dport = rec.get('dport')
            src = rec.get('src')
            dst = rec.get('dst')
            if sport and dport:
                line = f"{src}:{sport} → {dst}:{dport} [{proto}]"
            else:
                line = f"{src} → {dst} [{proto}]"
            self.log_packets.append(line)

        # KPI paquets/min
        self._packets_last_count += drained
        self.kpis[0] = ("Paquets/min", str(self._packets_last_count))

        # KPI alertes
        try:
            alerts = int(self.log_alerts.text.index('end-1c').split('.')[0]) - 1
        except Exception:
            alerts = 0
        self.kpis[1] = ("Alertes IDS", str(alerts))

        # Mise à jour du carousel
        self.carousel.items = self.kpis

        # --- Graphique temps réel ---
        elapsed = int(time.time() - self.start_time)
        self.data_x.append(elapsed)
        self.data_y.append(self._packets_last_count)
        self.line.set_data(self.data_x, self.data_y)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle()

        self.after(500, self._ui_tick)