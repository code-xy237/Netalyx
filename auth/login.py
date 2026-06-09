# auth/login.py — Page de connexion Netalyx PRO (refonte UI)
import tkinter as tk
from tkinter import messagebox, simpledialog
import ttkbootstrap as tb
from PIL import Image, ImageTk, ImageDraw, ImageFilter

from auth.otp import send_otp
from auth.utils import verify_otp, authenticate_user
from common import resource_path

_LANCZOS = getattr(Image, "Resampling", Image).LANCZOS


class LoginFrame(tk.Frame):
    def __init__(self, parent, on_success, goto_signup):
        super().__init__(parent, bg="#070a10")
        self.on_success  = on_success
        self.goto_signup = goto_signup
        self._img_refs   = []
        self._build()

    def _build(self):
        # ── Fond ──────────────────────────────────────────────────────
        try:
            img = Image.open(resource_path("assets/fond_2.png"))
            img = img.resize((1920, 1080), _LANCZOS).convert("RGBA")
            ov  = Image.new("RGBA", img.size, (5, 10, 20, 180))
            img = Image.alpha_composite(img, ov)
            ph  = ImageTk.PhotoImage(img)
            self._img_refs.append(ph)
            tk.Label(self, image=ph, bg="#070a10").place(
                relx=0, rely=0, relwidth=1, relheight=1)
        except Exception:
            self.configure(bg="#070a10")

        # ── Panneau central ────────────────────────────────────────────
        panel = tk.Frame(self, bg="#0d1520", bd=0,
                         highlightbackground="#1a3050", highlightthickness=1)
        panel.place(relx=0.5, rely=0.5, anchor="center", width=400)

        # Accent bar top
        tk.Frame(panel, bg="#0055cc", height=3).pack(fill="x")

        inner = tk.Frame(panel, bg="#0d1520", padx=36, pady=36)
        inner.pack(fill="both", expand=True)

        # Logo / Titre
        try:
            img2 = Image.open(resource_path("assets/logo-2.png"))
            img2 = img2.resize((160, 44), _LANCZOS).convert("RGBA")
            ph2  = ImageTk.PhotoImage(img2)
            self._img_refs.append(ph2)
            tk.Label(inner, image=ph2, bg="#0d1520").pack(pady=(0, 8))
        except Exception:
            tk.Label(inner, text="NETALYX",
                     font=("Consolas", 28, "bold"),
                     fg="#0088ff", bg="#0d1520").pack(pady=(0, 8))

        tk.Label(inner, text="Network Security Monitor",
                 font=("Segoe UI", 10), fg="#2a4a6a",
                 bg="#0d1520").pack()
        tk.Frame(inner, bg="#1a3050", height=1).pack(fill="x", pady=18)

        tk.Label(inner, text="CONNEXION",
                 font=("Segoe UI", 11, "bold"),
                 fg="#4a7090", bg="#0d1520").pack(anchor="w")

        # Champ utilisateur
        tk.Label(inner, text="Identifiant",
                 font=("Segoe UI", 9), fg="#3a5570",
                 bg="#0d1520").pack(anchor="w", pady=(12, 2))
        self.user_var = tk.StringVar()
        user_e = tk.Entry(inner, textvariable=self.user_var,
                          font=("Segoe UI", 11),
                          bg="#111d2b", fg="#c9d9e8",
                          insertbackground="#c9d9e8",
                          relief="flat", bd=0,
                          highlightbackground="#1a3050",
                          highlightthickness=1)
        user_e.pack(fill="x", ipady=8)

        # Champ mot de passe
        tk.Label(inner, text="Mot de passe",
                 font=("Segoe UI", 9), fg="#3a5570",
                 bg="#0d1520").pack(anchor="w", pady=(10, 2))
        self.pass_var = tk.StringVar()
        pass_e = tk.Entry(inner, textvariable=self.pass_var,
                          show="●", font=("Segoe UI", 11),
                          bg="#111d2b", fg="#c9d9e8",
                          insertbackground="#c9d9e8",
                          relief="flat", bd=0,
                          highlightbackground="#1a3050",
                          highlightthickness=1)
        pass_e.pack(fill="x", ipady=8)
        pass_e.bind("<Return>", lambda e: self._login())

        # Bouton connexion
        btn = tk.Button(inner, text="SE CONNECTER",
                        font=("Segoe UI", 10, "bold"),
                        bg="#0055cc", fg="white",
                        activebackground="#0044aa",
                        activeforeground="white",
                        relief="flat", bd=0, cursor="hand2",
                        command=self._login)
        btn.pack(fill="x", pady=(22, 0), ipady=11)

        # Hover
        btn.bind("<Enter>", lambda e: btn.config(bg="#0066dd"))
        btn.bind("<Leave>", lambda e: btn.config(bg="#0055cc"))

        tk.Frame(inner, bg="#1a3050", height=1).pack(fill="x", pady=16)

        # Lien inscription
        lnk = tk.Label(inner, text="Pas encore de compte ?  Créer un compte →",
                        font=("Segoe UI", 9), fg="#225580",
                        bg="#0d1520", cursor="hand2")
        lnk.pack()
        lnk.bind("<Enter>", lambda e: lnk.config(fg="#0088ff"))
        lnk.bind("<Leave>", lambda e: lnk.config(fg="#225580"))
        lnk.bind("<Button-1>", lambda e: self.goto_signup())

        # BorIA badge
        tk.Label(inner, text="⚡ BorIA AI Engine intégré",
                 font=("Segoe UI", 8, "italic"),
                 fg="#1a3050", bg="#0d1520").pack(pady=(10, 0))

    def _login(self):
        username = self.user_var.get().strip()
        password = self.pass_var.get()
        if not username or not password:
            messagebox.showwarning("Champs vides", "Veuillez remplir tous les champs.", parent=self)
            return
        if not authenticate_user(username, password):
            messagebox.showerror("Échec", "Identifiant ou mot de passe incorrect.", parent=self)
            return
        code = send_otp(username)
        if code:
            messagebox.showinfo("Code OTP",
                f"Votre code : {code}\n(Configurez email/Telegram pour l'envoi automatique)",
                parent=self)
        else:
            messagebox.showinfo("OTP", "Code envoyé par email / Telegram.", parent=self)

        # parent=self garantit que la dialog est bien rattachée à la fenêtre principale
        entered = simpledialog.askstring("Vérification OTP", "Code à 6 chiffres :", parent=self)
        if not entered:
            return
        if verify_otp(username, entered.strip()):
            # after() permet à Tkinter de fermer proprement la dialog OTP
            # avant de construire et afficher le Dashboard
            self.after(50, lambda: self.on_success(username))
        else:
            messagebox.showerror("OTP invalide", "Code incorrect ou expiré.", parent=self)
