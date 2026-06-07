# main.py — Point d'entrée Netalyx PRO
# Refonte complète : Splash Screen animé, UI pro, intégration BorIA
import os
import sys
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import ttkbootstrap as tb

from auth.utils import ensure_db
from common import resource_path, CFG

APP_TITLE   = "Netalyx PRO — Network Security Monitor"
APP_VERSION = "3.0 PRO"
_LANCZOS    = getattr(Image, "Resampling", Image).LANCZOS


# ══════════════════════════════════════════════════════════════════════
#  SPLASH SCREEN PROFESSIONNEL ANIMÉ
# ══════════════════════════════════════════════════════════════════════
class SplashScreen:
    STEPS = [
        (0.10, "Initialisation du moteur réseau…"),
        (0.25, "Chargement de la base de données…"),
        (0.40, "Connexion au moteur BorIA IA…"),
        (0.55, "Préparation des modules de sécurité…"),
        (0.70, "Chargement des règles IDS…"),
        (0.85, "Initialisation de l'interface…"),
        (1.00, "Démarrage de Netalyx PRO…"),
    ]
    W, H = 640, 380

    def __init__(self, on_done):
        self.on_done   = on_done
        self._img_refs = []

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg="#050810")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.0)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{self.W}x{self.H}+{(sw-self.W)//2}+{(sh-self.H)//2}")

        self.canvas = tk.Canvas(self.root, width=self.W, height=self.H,
                                bg="#050810", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self._draw_bg()
        self._build_ui()
        self._alpha    = 0.0
        self._progress = 0.0
        self._step_idx = 0

        self.root.after(30,  self._fade_in)
        self.root.after(700, self._animate_progress)

    def _draw_bg(self):
        bg   = Image.new("RGB", (self.W, self.H), "#050810")
        draw = ImageDraw.Draw(bg)
        for x in range(0, self.W, 32):
            draw.line([(x, 0), (x, self.H)], fill="#0a1428", width=1)
        for y in range(0, self.H, 32):
            draw.line([(0, y), (self.W, y)], fill="#0a1428", width=1)
        draw.rectangle([(0,0),(self.W-1,self.H-1)], outline="#0f3060", width=2)
        ph = ImageTk.PhotoImage(bg)
        self._img_refs.append(ph)
        self.canvas.create_image(0, 0, anchor="nw", image=ph)

    def _build_ui(self):
        try:
            img  = Image.open(resource_path("assets/logo-2.png")).resize((220,60),_LANCZOS).convert("RGBA")
            ph   = ImageTk.PhotoImage(img)
            self._img_refs.append(ph)
            self.canvas.create_image(self.W//2, 100, anchor="center", image=ph)
        except Exception:
            self.canvas.create_text(self.W//2, 100, text="NETALYX",
                font=("Consolas",42,"bold"), fill="#0088ff", anchor="center")

        self.canvas.create_text(self.W//2, 158,
            text="Network Security Monitor",
            font=("Segoe UI",13), fill="#4488cc", anchor="center")
        self.canvas.create_text(self.W//2, 178,
            text=f"Version {APP_VERSION}",
            font=("Segoe UI",9), fill="#1a3050", anchor="center")
        self.canvas.create_line(80,203,self.W-80,203, fill="#0f3060")
        self.canvas.create_text(self.W//2, 220,
            text="⚡ Powered by BorIA AI Engine",
            font=("Segoe UI",9,"italic"), fill="#225580", anchor="center")

        # Barre de progression
        self.canvas.create_rectangle(60,275,self.W-60,293,
            fill="#0a1020", outline="#0f2040")
        self.bar_id  = self.canvas.create_rectangle(62,277,62,291,
            fill="#0055cc", outline="")
        self.glow_id = self.canvas.create_rectangle(62,277,62,291,
            fill="#33aaff", outline="")
        self.status_id = self.canvas.create_text(self.W//2, 308,
            text="Initialisation…",
            font=("Consolas",9), fill="#336699", anchor="center")
        self.pct_id = self.canvas.create_text(self.W-62, 284,
            text="0%", font=("Consolas",8,"bold"), fill="#0088ff", anchor="center")
        self.canvas.create_text(self.W//2, self.H-14,
            text="© 2025 Netalyx PRO  •  Tous droits réservés Par JB Link",
            font=("Segoe UI",7), fill="#0f1e30", anchor="center")

    def _fade_in(self):
        self._alpha = min(1.0, self._alpha + 0.07)
        self.root.attributes("-alpha", self._alpha)
        if self._alpha < 1.0:
            self.root.after(25, self._fade_in)

    def _animate_progress(self):
        if self._step_idx >= len(self.STEPS):
            self.root.after(450, self._finish)
            return
        target, label = self.STEPS[self._step_idx]
        self._step_idx += 1
        self.canvas.itemconfig(self.status_id, text=label)
        self._smooth_to(target, done_cb=self._animate_progress, pause=280)

    def _smooth_to(self, target, done_cb, pause, _step=0, _steps=20):
        start = self._progress
        if _step > _steps:
            self._progress = target
            self._redraw_bar()
            self.root.after(pause, done_cb)
            return
        self._progress = start + (target - start) * (_step / _steps)
        self._redraw_bar()
        self.root.after(14, lambda: self._smooth_to(
            target, done_cb, pause, _step+1, _steps))

    def _redraw_bar(self):
        bw  = int((self.W - 122) * self._progress)
        x2  = 62 + bw
        self.canvas.coords(self.bar_id,  62, 277, x2, 291)
        self.canvas.coords(self.glow_id, max(62, x2-10), 277, x2, 291)
        self.canvas.itemconfig(self.pct_id, text=f"{int(self._progress*100)}%")

    def _finish(self):
        def fade():
            a = self.root.attributes("-alpha")
            if a > 0.04:
                self.root.attributes("-alpha", a - 0.06)
                self.root.after(22, fade)
            else:
                self.root.destroy()
                self.on_done()
        fade()

    def run(self):
        self.root.mainloop()


# ══════════════════════════════════════════════════════════════════════
#  LANCEMENT PRINCIPAL
# ══════════════════════════════════════════════════════════════════════
def launch_app():
    from gui.dashboard import Dashboard
    from auth.login   import LoginFrame
    from auth.signup  import SignupFrame

    ensure_db()
    os.makedirs("logs", exist_ok=True)
    for _, path in CFG.get("logging", {}).items():
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        if not os.path.exists(path):
            open(path, "a", encoding="utf-8").close()

    app = tb.Window(title=APP_TITLE, themename="cyborg")
    app.geometry("1366x768")
    app.minsize(1200, 720)
    try:
        app.state("zoomed")
    except Exception:
        app.attributes("-zoomed", True)

    # Icône barre des tâches
    for ico in ["tache.ico", "assets/icone.ico"]:
        try:
            app.iconbitmap(resource_path(ico)); break
        except Exception:
            pass

    container = tk.Frame(app, bg="#070a10")
    container.pack(fill="both", expand=True)
    frames: dict = {}

    def show(name):
        for f in frames.values(): f.pack_forget()
        frames[name].pack(fill="both", expand=True)

    def on_login(username):
        dash = Dashboard(container, username=username)
        frames["dashboard"] = dash
        show("dashboard")

    frames["signup"] = SignupFrame(container, on_success=lambda: show("login"))
    frames["login"]  = LoginFrame(container, on_success=on_login,
                                  goto_signup=lambda: show("signup"))
    show("login")
    app.mainloop()


if __name__ == "__main__":
    SplashScreen(on_done=launch_app).run()
