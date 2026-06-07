import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from PIL import Image, ImageTk


class Dashboard(tk.Frame):
    def __init__(self, parent, username="Utilisateur"):
        super().__init__(parent)

        # Charger image de fond
        self.bg_image = Image.open("assets/bg_dashboard.jpg")  # mets une image
        self.bg_image = self.bg_image.resize((1180, 760), Image.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(self.bg_image)

        bg_label = tk.Label(self, image=self.bg_photo)
        bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        # Overlay sombre
        overlay = tk.Frame(self, bg="#000000")
        overlay.place(x=0, y=0, relwidth=1, relheight=1)
        overlay.configure(bg="#000000")
        overlay.tkraise()

        # Barre latérale
        sidebar = tk.Frame(overlay, bg="#1c1c1c", width=220)
        sidebar.pack(side="left", fill="y")

        title = tk.Label(
            sidebar,
            text="⚡ DexTrack",
            font=("Segoe UI", 18, "bold"),
            fg="cyan",
            bg="#1c1c1c"
        )
        title.pack(pady=20)

        user_label = tk.Label(
            sidebar,
            text=f"👤 {username}",
            font=("Segoe UI", 12),
            fg="white",
            bg="#1c1c1c"
        )
        user_label.pack(pady=10)

        # Boutons de navigation
        nav_items = [
            ("📊 Tableau de bord", self.show_dashboard),
            ("🚨 Alertes IDS", self.show_alerts),
            ("📝 Logs", self.show_logs),
            ("⚙ Paramètres", self.show_settings),
            ("❌ Déconnexion", self.logout)
        ]

        for text, cmd in nav_items:
            btn = tk.Button(
                sidebar,
                text=text,
                font=("Segoe UI", 11, "bold"),
                fg="white",
                bg="#2a2a2a",
                activebackground="#00bfff",
                activeforeground="black",
                bd=0,
                relief="flat",
                command=cmd
            )
            btn.pack(fill="x", pady=5, padx=10, ipady=6)

        # Conteneur principal
        self.main_container = tk.Frame(overlay, bg="#121212")
        self.main_container.pack(side="right", fill="both", expand=True)

        self.show_dashboard()

    # --------------------
    # Vues principales
    # --------------------
    def show_dashboard(self):
        self.clear_main()
        tk.Label(
            self.main_container,
            text="📊 Vue générale du réseau",
            font=("Segoe UI", 18, "bold"),
            fg="white",
            bg="#121212"
        ).pack(pady=20)

        # Exemple de cartes statistiques
        stats_frame = tk.Frame(self.main_container, bg="#121212")
        stats_frame.pack(pady=10)

        self.create_stat_card(stats_frame, "Appareils connectés", "15", "#00bfff")
        self.create_stat_card(stats_frame, "Alertes actives", "3", "#ff4d4d")
        self.create_stat_card(stats_frame, "Ports surveillés", "1024", "#4dff4d")

    def show_alerts(self):
        self.clear_main()
        tk.Label(
            self.main_container,
            text="🚨 Alertes IDS",
            font=("Segoe UI", 18, "bold"),
            fg="red",
            bg="#121212"
        ).pack(pady=20)

        alert_list = tk.Listbox(
            self.main_container,
            bg="#1c1c1c",
            fg="white",
            font=("Segoe UI", 11),
            width=80,
            height=15
        )
        alert_list.pack(pady=10)

        # Exemple d’alertes IDS
        alerts = [
            "Intrusion détectée - IP 192.168.1.15",
            "Scan de ports suspect - IP 10.0.0.45",
            "Tentative brute force SSH - IP 172.16.0.8"
        ]
        for a in alerts:
            alert_list.insert("end", a)

    def show_logs(self):
        self.clear_main()
        tk.Label(
            self.main_container,
            text="📝 Journaux système",
            font=("Segoe UI", 18, "bold"),
            fg="white",
            bg="#121212"
        ).pack(pady=20)

        text_area = tk.Text(
            self.main_container,
            bg="#1c1c1c",
            fg="white",
            insertbackground="white",
            font=("Consolas", 10),
            wrap="none",
            height=20
        )
        text_area.pack(padx=20, pady=10, fill="both", expand=True)

        # Exemple log
        sample_logs = [
            "[2025-09-10 10:15] Connexion utilisateur admin",
            "[2025-09-10 10:17] Scan réseau lancé",
            "[2025-09-10 10:20] IDS : alerte brute force détectée"
        ]
        for log in sample_logs:
            text_area.insert("end", log + "\n")

    def show_settings(self):
        self.clear_main()
        tk.Label(
            self.main_container,
            text="⚙ Paramètres",
            font=("Segoe UI", 18, "bold"),
            fg="white",
            bg="#121212"
        ).pack(pady=20)

        tk.Label(
            self.main_container,
            text="(Section à développer : configuration réseau, choix des ports, etc.)",
            font=("Segoe UI", 11),
            fg="gray",
            bg="#121212"
        ).pack(pady=10)

    def logout(self):
        from auth.login import LoginFrame
        for widget in self.parent.winfo_children():
            widget.destroy()
        login = LoginFrame(self.parent, on_success=lambda u: Dashboard(self.parent, u), goto_signup=lambda: None)
        login.pack(fill="both", expand=True)

    # --------------------
    # Outils
    # --------------------
    def clear_main(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()

    def create_stat_card(self, parent, title, value, color):
        card = tk.Frame(parent, bg="#1e1e1e", width=200, height=120, highlightbackground=color, highlightthickness=2)
        card.pack(side="left", padx=10, pady=10)

        tk.Label(
            card,
            text=title,
            font=("Segoe UI", 12, "bold"),
            fg="white",
            bg="#1e1e1e"
        ).pack(pady=10)

        tk.Label(
            card,
            text=value,
            font=("Segoe UI", 20, "bold"),
            fg=color,
            bg="#1e1e1e"
        ).pack()