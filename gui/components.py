# gui/components.py — Composants UI réutilisables Netalyx PRO
# Refonte complète : StatCard moderne, LogList amélioré, KPIBar, BorIAStatusBadge
import tkinter as tk
import ttkbootstrap as tb
import time
from typing import List, Tuple


# ══════════════════════════════════════════════════════════════════════
#  STAT CARD — Carte KPI avec accent coloré et animation
# ══════════════════════════════════════════════════════════════════════
class StatCard(tb.Frame):
    def __init__(self, master, title: str, value: str,
                 accent: str = "#00aaff", icon: str = "",
                 width=220, height=90):
        super().__init__(master, padding=0)
        self.configure(style="secondary.TFrame")

        self.cv = tk.Canvas(self, width=width, height=height,
                            highlightthickness=0, bg="#0d1117")
        self.cv.pack(fill="both", expand=True)

        # Fond principal
        self.cv.create_rectangle(0, 0, width, height, fill="#0d1117", outline="")
        # Accent bar gauche
        self.cv.create_rectangle(0, 0, 4, height, fill=accent, outline="")
        # Bordure subtile
        self.cv.create_rectangle(0, 0, width-1, height-1,
                                  fill="", outline="#1a2535", width=1)

        # Icône
        if icon:
            self.cv.create_text(width-18, 18, text=icon,
                                 font=("Segoe UI", 16), fill=accent, anchor="center")

        # Titre
        self.title_id = self.cv.create_text(14, 18, anchor="nw", text=title,
            fill="#6b8499", font=("Segoe UI", 9, "bold"))

        # Valeur
        self.value_id = self.cv.create_text(14, 42, anchor="nw", text=value,
            fill=accent, font=("Consolas", 22, "bold"))

        # Sous-ligne décorative
        self.cv.create_line(14, height-12, width-14, height-12,
                             fill="#1a2535", width=1)

    def set_value(self, v: str):
        self.cv.itemconfigure(self.value_id, text=v)

    def set_title(self, t: str):
        self.cv.itemconfigure(self.title_id, text=t)


# ══════════════════════════════════════════════════════════════════════
#  KPI BAR — Barre de 4 cartes KPI toujours visible
# ══════════════════════════════════════════════════════════════════════
class KPIBar(tb.Frame):
    """Barre de KPI statique — remplace le carousel rotatif."""

    CARDS = [
        ("Paquets capturés",   "0", "#00aaff", "📦"),
        ("Alertes IDS",        "0", "#ff4455", "🚨"),
        ("Appareils détectés", "0", "#00dd88", "🖥"),
        ("Score ML moyen",     "—", "#ffaa00", "🧬"),
    ]

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._cards: List[StatCard] = []
        for title, value, accent, icon in self.CARDS:
            c = StatCard(self, title=title, value=value,
                         accent=accent, icon=icon, width=230, height=88)
            c.pack(side="left", padx=(0, 8), fill="x", expand=True)
            self._cards.append(c)

    def update(self, packets: int, alerts: int, devices: int, ml_score: str = "—"):
        vals = [str(packets), str(alerts), str(devices), ml_score]
        for card, val in zip(self._cards, vals):
            card.set_value(val)


# ══════════════════════════════════════════════════════════════════════
#  LOG LIST — Panneau de logs avec coloration syntaxique améliorée
# ══════════════════════════════════════════════════════════════════════
class LogList(tb.Frame):
    MAX_LINES = 500   # limite pour éviter la montée en mémoire

    def __init__(self, master, title="Logs", height=12,
                 color_map: dict = None, show_toolbar=True):
        super().__init__(master, padding=6)
        self.configure(style="secondary.TFrame")
        self.color_map = color_map or {}

        # En-tête avec titre + bouton clear
        hdr = tk.Frame(self, bg="#0d1117")
        hdr.pack(fill="x", pady=(0, 4))
        tk.Label(hdr, text=title, font=("Segoe UI", 11, "bold"),
                 fg="#a8c0d6", bg="#0d1117").pack(side="left")
        if show_toolbar:
            tk.Button(hdr, text="⬛ Vider", font=("Segoe UI", 8),
                      bg="#1a2535", fg="#6b8499", relief="flat",
                      cursor="hand2", bd=0, padx=6,
                      command=self.clear).pack(side="right")

        # Zone texte
        box = tk.Frame(self, bg="#0a0e16")
        box.pack(fill="both", expand=True)

        self.text = tk.Text(
            box, height=height,
            bg="#0a0e16", fg="#c9d9e8",
            insertbackground="#c9d9e8",
            selectbackground="#1a3050",
            bd=0, relief="flat",
            font=("Consolas", 10),
            padx=10, pady=6,
            wrap="none"
        )
        self.text.pack(side="left", fill="both", expand=True)
        self.text.configure(state="disabled")

        # Scrollbars
        vsb = tb.Scrollbar(box, orient="vertical",   command=self.text.yview)
        hsb = tb.Scrollbar(box, orient="horizontal",  command=self.text.xview)
        vsb.pack(side="right",  fill="y")
        self.text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Tags de couleur
        self.text.tag_configure("ts",   foreground="#3a5070")
        self.text.tag_configure("info", foreground="#c9d9e8")
        for kw, color in self.color_map.items():
            self.text.tag_configure(kw, foreground=color, font=("Consolas", 10, "bold"))

        # Tag BorIA
        self.text.tag_configure("boria", foreground="#aa66ff")

    def append(self, line: str, tag: str = "info"):
        self.text.configure(state="normal")

        # Limite mémoire
        count = int(self.text.index("end-1c").split(".")[0])
        if count > self.MAX_LINES:
            self.text.delete("1.0", "100.0")

        ts   = time.strftime("%H:%M:%S")
        full = f"[{ts}] {line}\n"

        self.text.insert("end", f"[{ts}] ", "ts")
        self.text.insert("end", f"{line}\n", tag)

        # Colorisation par mot-clé
        for kw in self.color_map:
            start = "1.0"
            while True:
                pos = self.text.search(kw, start, stopindex="end")
                if not pos:
                    break
                end = f"{pos}+{len(kw)}c"
                self.text.tag_add(kw, pos, end)
                start = end

        # Tag BorIA
        if "[BorIA]" in line or "[AI]" in line:
            idx = self.text.index("end-2l")
            self.text.tag_add("boria", idx, "end-1c")

        self.text.see("end")
        self.text.configure(state="disabled")

    def clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

    def get_line_count(self) -> int:
        return int(self.text.index("end-1c").split(".")[0]) - 1


# ══════════════════════════════════════════════════════════════════════
#  BORIA STATUS BADGE — Indicateur de connexion BorIA dans la barre
# ══════════════════════════════════════════════════════════════════════
class BorIAStatusBadge(tk.Frame):
    """Petit badge affichant l'état de connexion au moteur BorIA."""

    def __init__(self, master, **kwargs):
        super().__init__(master, bg="#0d1117", **kwargs)
        self._dot = tk.Canvas(self, width=10, height=10,
                               bg="#0d1117", highlightthickness=0)
        self._dot.create_oval(1,1,9,9, fill="#333", tags="dot")
        self._dot.pack(side="left", padx=(0,4))
        self._lbl = tk.Label(self, text="BorIA: —",
                              font=("Segoe UI",8), fg="#445566", bg="#0d1117")
        self._lbl.pack(side="left")
        self._pulse_state = False
        self._animate()

    def set_online(self, online: bool):
        color = "#44ff88" if online else "#555555"
        text  = "BorIA: En ligne" if online else "BorIA: Hors ligne"
        fg    = "#44ff88" if online else "#445566"
        self._dot.itemconfig("dot", fill=color)
        self._lbl.config(text=text, fg=fg)

    def _animate(self):
        """Pulse quand connecté."""
        self.after(800, self._animate)


# ══════════════════════════════════════════════════════════════════════
#  SEPARATOR PRO — Séparateur horizontal stylé
# ══════════════════════════════════════════════════════════════════════
class ProSeparator(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, height=1, highlightthickness=0,
                         bg="#0d1117", **kwargs)
        self.bind("<Configure>", self._draw)

    def _draw(self, event=None):
        w = self.winfo_width()
        self.delete("all")
        self.create_line(0, 0, w, 0, fill="#1a2535", width=1)


# ══════════════════════════════════════════════════════════════════════
#  CAROUSEL — Conservé pour compatibilité (aliasé sur KPIBar)
# ══════════════════════════════════════════════════════════════════════
class Carousel(KPIBar):
    """Alias de compatibilité — utilise KPIBar en interne."""
    def __init__(self, master, items, slide_ms=3500):
        super().__init__(master)
        if items:
            for i, (title, value) in enumerate(items[:4]):
                if i < len(self._cards):
                    self._cards[i].set_title(title)
                    self._cards[i].set_value(value)
