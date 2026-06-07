# gui/voice_panel.py — Panneau vocal PRO + Intégration BorIA #2
import tkinter as tk
import ttkbootstrap as tb
import threading


class VoicePanel(tb.Frame):
    """
    Panneau de contrôle vocal refonte PRO.
    Intégration BorIA #2 : les commandes vocales non reconnues
    sont transmises au chatbot BorIA pour réponse IA.
    """

    COMMANDS_HELP = [
        ("'Reset'",              "→ Réinitialiser le graphe"),
        ("'Bloquer [IP]'",       "→ Bloquer une IP"),
        ("'Suspect [IP]'",       "→ Marquer suspecte"),
        ("'Zoom'",               "→ Zoom scène réseau"),
        ("'Alertes'",            "→ Voir alertes IDS"),
        ("'Stats'",              "→ Statistiques réseau"),
        ("'Rafraîchir'",         "→ Actualiser données"),
        ("[Toute question]",     "→ BorIA répond en IA ⚡"),
    ]

    def __init__(self, master, voice_engine=None, **kwargs):
        super().__init__(master, padding=10, style="secondary.TFrame", **kwargs)
        self.ve             = voice_engine
        self._active        = tk.BooleanVar(value=False)
        self._status_text   = tk.StringVar(value="⏸ En veille")
        self._last_text     = tk.StringVar(value="—")
        self._last_cmd      = tk.StringVar(value="—")
        self._boria_reply   = tk.StringVar(value="—")
        self._build_ui()

    def _build_ui(self):
        # ── Titre ──────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg="#0d1117")
        hdr.pack(fill="x", pady=(0, 8))
        tk.Label(hdr, text="🎙  Assistant Vocal",
                 font=("Segoe UI", 12, "bold"),
                 fg="#a8c0d6", bg="#0d1117").pack(side="left")
        self._btn = tb.Checkbutton(hdr, text="Activer",
                                    variable=self._active,
                                    bootstyle="success-round-toggle",
                                    command=self._toggle)
        self._btn.pack(side="right")

        # ── Statut ──────────────────────────────────────────────────────
        stat = tk.Frame(self, bg="#111d2b",
                         highlightbackground="#1a3050",
                         highlightthickness=1)
        stat.pack(fill="x", pady=(0, 8))
        inner = tk.Frame(stat, bg="#111d2b", padx=10, pady=8)
        inner.pack(fill="x")

        self._dot = tk.Canvas(inner, width=12, height=12,
                               bg="#111d2b", highlightthickness=0)
        self._dot.create_oval(1,1,11,11, fill="#333", tags="dot")
        self._dot.pack(side="left", padx=(0, 6))
        tk.Label(inner, textvariable=self._status_text,
                 font=("Segoe UI", 10), fg="#6b8499",
                 bg="#111d2b").pack(side="left")

        # ── Texte reconnu ───────────────────────────────────────────────
        self._make_card("Texte reconnu",  self._last_text,  "#4488cc")
        self._make_card("Commande",       self._last_cmd,   "#44cc88")

        # ── Réponse BorIA ───────────────────────────────────────────────
        bcard = tk.Frame(self, bg="#0d1117",
                          highlightbackground="#442255",
                          highlightthickness=1)
        bcard.pack(fill="x", pady=(0, 8))
        tk.Frame(bcard, bg="#6633aa", height=2).pack(fill="x")
        bi = tk.Frame(bcard, bg="#0d1117", padx=10, pady=8)
        bi.pack(fill="x")
        tk.Label(bi, text="⚡ Réponse BorIA",
                 font=("Segoe UI", 9, "bold"),
                 fg="#8844cc", bg="#0d1117").pack(anchor="w")
        tk.Label(bi, textvariable=self._boria_reply,
                 font=("Consolas", 9), fg="#cc99ff",
                 bg="#0d1117", wraplength=220,
                 justify="left").pack(anchor="w", pady=(4, 0))

        # ── Commandes disponibles ───────────────────────────────────────
        hlp = tk.Frame(self, bg="#0d1117",
                        highlightbackground="#1a3050",
                        highlightthickness=1)
        hlp.pack(fill="both", expand=True)
        tk.Frame(hlp, bg="#0055cc", height=2).pack(fill="x")
        hi = tk.Frame(hlp, bg="#0d1117", padx=10, pady=8)
        hi.pack(fill="both", expand=True)
        tk.Label(hi, text="Commandes disponibles",
                 font=("Segoe UI", 9, "bold"),
                 fg="#3a5570", bg="#0d1117").pack(anchor="w", pady=(0, 6))
        for cmd, desc in self.COMMANDS_HELP:
            row = tk.Frame(hi, bg="#0d1117")
            row.pack(fill="x", pady=2)
            tk.Label(row, text=cmd, font=("Consolas", 8),
                     fg="#4477aa", bg="#0d1117").pack(side="left")
            tk.Label(row, text=desc, font=("Segoe UI", 8),
                     fg="#3a5060", bg="#0d1117").pack(side="left", padx=(6, 0))

    def _make_card(self, label: str, var: tk.StringVar, accent: str):
        f = tk.Frame(self, bg="#111d2b",
                      highlightbackground="#1a3050",
                      highlightthickness=1)
        f.pack(fill="x", pady=(0, 8))
        tk.Frame(f, bg=accent, height=2).pack(fill="x")
        i = tk.Frame(f, bg="#111d2b", padx=10, pady=6)
        i.pack(fill="x")
        tk.Label(i, text=label, font=("Segoe UI", 8, "bold"),
                 fg="#3a5570", bg="#111d2b").pack(anchor="w")
        tk.Label(i, textvariable=var, font=("Consolas", 9),
                 fg="#a8c0d6", bg="#111d2b",
                 wraplength=220).pack(anchor="w", pady=(2, 0))

    # ── Contrôle ────────────────────────────────────────────────────────
    def _toggle(self):
        if self._active.get():
            self._start()
        else:
            self._stop()

    def _start(self):
        if not self.ve:
            self._status_text.set("⚠ Moteur non disponible")
            self._dot.itemconfig("dot", fill="#ff8800")
            return
        self.ve.set_on_recognized(self._on_recognized)
        self.ve.start()
        self._status_text.set("🟢 Écoute active")
        self._dot.itemconfig("dot", fill="#44cc88")
        self._animate_pulse()

    def _stop(self):
        if self.ve:
            self.ve.stop()
        self._status_text.set("⏸ En veille")
        self._dot.itemconfig("dot", fill="#333")

    def _on_recognized(self, text: str):
        """Thread vocal → thread Tkinter."""
        self.after(0, self._process_recognized, text)

    def _process_recognized(self, text: str):
        self._last_text.set(text[:45] + ("…" if len(text) > 45 else ""))
        self._status_text.set("🔵 Traitement BorIA…")
        # Intégration BorIA #2 — réponse IA en background
        threading.Thread(target=self._ask_boria, args=(text,),
                         daemon=True).start()

    def _ask_boria(self, text: str):
        try:
            from boria_bridge import BorIABridge
            reply = BorIABridge.get().chat(text)
        except Exception:
            reply = "BorIA hors ligne."
        self.after(0, self._show_boria_reply, reply)

    def _show_boria_reply(self, reply: str):
        self._boria_reply.set(reply[:120] + ("…" if len(reply) > 120 else ""))
        self._status_text.set("🟢 Écoute active")
        # TTS
        if self.ve:
            try:
                self.ve.speak(reply)
            except Exception:
                pass

    def update_command(self, cmd: str):
        self.after(0, self._last_cmd.set, cmd)

    def _animate_pulse(self):
        if not self._active.get():
            return
        c = self._dot.itemcget("dot", "fill")
        self._dot.itemconfig("dot", fill="#22aa55" if c == "#44cc88" else "#44cc88")
        self.after(700, self._animate_pulse)
