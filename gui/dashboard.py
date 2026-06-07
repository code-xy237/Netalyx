# gui/dashboard.py — Dashboard PRO Netalyx (refonte complète + BorIA)
import tkinter as tk
import ttkbootstrap as tb
from queue import Queue
import time
from collections import deque

from sniffer.capture import SnifferService
from sniffer.analyzer import RecentPackets
from ids.detector import IDSService
from network.monitor import NetworkMonitor
from gui.components import KPIBar, LogList, BorIAStatusBadge
from gui.settings_panel import SettingsPanel
from gui.ml_tab import MLIDSTab
from gui.graph_tab import GraphTab
from gui.web_tab import WebTab
from gui.voice_panel import VoicePanel
from security.network_graph import NetworkGraph
from gui.security_tabs import (BannerCVETab, TLSAuditTab, MisconfigTab,
                                TracerouteTab, TimelineTab, ReportTab)
from security.ml_ids import MLIDSService
from security.notifier import alert as notify_all
from security.threat_intel import enrich_ip
from boria_bridge import BorIABridge
from common import resource_path, CFG

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Couleurs alertes
ALERT_COLORS = {
    "CRITICAL_INCIDENT": "#ff2222",
    "HIGH_PACKET_RATE":  "#ff8800",
    "SYN_SCAN":          "#ffcc00",
    "PORT_PROBING":      "#ff8800",
    "IP_BLOCKED":        "#cc44ff",
    "ANOMALY_DETECTED":  "#ff6633",
}

# Palette dark pro
BG_MAIN   = "#070a10"
BG_PANEL  = "#0d1117"
BG_CARD   = "#111d2b"
FG_MAIN   = "#c9d9e8"
FG_DIM    = "#3a5570"
ACCENT    = "#0055cc"
ACCENT2   = "#00aaff"


class Dashboard(tb.Frame):
    def __init__(self, master, username: str):
        super().__init__(master, padding=0, style="secondary.TFrame")
        self.username = username
        self._boria   = BorIABridge.get()
        self._boria.start_jar()

        self._build_topbar()
        self._build_notebook()
        self._init_services()

    # ══════════════════════════════════════════════════════════════════
    #  TOPBAR PROFESSIONNELLE
    # ══════════════════════════════════════════════════════════════════
    def _build_topbar(self):
        bar = tk.Frame(self, bg=BG_PANEL,
                       highlightbackground="#1a3050",
                       highlightthickness=1)
        bar.pack(fill="x", side="top")

        # Accent left bar
        tk.Frame(bar, bg=ACCENT, width=4).pack(side="left", fill="y")

        left = tk.Frame(bar, bg=BG_PANEL, padx=14, pady=8)
        left.pack(side="left", fill="y")
        tk.Label(left, text="NETALYX PRO",
                 font=("Consolas", 16, "bold"),
                 fg=ACCENT2, bg=BG_PANEL).pack(side="left")
        tk.Label(left, text="  Network Security Monitor",
                 font=("Segoe UI", 10),
                 fg=FG_DIM, bg=BG_PANEL).pack(side="left")

        right = tk.Frame(bar, bg=BG_PANEL, padx=14, pady=8)
        right.pack(side="right", fill="y")

        # Utilisateur
        tk.Label(right, text=f"👤  {self.username}",
                 font=("Segoe UI", 9),
                 fg="#4477aa", bg=BG_PANEL).pack(side="right", padx=(10, 0))

        # Paramètres
        btn_cfg = tk.Button(right, text="⚙",
                             font=("Segoe UI", 13),
                             bg=BG_PANEL, fg=FG_DIM,
                             relief="flat", bd=0,
                             cursor="hand2",
                             command=lambda: SettingsPanel(self))
        btn_cfg.pack(side="right", padx=6)
        btn_cfg.bind("<Enter>", lambda e: btn_cfg.config(fg=ACCENT2))
        btn_cfg.bind("<Leave>", lambda e: btn_cfg.config(fg=FG_DIM))

        # Badge BorIA
        self._boria_badge = BorIAStatusBadge(right)
        self._boria_badge.pack(side="right", padx=(0, 12))

        # Heure
        self._time_lbl = tk.Label(right,
                                   font=("Consolas", 10),
                                   fg="#224455", bg=BG_PANEL)
        self._time_lbl.pack(side="right", padx=(0, 16))
        self._tick_clock()

    def _tick_clock(self):
        self._time_lbl.config(text=time.strftime("%H:%M:%S"))
        self._boria_badge.set_online(self._boria.online)
        self.after(1000, self._tick_clock)

    # ══════════════════════════════════════════════════════════════════
    #  NOTEBOOK — 11 onglets
    # ══════════════════════════════════════════════════════════════════
    def _build_notebook(self):
        style = tb.Style()
        style.configure("TNotebook",       background=BG_MAIN)
        style.configure("TNotebook.Tab",   background=BG_PANEL,
                        foreground=FG_DIM,
                        font=("Segoe UI", 9, "bold"),
                        padding=[10, 5])
        style.map("TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "white")])

        self.nb = tb.Notebook(self, bootstyle="dark")
        self.nb.pack(fill="both", expand=True, padx=0, pady=0)

        # ── Onglet 1 : Surveillance ────────────────────────────────────
        main_tab = tk.Frame(self.nb, bg=BG_MAIN)
        self.nb.add(main_tab, text="📡  Surveillance")
        self._build_surveillance(main_tab)

        # ── Onglet 2-7 : Sécurité ─────────────────────────────────────
        self.nb.add(BannerCVETab(self.nb),   text="🔍  Banner / CVE")
        self.nb.add(TLSAuditTab(self.nb),    text="🔒  Audit TLS")
        self.nb.add(MisconfigTab(self.nb),   text="⚠  Misconfigs")
        self.nb.add(TracerouteTab(self.nb),  text="🗺  Traceroute")
        self.nb.add(TimelineTab(self.nb),    text="⏱  Timeline")

        # ── Onglet 8 : ML IDS ─────────────────────────────────────────
        self.ml_service = MLIDSService(alert_sink=self._on_ml_alert)
        self.ml_tab     = MLIDSTab(self.nb, ml_service=self.ml_service)
        self.nb.add(self.ml_tab, text="🧬  ML + BorIA")

        # ── Onglet 9 : Cartographie ────────────────────────────────────
        self.net_graph = NetworkGraph()
        self.graph_tab = GraphTab(self.nb, net_graph=self.net_graph)
        self.nb.add(self.graph_tab, text="🕸  Cartographie")

        # ── Onglet 10 : Interface Web ──────────────────────────────────
        self.web_tab = WebTab(self.nb)
        self.nb.add(self.web_tab, text="🌐  Web")

        # ── Onglet 11 : BorIA Chat ─────────────────────────────────────
        self._build_boria_tab()

        # ── Onglet 12 : Rapport ────────────────────────────────────────
        self.nb.add(ReportTab(self.nb, username=self.username), text="📄  Rapport")

    # ══════════════════════════════════════════════════════════════════
    #  ONGLET SURVEILLANCE
    # ══════════════════════════════════════════════════════════════════
    def _build_surveillance(self, parent):
        # ── Barre d'actions ────────────────────────────────────────────
        actions = tk.Frame(parent, bg=BG_PANEL, padx=10, pady=8)
        actions.pack(fill="x")

        def action_btn(text, color, cmd):
            b = tk.Button(actions, text=text,
                           font=("Segoe UI", 9, "bold"),
                           bg=color, fg="white",
                           activebackground=color,
                           relief="flat", bd=0,
                           cursor="hand2",
                           padx=14, pady=6,
                           command=cmd)
            b.pack(side="left", padx=(0, 6))
            return b

        self.btn_sniff     = action_btn("▶  Sniffer",          "#1a6b2a", self.toggle_sniffer)
        self.btn_ids       = action_btn("🛡  Activer IDS",      "#1a4a6b", self.toggle_ids)
        self.btn_ids.config(state="disabled")
        self.btn_mon       = action_btn("🔭  Scanner réseau",   "#6b4a1a", self.toggle_monitor)
        self.btn_pcap_save = action_btn("💾  Export PCAP",      "#2a2a3a", self.export_pcap)
        self.btn_pcap_load = action_btn("📂  Charger PCAP",     "#2a2a3a", self.load_pcap)

        # ── KPI Bar ────────────────────────────────────────────────────
        self.kpi_bar = KPIBar(parent)
        self.kpi_bar.pack(fill="x", padx=10, pady=(8, 4))

        # ── Corps principal ────────────────────────────────────────────
        body = tk.Frame(parent, bg=BG_MAIN)
        body.pack(fill="both", expand=True, padx=10, pady=6)

        # Colonne gauche
        left = tk.Frame(body, bg=BG_MAIN)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.log_packets = LogList(
            left, title="🔵  Trafic réseau temps réel",
            height=14,
            color_map={"CRITICAL_INCIDENT": "#ff2222", "BLOQUÉ": "#cc44ff"}
        )
        self.log_packets.pack(fill="both", expand=True, pady=(0, 6))

        # Graphique Matplotlib
        gf = tk.Frame(left, bg=BG_PANEL,
                       highlightbackground="#1a3050",
                       highlightthickness=1)
        gf.pack(fill="both", expand=False)
        tk.Label(gf, text="Paquets / min",
                 font=("Segoe UI", 9, "bold"),
                 fg=FG_DIM, bg=BG_PANEL).pack(anchor="w", padx=10, pady=(6,0))

        self.fig = Figure(figsize=(6, 2.0), dpi=96, facecolor="#0d1117")
        self.ax  = self.fig.add_subplot(111)
        self.ax.set_facecolor("#070a10")
        self.ax.tick_params(colors="#334455", labelsize=7)
        self.ax.spines[:].set_color("#1a3050")
        self.ax.set_ylabel("Paquets", color="#334455", fontsize=7)
        self.line, = self.ax.plot([], [], color=ACCENT2, lw=1.5)
        self.data_x = deque(maxlen=60)
        self.data_y = deque(maxlen=60)
        self.canvas_fig = FigureCanvasTkAgg(self.fig, master=gf)
        self.canvas_fig.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)

        # Colonne droite
        right = tk.Frame(body, bg=BG_MAIN, width=340)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        self.log_alerts = LogList(
            right, title="🚨  Alertes IDS",
            height=10, color_map=ALERT_COLORS
        )
        self.log_alerts.pack(fill="both", expand=False, pady=(0, 6))

        self.log_devices = LogList(
            right, title="🖥  Appareils & Threat Intel",
            height=9,
            color_map={"CRITIQUE": "#ff4444", "SUSPECT": "#ff8800", "PROPRE": "#00cc66"}
        )
        self.log_devices.pack(fill="both", expand=True)

    # ══════════════════════════════════════════════════════════════════
    #  ONGLET BORIA CHAT
    # ══════════════════════════════════════════════════════════════════
    def _build_boria_tab(self):
        tab = tk.Frame(self.nb, bg=BG_MAIN)
        self.nb.add(tab, text="⚡  BorIA IA")

        # Header
        hdr = tk.Frame(tab, bg="#0d0820", padx=16, pady=12)
        hdr.pack(fill="x")
        tk.Frame(hdr, bg="#6633aa", height=2).pack(fill="x", side="bottom")
        tk.Label(hdr, text="⚡  Assistant Sécurité BorIA",
                 font=("Segoe UI", 14, "bold"),
                 fg="#aa66ff", bg="#0d0820").pack(side="left")
        self._boria_status = tk.Label(hdr, text="● Hors ligne",
                                       font=("Segoe UI", 9),
                                       fg="#555", bg="#0d0820")
        self._boria_status.pack(side="right")

        # Zone de conversation
        chat_frame = tk.Frame(tab, bg=BG_MAIN)
        chat_frame.pack(fill="both", expand=True, padx=16, pady=10)

        self.boria_log = tk.Text(
            chat_frame,
            bg="#08060f", fg="#c0a0ff",
            font=("Consolas", 11),
            bd=0, relief="flat",
            padx=14, pady=10,
            state="disabled",
            wrap="word",
            insertbackground="#aa66ff",
            selectbackground="#2a1050"
        )
        self.boria_log.pack(side="left", fill="both", expand=True)
        vsb = tb.Scrollbar(chat_frame, orient="vertical",
                            command=self.boria_log.yview)
        vsb.pack(side="right", fill="y")
        self.boria_log.configure(yscrollcommand=vsb.set)
        self.boria_log.tag_configure("user",  foreground="#4488cc",
                                      font=("Consolas", 10, "bold"))
        self.boria_log.tag_configure("bot",   foreground="#aa66ff")
        self.boria_log.tag_configure("ts",    foreground="#332244",
                                      font=("Consolas", 8))
        self.boria_log.tag_configure("sys",   foreground="#333355",
                                      font=("Consolas", 9, "italic"))

        # Zone de saisie
        inp_frame = tk.Frame(tab, bg=BG_PANEL, padx=16, pady=10)
        inp_frame.pack(fill="x")

        self.boria_var = tk.StringVar()
        entry = tk.Entry(inp_frame, textvariable=self.boria_var,
                          font=("Segoe UI", 11),
                          bg="#0d0820", fg="#c0a0ff",
                          insertbackground="#aa66ff",
                          relief="flat", bd=0,
                          highlightbackground="#442266",
                          highlightthickness=1)
        entry.pack(side="left", fill="x", expand=True, ipady=9)
        entry.bind("<Return>", lambda e: self._boria_send())

        send = tk.Button(inp_frame, text="Envoyer ⚡",
                          font=("Segoe UI", 10, "bold"),
                          bg="#441188", fg="white",
                          activebackground="#6622aa",
                          relief="flat", bd=0,
                          cursor="hand2", padx=16,
                          command=self._boria_send)
        send.pack(side="right", padx=(8, 0), ipady=9)

        # Message initial
        self._boria_append_sys(
            "BorIA est votre assistant IA intégré. Posez des questions sur la sécurité réseau, "
            "demandez d'expliquer une alerte, ou tapez 'aide'."
        )

    def _boria_send(self):
        msg = self.boria_var.get().strip()
        if not msg:
            return
        self.boria_var.set("")
        self._boria_append("Vous", msg, "user")
        import threading
        threading.Thread(target=self._boria_query, args=(msg,),
                         daemon=True).start()

    def _boria_query(self, msg: str):
        reply = self._boria.chat(msg)
        self.after(0, self._boria_append, "BorIA", reply, "bot")

    def _boria_append(self, who: str, text: str, tag: str):
        self.boria_log.configure(state="normal")
        ts = time.strftime("%H:%M")
        self.boria_log.insert("end", f"[{ts}] ", "ts")
        self.boria_log.insert("end", f"{who}: ", tag)
        self.boria_log.insert("end", f"{text}\n\n", "bot" if tag == "bot" else "user")
        self.boria_log.see("end")
        self.boria_log.configure(state="disabled")

    def _boria_append_sys(self, text: str):
        self.boria_log.configure(state="normal")
        self.boria_log.insert("end", f"[Système] {text}\n\n", "sys")
        self.boria_log.configure(state="disabled")

    # ══════════════════════════════════════════════════════════════════
    #  INITIALISATION DES SERVICES
    # ══════════════════════════════════════════════════════════════════
    def _init_services(self):
        self.gui_queue  = Queue()
        self.ids_queue  = Queue()
        self.sniffer    = SnifferService(self.gui_queue, self.ids_queue)
        self.recent     = RecentPackets()
        self.ids        = IDSService(self.ids_queue, alert_sink=self._on_alert)
        self.monitor    = NetworkMonitor(
            CFG["ip_range"], CFG["port_scan_list"],
            on_new_device=self._on_new_device
        )
        self.alert_count  = 0
        self.device_count = 0
        self.packet_count = 0
        self.start_time   = time.time()
        self.running_sniffer = self.running_ids = self.running_monitor = False
        self.after(500, self._ui_tick)

    # ══════════════════════════════════════════════════════════════════
    #  CALLBACKS
    # ══════════════════════════════════════════════════════════════════
    def _on_ml_alert(self, kind: str, detail: dict):
        self.after(0, self._on_ml_alert_safe, kind, detail)

    def _on_ml_alert_safe(self, kind: str, detail: dict):
        if kind == "ML_MODEL_READY":
            self.log_alerts.append(f"[ML] ✓ {detail.get('message','Modèle prêt')}")
        elif kind == "ML_TRAIN_ERROR":
            self.log_alerts.append(f"[ML] ✗ {detail.get('error','?')}")
        elif kind == "ANOMALY_DETECTED":
            self.alert_count += 1
            self.log_alerts.append(
                f"[ML-ANOMALY] src={detail.get('src','?')} "
                f"score={detail.get('score','?')} — {detail.get('detail','')}"
            )
            notify_all("ANOMALY_DETECTED", detail)

    def _on_alert(self, kind: str, detail: dict):
        self.alert_count += 1
        from ids.alerts import log_alert
        log_alert(kind, detail)
        self.log_alerts.append(f"[{kind}] {detail}")
        src = detail.get("src")
        if src:
            if kind == "IP_BLOCKED":
                self.net_graph.mark_blocked(src)
            elif kind in ALERT_COLORS:
                self.net_graph.mark_suspect(src)
        if kind in ("CRITICAL_INCIDENT", "IP_BLOCKED"):
            notify_all(kind, detail)
        from web.server import push_alert, is_running
        if is_running():
            push_alert(kind, detail)
        if CFG.get("firewall", {}).get("auto_block") and kind == "CRITICAL_INCIDENT" and src:
            ok = self.ids.block_ip(src)
            self.log_alerts.append(
                f"[AUTO-BLOCK] {src} {'bloquée' if ok else 'erreur'}")

    def _on_new_device(self, ip, mac, open_ports, hostname):
        self.after(0, self._on_new_device_safe, ip, mac, open_ports, hostname)

    def _on_new_device_safe(self, ip, mac, open_ports, hostname):
        self.device_count += 1
        self.log_devices.append(
            f"Appareil: {hostname} | {ip} | {mac} | ports:{open_ports[:5]}")
        from web.server import push_device, is_running
        if is_running():
            push_device(ip, mac, hostname, open_ports)
        if CFG.get("threat_intel", {}).get("enabled"):
            enrich_ip(ip, callback=self._on_threat_intel)

    def _on_threat_intel(self, ip, result):
        self.after(0, self._on_threat_intel_safe, ip, result)

    def _on_threat_intel_safe(self, ip, result):
        score   = result.get("threat_score", "?")
        country = result.get("country", "?")
        abuse   = result.get("abuse_score", "?")
        self.log_devices.append(
            f"[ThreatIntel] {ip} → score:{score} | {country} | abuse:{abuse}")

    # ══════════════════════════════════════════════════════════════════
    #  BOUTONS D'ACTION
    # ══════════════════════════════════════════════════════════════════
    def toggle_sniffer(self):
        if not self.running_sniffer:
            self.sniffer.start()
            self.running_sniffer = True
            self.btn_sniff.config(text="⏹  Sniffer", bg="#6b1a1a")
            self.btn_ids.config(state="normal")
        else:
            self.sniffer.stop()
            self.running_sniffer = False
            self.btn_sniff.config(text="▶  Sniffer", bg="#1a6b2a")

    def toggle_ids(self):
        if not self.running_ids:
            self.ids.start()
            self.running_ids = True
            self.btn_ids.config(text="🛡  Désactiver IDS", bg="#4a1a6b")
        else:
            self.ids.stop()
            self.running_ids = False
            self.btn_ids.config(text="🛡  Activer IDS", bg="#1a4a6b")

    def toggle_monitor(self):
        if not self.running_monitor:
            self.monitor.start()
            self.running_monitor = True
            self.btn_mon.config(text="⏹  Scanner réseau", bg="#6b1a1a")
        else:
            self.monitor.stop()
            self.running_monitor = False
            self.btn_mon.config(text="🔭  Scanner réseau", bg="#6b4a1a")

    def export_pcap(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".pcap",
            filetypes=[("PCAP", "*.pcap"), ("Tous", "*.*")],
            initialfile="capture_netalyx.pcap"
        )
        if path:
            ok = self.sniffer.export_pcap(path)
            self.log_packets.append(
                f"[EXPORT] {'OK: ' + path if ok else 'Aucun paquet ou erreur'}")

    def load_pcap(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            filetypes=[("PCAP", "*.pcap *.pcapng"), ("Tous", "*.*")])
        if path:
            self.log_packets.append(f"[IMPORT] Chargement {path}…")
            n = self.sniffer.load_pcap(path, self.ids_queue)
            self.log_packets.append(f"[IMPORT] {n} paquets — IDS analyse…")

    # ══════════════════════════════════════════════════════════════════
    #  TICK UI
    # ══════════════════════════════════════════════════════════════════
    def _ui_tick(self):
        self.ids.poll()
        drained = 0
        while not self.gui_queue.empty() and drained < 40:
            rec = self.gui_queue.get_nowait()
            drained += 1
            self.recent.push(rec)
            self.ml_service.feed(rec)
            self.net_graph.feed(rec)
            from web.server import push_packet, is_running
            if is_running():
                push_packet(rec)
            src, dst, proto = rec.get("src"), rec.get("dst"), rec.get("proto")
            sport, dport    = rec.get("sport"), rec.get("dport")
            line = (f"{src}:{sport} → {dst}:{dport} [{proto}]"
                    if sport else f"{src} → {dst} [{proto}]")
            self.log_packets.append(line)

        self.packet_count += drained

        # ML score moyen
        ml_stats  = self.ml_service.stats()
        avg_score = ml_stats.get("avg_score", 0)
        score_txt = f"{avg_score:.2%}" if ml_stats.get("trained") else "—"

        # KPI
        self.kpi_bar.update(self.packet_count, self.alert_count,
                             self.device_count, score_txt)

        # Graphique
        elapsed = int(time.time() - self.start_time)
        self.data_x.append(elapsed)
        self.data_y.append(self.packet_count)
        self.line.set_data(list(self.data_x), list(self.data_y))
        self.ax.relim(); self.ax.autoscale_view()
        self.canvas_fig.draw_idle()

        # Push web toutes les 3s
        if elapsed % 3 == 0:
            from web.server import update_graph, update_ml_stats, update_top_ips, is_running
            if is_running():
                update_graph(self.net_graph.snapshot())
                update_ml_stats(self.ml_service.stats())
                update_top_ips(self.net_graph.get_top_ips(10))

        self.after(500, self._ui_tick)
