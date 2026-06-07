import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb
from PIL import Image, ImageTk

from auth.utils import create_user


class SignupFrame(tk.Frame):
    def __init__(self, parent, on_success):
        super().__init__(parent)

        self.parent = parent
        self.on_success = on_success

        # Charger et afficher l'image d'arrière-plan
        self.bg_image = Image.open("assets/bg_signup.jpg")  # Mets ton image ici
        self.bg_image = self.bg_image.resize((1180, 760), Image.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(self.bg_image)

        self.bg_label = tk.Label(self, image=self.bg_photo)
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        # Couche semi-transparente pour lisibilité
        self.overlay = tk.Frame(self, bg="#000000", bd=0)
        self.overlay.place(x=0, y=0, relwidth=1, relheight=1)

        # Conteneur central
        container = tk.Frame(self.overlay, bg="#1c1c1c", bd=0, relief="flat")
        container.place(relx=0.5, rely=0.5, anchor="center")

        # Titre
        title = tk.Label(
            container,
            text="📝 Créez votre compte DexTrack",
            font=("Segoe UI", 22, "bold"),
            fg="white",
            bg="#1c1c1c",
        )
        title.pack(pady=20)

        # Champ utilisateur
        self.username_entry = tb.Entry(
            container,
            bootstyle="info",
            font=("Segoe UI", 12),
            width=30
        )
        self.username_entry.insert(0, "Nom d’utilisateur")
        self.username_entry.pack(pady=10, ipady=5)

        # Champ mot de passe
        self.password_entry = tb.Entry(
            container,
            bootstyle="info",
            font=("Segoe UI", 12),
            show="*",
            width=30
        )
        self.password_entry.insert(0, "Mot de passe")
        self.password_entry.pack(pady=10, ipady=5)

        # Confirmation mot de passe
        self.confirm_entry = tb.Entry(
            container,
            bootstyle="info",
            font=("Segoe UI", 12),
            show="*",
            width=30
        )
        self.confirm_entry.insert(0, "Confirmer le mot de passe")
        self.confirm_entry.pack(pady=10, ipady=5)

        # Bouton inscription
        signup_btn = tb.Button(
            container,
            text="Créer mon compte",
            bootstyle="success",
            command=self.signup
        )
        signup_btn.pack(pady=20, ipadx=10, ipady=5)

        # Lien retour connexion
        back_link = tk.Label(
            container,
            text="Déjà un compte ? Connectez-vous ici",
            fg="cyan",
            bg="#1c1c1c",
            cursor="hand2",
            font=("Segoe UI", 10, "italic")
        )
        back_link.pack()
        back_link.bind("<Button-1>", lambda e: self.on_success())

    def signup(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()

        if password != confirm:
            messagebox.showerror("Erreur", "Les mots de passe ne correspondent pas ⚠️")
            return

        if create_user(username, password):
            messagebox.showinfo("Succès", "Compte créé avec succès 🎉")
            self.on_success()
        else:
            messagebox.showerror("Erreur", "Ce nom d’utilisateur existe déjà ❌")