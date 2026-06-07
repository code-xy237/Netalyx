# auth/signup.py — Page inscription Netalyx PRO (refonte UI)
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb
from PIL import Image, ImageTk

from auth.utils import create_user, validate_credentials
from common import resource_path

_LANCZOS = getattr(Image, "Resampling", Image).LANCZOS


class SignupFrame(tk.Frame):
    def __init__(self, parent, on_success):
        super().__init__(parent, bg="#070a10")
        self.on_success = on_success
        self._img_refs  = []
        self._build()

    def _build(self):
        # Fond
        try:
            img = Image.open(resource_path("assets/fond_1.jpeg"))
            img = img.resize((1920, 1080), _LANCZOS).convert("RGBA")
            ov  = Image.new("RGBA", img.size, (5, 10, 20, 190))
            img = Image.alpha_composite(img, ov)
            ph  = ImageTk.PhotoImage(img)
            self._img_refs.append(ph)
            tk.Label(self, image=ph, bg="#070a10").place(
                relx=0, rely=0, relwidth=1, relheight=1)
        except Exception:
            self.configure(bg="#070a10")

        # Panneau central
        panel = tk.Frame(self, bg="#0d1520", bd=0,
                         highlightbackground="#1a3050", highlightthickness=1)
        panel.place(relx=0.5, rely=0.5, anchor="center", width=420)

        tk.Frame(panel, bg="#00cc66", height=3).pack(fill="x")

        inner = tk.Frame(panel, bg="#0d1520", padx=36, pady=30)
        inner.pack(fill="both", expand=True)

        tk.Label(inner, text="NETALYX PRO",
                 font=("Consolas", 22, "bold"),
                 fg="#00cc66", bg="#0d1520").pack()
        tk.Label(inner, text="Créer un compte",
                 font=("Segoe UI", 10), fg="#2a5040",
                 bg="#0d1520").pack(pady=(2, 0))
        tk.Frame(inner, bg="#1a3050", height=1).pack(fill="x", pady=16)

        for label, attr, show in [
            ("Identifiant",            "user_var",    ""),
            ("Mot de passe",           "pass_var",    "●"),
            ("Confirmer le mot de passe", "conf_var", "●"),
        ]:
            tk.Label(inner, text=label,
                     font=("Segoe UI", 9), fg="#3a5570",
                     bg="#0d1520").pack(anchor="w", pady=(8, 2))
            var = tk.StringVar()
            setattr(self, attr, var)
            tk.Entry(inner, textvariable=var,
                     show=show, font=("Segoe UI", 11),
                     bg="#111d2b", fg="#c9d9e8",
                     insertbackground="#c9d9e8",
                     relief="flat", bd=0,
                     highlightbackground="#1a3050",
                     highlightthickness=1).pack(fill="x", ipady=8)

        btn = tk.Button(inner, text="CRÉER MON COMPTE",
                        font=("Segoe UI", 10, "bold"),
                        bg="#007744", fg="white",
                        activebackground="#005533",
                        activeforeground="white",
                        relief="flat", bd=0, cursor="hand2",
                        command=self._signup)
        btn.pack(fill="x", pady=(20, 0), ipady=11)
        btn.bind("<Enter>", lambda e: btn.config(bg="#009955"))
        btn.bind("<Leave>", lambda e: btn.config(bg="#007744"))

        tk.Frame(inner, bg="#1a3050", height=1).pack(fill="x", pady=14)

        lnk = tk.Label(inner,
                        text="Déjà un compte ?  Se connecter →",
                        font=("Segoe UI", 9), fg="#225580",
                        bg="#0d1520", cursor="hand2")
        lnk.pack()
        lnk.bind("<Enter>", lambda e: lnk.config(fg="#0088ff"))
        lnk.bind("<Leave>", lambda e: lnk.config(fg="#225580"))
        lnk.bind("<Button-1>", lambda e: self.on_success())

    def _signup(self):
        username = self.user_var.get().strip()
        password = self.pass_var.get()
        confirm  = self.conf_var.get()
        err = validate_credentials(username, password)
        if err:
            messagebox.showerror("Validation", err); return
        if password != confirm:
            messagebox.showerror("Erreur", "Les mots de passe ne correspondent pas."); return
        if create_user(username, password):
            messagebox.showinfo("Succès", "Compte créé avec succès ✔")
            self.on_success()
        else:
            messagebox.showerror("Erreur", "Ce nom d'utilisateur existe déjà.")
