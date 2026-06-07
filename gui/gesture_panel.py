# gui/gesture_panel.py — Panneau de contrôle gestuel dans le dashboard Tkinter
import tkinter as tk
import ttkbootstrap as tb


class GesturePanel(tb.Frame):
    """
    Panneau de contrôle pour l'interaction gestuelle.
    Affiche les gestes détectés, leur statut, et le guide des gestes.
    """

    GESTURES_GUIDE = [
        ("👆 Pointage",    "Sélectionner un nœud 3D"),
        ("🤏 Pinch",       "Zoom in/out sur la scène"),
        ("👋 Main ouverte","Réinitialiser la vue"),
        ("← Swipe gauche", "Rotation gauche"),
        ("→ Swipe droite", "Rotation droite"),
        ("↑ Swipe haut",   "Actualiser données"),
        ("✌ Deux doigts",  "Pause / Reprendre"),
    ]

    def __init__(self, master, gesture_engine=None, **kwargs):
        super().__init__(master, padding=8, **kwargs)
        self.ge = gesture_engine
        self._active = tk.BooleanVar(value=False)
        self._status_text = tk.StringVar(value="⏸ Inactif")
        self._last_gesture = tk.StringVar(value="—")
        self._gesture_count = tk.IntVar(value=0)
        self._build_ui()

    def _build_ui(self):
        # Header
        hdr = tb.Frame(self)
        hdr.pack(fill="x", pady=(0, 6))
        tb.Label(hdr, text="✋ Interaction Gestuelle",
                 font=("Segoe UI", 12, "bold")).pack(side="left")
        self._btn = tb.Checkbutton(
            hdr, text="Activer", variable=self._active,
            bootstyle="warning-round-toggle",
            command=self._toggle
        )
        self._btn.pack(side="right")

        # Statut
        stat = tb.Labelframe(self, text="Statut caméra", bootstyle="secondary", padding=8)
        stat.pack(fill="x", pady=(0, 6))
        row = tb.Frame(stat)
        row.pack(fill="x")
        self._cam_dot = tk.Canvas(stat, width=14, height=14,
                                   bg="#0e0f12", highlightthickness=0)
        self._cam_dot.create_oval(1, 1, 13, 13, fill="#555", tags="dot")
        self._cam_dot.pack(side="left", padx=(0, 6))
        tb.Label(stat, textvariable=self._status_text,
                 font=("Segoe UI", 10)).pack(side="left")

        # Dernier geste
        gest_card = tb.Labelframe(self, text="Geste détecté", bootstyle="warning", padding=8)
        gest_card.pack(fill="x", pady=(0, 6))
        tb.Label(gest_card, textvariable=self._last_gesture,
                 font=("Segoe UI", 14, "bold"), foreground="#facc15").pack()

        count_row = tb.Frame(gest_card)
        count_row.pack(fill="x")
        tb.Label(count_row, text="Total gestes : ",
                 font=("Segoe UI", 9), foreground="#9ca3af").pack(side="left")
        tb.Label(count_row, textvariable=self._gesture_count,
                 font=("Consolas", 9), foreground="#facc15").pack(side="left")

        # Guide
        guide = tb.Labelframe(self, text="Guide des gestes", bootstyle="warning", padding=8)
        guide.pack(fill="both", expand=True)
        for geste, action in self.GESTURES_GUIDE:
            row = tb.Frame(guide)
            row.pack(fill="x", pady=2)
            tb.Label(row, text=geste, font=("Segoe UI", 9),
                     foreground="#facc15", width=18, anchor="w").pack(side="left")
            tb.Label(row, text=action, font=("Segoe UI", 9),
                     foreground="#9ca3af").pack(side="left")

        # Info webcam
        info = tb.Labelframe(self, text="Info", bootstyle="secondary", padding=6)
        info.pack(fill="x", pady=(6, 0))
        tb.Label(info, text="Nécessite : OpenCV + MediaPipe\npip install opencv-python mediapipe",
                 font=("Segoe UI", 8), foreground="#6b7280").pack()

    def _toggle(self):
        if self._active.get():
            self._start_gesture()
        else:
            self._stop_gesture()

    def _start_gesture(self):
        if not self.ge or not self.ge.available:
            self._status_text.set("⚠ Non disponible")
            self._cam_dot.itemconfig("dot", fill="#ff8800")
            self._active.set(False)
            return
        self.ge.set_on_gesture(self._on_gesture)
        ok = self.ge.start(preview=False)
        if ok:
            self._status_text.set("🟢 Caméra active")
            self._cam_dot.itemconfig("dot", fill="#4ade80")
        else:
            self._status_text.set("✗ Erreur caméra")
            self._cam_dot.itemconfig("dot", fill="#ef4444")
            self._active.set(False)

    def _stop_gesture(self):
        if self.ge:
            self.ge.stop()
        self._status_text.set("⏸ Inactif")
        self._cam_dot.itemconfig("dot", fill="#555")

    def _on_gesture(self, gesture: str, data: dict):
        """Appelé depuis le thread geste → after() pour Tkinter."""
        self.after(0, self._update_gesture, gesture, data)

    def _update_gesture(self, gesture: str, data: dict):
        emoji_map = {
            "pinch": "🤏 Pinch",
            "point": "👆 Pointage",
            "open_hand": "👋 Main ouverte",
            "swipe_left": "← Swipe gauche",
            "swipe_right": "→ Swipe droite",
            "swipe_up": "↑ Swipe haut",
            "swipe_down": "↓ Swipe bas",
        }
        self._last_gesture.set(emoji_map.get(gesture, gesture))
        self._gesture_count.set(self._gesture_count.get() + 1)
