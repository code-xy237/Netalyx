# gui/settings_panel.py — Panneau de configuration (notifications, profils, threat intel)
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb
import json
import copy
import os
from common import resource_path, CFG


class SettingsPanel(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Paramètres Netalyx")
        self.geometry("620x680")
        self.configure(bg="#0e0f12")
        self.resizable(False, False)

        nb = tb.Notebook(self, bootstyle="dark")
        nb.pack(fill="both", expand=True, padx=12, pady=12)

        nb.add(self._build_notifications(nb),  text="Notifications")
        nb.add(self._build_threat_intel(nb),   text="Threat Intel")
        nb.add(self._build_network(nb),        text="Réseau & IDS")
        nb.add(self._build_profiles(nb),       text="Profils")

        tb.Button(self, text="💾  Enregistrer", bootstyle="success",
                  command=self._save).pack(pady=10, ipadx=20, ipady=6)

    # ── Notifications ────────────────────────────────────────────────────
    def _build_notifications(self, parent):
        frame = tb.Frame(parent, padding=16)
        cfg   = CFG.get("notifications", {})

        tb.Label(frame, text="Email (SMTP)", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 6))

        self.email_enabled = tb.BooleanVar(value=cfg.get("email_enabled", False))
        tb.Checkbutton(frame, text="Activer les alertes email",
                       variable=self.email_enabled, bootstyle="success").pack(anchor="w")

        fields = [
            ("SMTP Host",   "email_smtp",     cfg.get("email_smtp", "smtp.gmail.com")),
            ("SMTP Port",   "email_port",     str(cfg.get("email_port", 587))),
            ("Email expéditeur", "email_user", cfg.get("email_user", "")),
            ("Mot de passe",     "email_password", cfg.get("email_password", "")),
            ("Email destinataire", "email_to",  cfg.get("email_to", "")),
        ]
        self._email_vars = {}
        for label, key, default in fields:
            tb.Label(frame, text=label, font=("Segoe UI", 10)).pack(anchor="w", pady=(8, 0))
            show = "*" if "password" in key else ""
            e = tb.Entry(frame, show=show, width=50)
            e.insert(0, default)
            e.pack(anchor="w")
            self._email_vars[key] = e

        tb.Separator(frame).pack(fill="x", pady=14)
        tb.Label(frame, text="Telegram Bot", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 6))

        self.tg_enabled = tb.BooleanVar(value=cfg.get("telegram_enabled", False))
        tb.Checkbutton(frame, text="Activer les alertes Telegram",
                       variable=self.tg_enabled, bootstyle="info").pack(anchor="w")

        tg_fields = [
            ("Bot Token",   "telegram_token",   cfg.get("telegram_token", "")),
            ("Chat ID",     "telegram_chat_id", cfg.get("telegram_chat_id", "")),
        ]
        self._tg_vars = {}
        for label, key, default in tg_fields:
            tb.Label(frame, text=label, font=("Segoe UI", 10)).pack(anchor="w", pady=(8, 0))
            e = tb.Entry(frame, width=50)
            e.insert(0, str(default))
            e.pack(anchor="w")
            self._tg_vars[key] = e

        return frame

    # ── Threat Intel ─────────────────────────────────────────────────────
    def _build_threat_intel(self, parent):
        frame = tb.Frame(parent, padding=16)
        cfg   = CFG.get("threat_intel", {})

        tb.Label(frame, text="APIs de réputation IP",
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 6))

        self.ti_enabled = tb.BooleanVar(value=cfg.get("enabled", False))
        tb.Checkbutton(frame, text="Activer le Threat Intelligence",
                       variable=self.ti_enabled, bootstyle="warning").pack(anchor="w")

        tb.Label(frame, text="Clé AbuseIPDB (gratuit sur abuseipdb.com)",
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(12, 0))
        self._abuse_key = tb.Entry(frame, width=60)
        self._abuse_key.insert(0, cfg.get("abuseipdb_key", ""))
        self._abuse_key.pack(anchor="w")

        tb.Label(frame, text="Clé VirusTotal (gratuit sur virustotal.com)",
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(12, 0))
        self._vt_key = tb.Entry(frame, width=60)
        self._vt_key.insert(0, cfg.get("virustotal_key", ""))
        self._vt_key.pack(anchor="w")

        tb.Label(frame, text="💡 Sans clé, seul AbuseIPDB en lecture publique est disponible.",
                 font=("Segoe UI", 9), bootstyle="secondary").pack(anchor="w", pady=(12, 0))
        return frame

    # ── Réseau & IDS ─────────────────────────────────────────────────────
    def _build_network(self, parent):
        frame = tb.Frame(parent, padding=16)

        tb.Label(frame, text="Plage IP à surveiller",
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))
        self._ip_range = tb.Entry(frame, width=30)
        self._ip_range.insert(0, CFG.get("ip_range", "192.168.1.0/24"))
        self._ip_range.pack(anchor="w")

        tb.Separator(frame).pack(fill="x", pady=14)
        tb.Label(frame, text="Seuils IDS", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))

        ids_cfg = CFG.get("ids", {})
        self._ids_vars = {}
        ids_fields = [
            ("Seuil paquets/fenêtre",      "packet_rate_threshold",  200),
            ("Seuil SYN scan",             "syn_scan_threshold",      40),
            ("Seuil port probing",         "port_probe_threshold",    20),
            ("Fenêtre temporelle (s)",     "burst_window_seconds",    15),
            ("Cooldown alertes (s)",       "alert_cooldown_seconds",  30),
        ]
        for label, key, default in ids_fields:
            row = tb.Frame(frame)
            row.pack(fill="x", pady=3)
            tb.Label(row, text=label, width=32).pack(side="left")
            e = tb.Entry(row, width=8)
            e.insert(0, str(ids_cfg.get(key, default)))
            e.pack(side="left")
            self._ids_vars[key] = e

        tb.Separator(frame).pack(fill="x", pady=14)
        self.auto_block = tb.BooleanVar(value=CFG.get("firewall", {}).get("auto_block", False))
        tb.Checkbutton(frame, text="Blocage IP automatique après CRITICAL_INCIDENT",
                       variable=self.auto_block, bootstyle="danger").pack(anchor="w")
        return frame

    # ── Profils ──────────────────────────────────────────────────────────
    def _build_profiles(self, parent):
        frame = tb.Frame(parent, padding=16)
        tb.Label(frame, text="Profils prédéfinis", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 12))

        profiles = {
            "🏠  Réseau domestique": {"packet_rate_threshold": 150, "syn_scan_threshold": 20,
                                      "port_probe_threshold": 15, "burst_window_seconds": 20,
                                      "alert_cooldown_seconds": 60},
            "🏢  Bureau / Entreprise": {"packet_rate_threshold": 300, "syn_scan_threshold": 50,
                                        "port_probe_threshold": 30, "burst_window_seconds": 10,
                                        "alert_cooldown_seconds": 20},
            "🖥  Serveur (strict)":   {"packet_rate_threshold": 80,  "syn_scan_threshold": 15,
                                       "port_probe_threshold": 10, "burst_window_seconds": 10,
                                       "alert_cooldown_seconds": 10},
        }

        for name, vals in profiles.items():
            btn = tb.Button(frame, text=name, bootstyle="outline",
                            command=lambda v=vals: self._apply_profile(v))
            btn.pack(fill="x", pady=4, ipady=6)

        tb.Label(frame,
                 text="Appliquer un profil remplace les seuils IDS dans l'onglet Réseau.",
                 font=("Segoe UI", 9), bootstyle="secondary").pack(anchor="w", pady=(16, 0))
        return frame

    def _apply_profile(self, vals: dict):
        for key, val in vals.items():
            if key in self._ids_vars:
                self._ids_vars[key].delete(0, "end")
                self._ids_vars[key].insert(0, str(val))
        messagebox.showinfo("Profil", "Profil appliqué. Cliquez sur Enregistrer pour valider.")

    # ── Sauvegarde ───────────────────────────────────────────────────────
    def _save(self):
        try:
            cfg = copy.deepcopy(CFG)

            # Notifications
            notif = cfg.setdefault("notifications", {})
            notif["email_enabled"]   = self.email_enabled.get()
            notif["telegram_enabled"] = self.tg_enabled.get()
            for key, entry in self._email_vars.items():
                notif[key] = entry.get()
            for key, entry in self._tg_vars.items():
                notif[key] = entry.get()

            # Threat intel
            ti = cfg.setdefault("threat_intel", {})
            ti["enabled"]         = self.ti_enabled.get()
            ti["abuseipdb_key"]   = self._abuse_key.get()
            ti["virustotal_key"]  = self._vt_key.get()

            # Réseau & IDS
            cfg["ip_range"] = self._ip_range.get()
            ids = cfg.setdefault("ids", {})
            for key, entry in self._ids_vars.items():
                try:
                    ids[key] = int(entry.get())
                except ValueError:
                    pass
            cfg.setdefault("firewall", {})["auto_block"] = self.auto_block.get()

            with open(resource_path("config.json"), "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)

            messagebox.showinfo("Sauvegardé", "Paramètres enregistrés. Redémarrez pour les appliquer.")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", f"Sauvegarde impossible : {e}")
