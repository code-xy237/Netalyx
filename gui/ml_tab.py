# gui/ml_tab.py — Onglet ML IDS dans le dashboard
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb
import threading
import time
from gui.components import LogList

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque


class MLIDSTab(tb.Frame):
    """
    Onglet complet pour le module ML IDS.
    Phases : Apprentissage → Entraînement → Détection
    """

    def __init__(self, master, ml_service):
        super().__init__(master, padding=12)
        self.ml  = ml_service
        self._timer_running = False
        self._train_seconds = 0
        self._score_history = deque(maxlen=120)   # pour le graphique

        self._build_ui()
        self._refresh_status()

    # ── Construction UI ───────────────────────────────────────────────────
    def _build_ui(self):
        # ── Bandeau de statut ─────────────────────────────────────────────
        status_bar = tb.Frame(self, style="dark.TFrame")
        status_bar.pack(fill="x", pady=(0, 10))

        self.lbl_mode = tb.Label(
            status_bar,
            text="● Mode : EN ATTENTE",
            font=("Segoe UI", 13, "bold"),
            bootstyle="secondary"
        )
        self.lbl_mode.pack(side="left", padx=8)

        self.lbl_stats = tb.Label(
            status_bar,
            text="",
            font=("Segoe UI", 10),
            bootstyle="secondary"
        )
        self.lbl_stats.pack(side="right", padx=8)

        # ── Zone de contrôle ──────────────────────────────────────────────
        ctrl = tb.Labelframe(self, text="Contrôle du modèle ML", bootstyle="primary", padding=14)
        ctrl.pack(fill="x", pady=(0, 10))

        # Ligne 1 : Apprentissage
        row1 = tb.Frame(ctrl)
        row1.pack(fill="x", pady=(0, 8))

        tb.Label(row1, text="① Apprentissage",
                 font=("Segoe UI", 11, "bold")).pack(side="left")
        tb.Label(row1,
                 text="  Laisse tourner pendant que tu utilises normalement ton réseau.",
                 font=("Segoe UI", 9), bootstyle="secondary").pack(side="left")

        row1b = tb.Frame(ctrl)
        row1b.pack(fill="x", pady=(0, 4))

        self.btn_train_start = tb.Button(
            row1b, text="▶  Démarrer l'apprentissage",
            bootstyle="success-outline", command=self._start_training, width=28
        )
        self.btn_train_start.pack(side="left", padx=(0, 8))

        self.btn_train_stop = tb.Button(
            row1b, text="⏹  Arrêter & Entraîner",
            bootstyle="warning-outline", command=self._stop_and_train,
            state="disabled", width=24
        )
        self.btn_train_stop.pack(side="left", padx=(0, 8))

        self.lbl_samples = tb.Label(row1b, text="0 paquets collectés",
                                    font=("Segoe UI", 10), bootstyle="secondary")
        self.lbl_samples.pack(side="left", padx=8)

        self.lbl_timer = tb.Label(row1b, text="",
                                  font=("Segoe UI", 10), bootstyle="info")
        self.lbl_timer.pack(side="left")

        # Barre de progression apprentissage
        self.progress = tb.Progressbar(ctrl, bootstyle="info-striped",
                                       mode="indeterminate", length=300)

        # Ligne 2 : Contamination
        row2 = tb.Frame(ctrl)
        row2.pack(fill="x", pady=(8, 4))

        tb.Label(row2, text="Taux de contamination estimé :",
                 font=("Segoe UI", 10)).pack(side="left")

        self.contam_var = tk.DoubleVar(value=0.05)
        tb.Label(row2, text="  1%", font=("Segoe UI", 9),
                 bootstyle="secondary").pack(side="left", padx=(8, 0))
        slider = tb.Scale(row2, from_=0.01, to=0.20,
                          variable=self.contam_var, orient="horizontal",
                          length=160, command=self._update_contam_label)
        slider.pack(side="left", padx=4)
        tb.Label(row2, text="20%", font=("Segoe UI", 9),
                 bootstyle="secondary").pack(side="left")
        self.lbl_contam = tb.Label(row2, text="5%",
                                   font=("Segoe UI", 10, "bold"), bootstyle="info")
        self.lbl_contam.pack(side="left", padx=(8, 0))
        tb.Label(row2,
                 text="  ← fraction de trafic anormal attendue dans les données d'entraînement",
                 font=("Segoe UI", 9), bootstyle="secondary").pack(side="left")

        # Ligne 3 : Détection
        row3 = tb.Frame(ctrl)
        row3.pack(fill="x", pady=(8, 0))

        tb.Label(row3, text="② Détection",
                 font=("Segoe UI", 11, "bold")).pack(side="left")

        self.btn_detect = tb.Button(
            row3, text="🛡  Activer la détection ML",
            bootstyle="info-outline", command=self._activate_detection,
            width=26
        )
        self.btn_detect.pack(side="left", padx=(16, 8))

        self.btn_stop = tb.Button(
            row3, text="⏹  Désactiver",
            bootstyle="secondary-outline", command=self._stop_detection,
            state="disabled", width=16
        )
        self.btn_stop.pack(side="left")

        tb.Label(row3,
                 text="  (nécessite un modèle entraîné)",
                 font=("Segoe UI", 9), bootstyle="secondary").pack(side="left", padx=8)

        # ── Colonnes basses ───────────────────────────────────────────────
        body = tb.Frame(self)
        body.pack(fill="both", expand=True)

        # Gauche : log anomalies
        left = tb.Frame(body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.log = LogList(
            left,
            title="Anomalies détectées par ML",
            height=16,
            color_map={
                "CRITIQUE":         "#ff2222",
                "MODÉRÉ":           "#ff8800",
                "FAIBLE":           "#ffcc00",
                "ML_MODEL_READY":   "#00cc88",
                "ML_TRAIN_ERROR":   "#ff4444",
                "ANOMALY_DETECTED": "#ff6644",
                "SYN":              "#ff8800",
                "RST":              "#ffcc00",
                "sensible":         "#ff8800",
            }
        )
        self.log.pack(fill="both", expand=True)

        # Droite : graphique + stats
        right = tb.Frame(body, width=340)
        right.pack(side="right", fill="y")

        # Graphique : score d'anomalie en temps réel
        gf = tb.Labelframe(right, text="Score d'anomalie (temps réel)",
                           bootstyle="danger", padding=4)
        gf.pack(fill="x", pady=(0, 8))

        self.fig = Figure(figsize=(3.4, 2.2), dpi=96)
        self.ax  = self.fig.add_subplot(111)
        self.ax.set_facecolor("#111318")
        self.fig.patch.set_facecolor("#111318")
        self.ax.tick_params(colors="#888")
        self.ax.set_ylabel("score", color="#888", fontsize=8)
        self.ax.axhline(y=0, color="#444", lw=0.8, linestyle="--")
        self.line_score, = self.ax.plot([], [], color="#ff6644", lw=1.5)
        self.canvas_fig  = FigureCanvasTkAgg(self.fig, master=gf)
        self.canvas_fig.get_tk_widget().pack(fill="both", expand=True)

        # Panneau de stats
        sf = tb.Labelframe(right, text="Statistiques", bootstyle="secondary", padding=10)
        sf.pack(fill="x", pady=(0, 8))

        self._stat_vars = {}
        stat_rows = [
            ("Paquets analysés",  "total_seen"),
            ("Anomalies",         "total_anomaly"),
            ("Taux d'anomalie",   "anomaly_rate"),
            ("Modèle sur disque", "model_on_disk"),
        ]
        for label, key in stat_rows:
            row = tb.Frame(sf)
            row.pack(fill="x", pady=2)
            tb.Label(row, text=label, font=("Segoe UI", 10),
                     width=20).pack(side="left")
            var = tk.StringVar(value="—")
            tb.Label(row, textvariable=var,
                     font=("Segoe UI", 10, "bold")).pack(side="left")
            self._stat_vars[key] = var

        # Bouton reset modèle
        tb.Button(right, text="🗑  Supprimer le modèle",
                  bootstyle="danger-outline",
                  command=self._delete_model).pack(fill="x", pady=(4, 0))

        # Lancement du ticker UI
        self.after(800, self._ui_tick)

    # ── Actions boutons ───────────────────────────────────────────────────
    def _start_training(self):
        self.ml.start_training()
        self.btn_train_start.config(state="disabled")
        self.btn_train_stop.config(state="normal")
        self.progress.pack(fill="x", pady=(6, 0))
        self.progress.start(12)
        self._train_seconds = 0
        self._timer_running = True
        self._tick_timer()
        self.log.append("Apprentissage démarré — génère du trafic normal sur ton réseau.")

    def _stop_and_train(self):
        self.progress.stop()
        self.progress.pack_forget()
        self._timer_running = False
        self.btn_train_stop.config(state="disabled")
        n = self.ml.sample_count
        self.log.append(f"Collecte arrêtée : {n} paquets. Entraînement en cours…")
        contam = round(self.contam_var.get(), 3)
        msg = self.ml.stop_training_and_fit(contamination=contam)
        self.log.append(msg)

    def _activate_detection(self):
        ok = self.ml.set_detecting()
        if ok:
            self.btn_detect.config(state="disabled")
            self.btn_stop.config(state="normal")
            self.btn_train_start.config(state="disabled")
            self.log.append("✓ Détection ML activée — surveillance en cours.")
        else:
            messagebox.showwarning(
                "Modèle manquant",
                "Aucun modèle entraîné trouvé.\n\n"
                "Lance d'abord la phase d'apprentissage,\n"
                "ou place un fichier ml_model.joblib dans logs/."
            )

    def _stop_detection(self):
        self.ml.stop()
        self.btn_detect.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.btn_train_start.config(state="normal")
        self.log.append("Détection ML désactivée.")

    def _delete_model(self):
        import os
        from security.ml_ids import MODEL_PATH, SCALER_PATH
        if messagebox.askyesno("Confirmer", "Supprimer le modèle entraîné ?"):
            for p in (MODEL_PATH, SCALER_PATH):
                try:
                    os.remove(p)
                except FileNotFoundError:
                    pass
            self.ml.detector._loaded = False
            self.ml.stop()
            self.log.append("Modèle supprimé. Relance une phase d'apprentissage.")
            self.btn_detect.config(state="normal")
            self.btn_stop.config(state="disabled")
            self.btn_train_start.config(state="normal")

    def _update_contam_label(self, _=None):
        val = round(self.contam_var.get() * 100)
        self.lbl_contam.config(text=f"{val}%")

    # ── Ticker timer ──────────────────────────────────────────────────────
    def _tick_timer(self):
        if not self._timer_running:
            return
        self._train_seconds += 1
        mins, secs = divmod(self._train_seconds, 60)
        self.lbl_timer.config(text=f"  ⏱ {mins:02d}:{secs:02d}")
        self.after(1000, self._tick_timer)

    # ── Rafraîchissement UI ───────────────────────────────────────────────
    def _refresh_status(self):
        mode = self.ml.mode
        MODE_LABELS = {
            "idle":       ("● EN ATTENTE",    "secondary"),
            "training":   ("● APPRENTISSAGE", "warning"),
            "detecting":  ("● DÉTECTION ML",  "success"),
        }
        text, style = MODE_LABELS.get(mode, ("● ?", "secondary"))
        self.lbl_mode.config(text=f"  {text}", bootstyle=f"inverse-{style}")

    def _ui_tick(self):
        # Statut
        self._refresh_status()

        # Compteur échantillons pendant apprentissage
        if self.ml.mode == "training":
            n = self.ml.sample_count
            self.lbl_samples.config(text=f"{n:,} paquets collectés")

        # Statistiques
        stats = self.ml.stats()
        self._stat_vars["total_seen"].set(f"{stats['total_seen']:,}")
        self._stat_vars["total_anomaly"].set(f"{stats['total_anomaly']:,}")
        self._stat_vars["anomaly_rate"].set(f"{stats['anomaly_rate']} %")
        self._stat_vars["model_on_disk"].set("✓ Oui" if stats["model_on_disk"] else "✗ Non")
        self.lbl_stats.config(
            text=f"Vus : {stats['total_seen']:,}  |  "
                 f"Anomalies : {stats['total_anomaly']:,}  |  "
                 f"Taux : {stats['anomaly_rate']} %"
        )

        # Graphique scores
        recent = self.ml.recent_anomalies(60)
        if recent:
            scores = [r["score"] for r in recent]
            self._score_history.extend(scores)
            ys = list(self._score_history)
            xs = list(range(len(ys)))
            self.line_score.set_data(xs, ys)
            self.ax.set_xlim(0, max(len(ys), 10))
            mn = min(ys) - 0.05
            mx = max(ys) + 0.05
            self.ax.set_ylim(mn, mx)
            self.canvas_fig.draw_idle()

        self.after(800, self._ui_tick)

    # ── Méthode appelée par le dashboard quand un paquet arrive ──────────
    def on_packet(self, rec: dict):
        """Appelée depuis le dashboard pour chaque paquet capturé."""
        self.ml.feed(rec)
