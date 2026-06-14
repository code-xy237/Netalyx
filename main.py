# main.py — Point d'entrée Netalyx PRO
# Ordre strict : élévation admin → imports → splash → app
#
# RÈGLE FONDAMENTALE PyInstaller --noconsole :
#   Aucun import lourd (PIL, ttkbootstrap, common, auth…) ne doit avoir lieu
#   avant ensure_admin(). Ces imports peuvent planter si le répertoire de
#   travail change après relance UAC, et le crash serait totalement invisible.
#   → Seuls os, sys, ctypes sont importés au niveau module.

import os
import sys
import ctypes
import datetime


def _app_dir() -> str:
    """Dossier stable de l'exe PyInstaller ou du script en mode dev."""
    return os.path.dirname(
        sys.executable if getattr(sys, "frozen", False)
        else os.path.abspath(__file__)
    )


def _set_app_cwd():
    """Force le dossier courant pour resource_path(), logs et assets."""
    try:
        os.chdir(_app_dir())
    except Exception as exc:
        _log(f"Impossible de changer le dossier courant : {exc}")


# ══════════════════════════════════════════════════════════════════════
#  LOG DE DÉMARRAGE — toujours disponible, même avant tout import
# ══════════════════════════════════════════════════════════════════════
def _log(msg: str):
    """
    Écrit dans netalyx_startup_error.log à côté de l'exe (ou du script).
    Seule façon de voir les erreurs en mode --noconsole PyInstaller.
    """
    try:
        base = _app_dir()
        with open(os.path.join(base, "netalyx_startup_error.log"),
                  "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════
#  ÉLÉVATION ADMINISTRATEUR
#  Appelée EN PREMIER, avant tout import de PIL / tkinter / common
# ══════════════════════════════════════════════════════════════════════
def ensure_admin():
    """
    Windows  : relance l'exe avec UAC si nécessaire, puis quitte l'instance
               non-élevée. Ne passe AUCUN argument supplémentaire à ShellExecuteW
               quand on est un exe PyInstaller (sys.frozen=True) pour éviter le
               crash "exe reçoit son propre chemin en argument".
    Linux/macOS : avertit si non-root (pas de relance auto).
    """
    _set_app_cwd()

    if os.name != "nt":
        # Linux / macOS
        try:
            if os.geteuid() != 0:
                _warn_no_admin_console()
        except AttributeError:
            pass
        return

    # ── Windows ───────────────────────────────────────────────────────
    try:
        already_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        already_admin = False

    if already_admin:
        _log("Démarrage avec droits administrateur — OK")
        return

    # En mode script/IDE, ne pas relancer automatiquement : l'IDE voit sinon
    # l'instance initiale se fermer et l'application semble disparaître.
    frozen = getattr(sys, "frozen", False)
    if not frozen and "--elevate" not in sys.argv:
        _log("Mode développement sans droits admin — poursuite sans relance UAC")
        _warn_no_admin_console()
        return

    # Pas encore admin → relancer avec élévation UAC
    if frozen:
        # Exe PyInstaller : sys.executable == l'exe lui-même
        # params = None  →  Windows lance juste l'exe, sans arguments parasites
        exe, params = sys.executable, None
    else:
        # Script Python : python.exe main.py
        exe    = sys.executable
        script = os.path.abspath(sys.argv[0])
        extra  = [arg for arg in sys.argv[1:] if arg != "--elevate"]
        parts  = [script] + extra
        params = " ".join(f'"{p}"' for p in parts)

    _log(f"Demande élévation UAC — frozen={frozen} exe={exe} params={params}")

    try:
        workdir = _app_dir()
        ret = int(ctypes.windll.shell32.ShellExecuteW(
            None, "runas", exe, params, workdir, 1
        ))
        _log(f"ShellExecuteW retourné {ret} — workdir={workdir}")
        if ret > 32:
            # Instance élevée lancée avec succès → fermer celle-ci
            _log("Instance non-élevée fermée après relance UAC réussie")
            sys.exit(0)
        else:
            # Refus UAC ou erreur (ret ≤ 32) → continuer sans droits admin
            _log(f"UAC refusée ou erreur (code {ret}) — poursuite sans droits admin")
            _warn_no_admin_console()
    except SystemExit:
        raise
    except Exception as exc:
        _log(f"ensure_admin exception : {exc}")
        _warn_no_admin_console()


def _warn_no_admin_console():
    """
    Avertit via une fenêtre simple (sans dépendances lourdes).
    N'utilise que tkinter standard, pas ttkbootstrap.
    """
    try:
        import tkinter as _tk
        from tkinter import messagebox as _mb
        r = _tk.Tk()
        r.withdraw()
        _mb.showwarning(
            "Droits administrateur recommandés",
            "Netalyx PRO fonctionne avec des privilèges limités.\n\n"
            "Certaines fonctionnalités (scan ARP complet, capture de paquets, "
            "blocage de pare-feu) peuvent ne pas fonctionner correctement.\n\n"
            "Relancez l'application en tant qu'administrateur pour un fonctionnement optimal."
        )
        r.destroy()
    except Exception as e:
        _log(f"_warn_no_admin_console échoué : {e}")


# ══════════════════════════════════════════════════════════════════════
#  IMPORTS LOURDS — seulement APRÈS ensure_admin()
# ══════════════════════════════════════════════════════════════════════
def _do_imports():
    """
    Importe tous les modules lourds. Appelé après ensure_admin().
    Toute erreur ici est catchée et affichée proprement.
    """
    global tk, messagebox, Image, ImageTk, ImageDraw, tb
    global resource_path, CFG, ensure_db
    global APP_TITLE, APP_VERSION, _LANCZOS

    _log("_do_imports: tkinter début")
    import tkinter as tk
    from tkinter import messagebox
    _log("_do_imports: tkinter OK")

    _log("_do_imports: PIL début")
    from PIL import Image, ImageTk, ImageDraw
    _log("_do_imports: PIL OK")

    _log("_do_imports: ttkbootstrap début")
    import ttkbootstrap as tb
    _log("_do_imports: ttkbootstrap OK")

    _log("_do_imports: auth.utils début")
    from auth.utils import ensure_db
    _log("_do_imports: auth.utils OK")

    _log("_do_imports: common début")
    from common import resource_path, CFG
    _log("_do_imports: common OK")

    APP_TITLE   = "Netalyx PRO — Network Security Monitor"
    APP_VERSION = "3.0 PRO"
    _LANCZOS    = getattr(Image, "Resampling", Image).LANCZOS


# ══════════════════════════════════════════════════════════════════════
#  SPLASH SCREEN
# ══════════════════════════════════════════════════════════════════════
def _run_splash_then(callback):
    """Construit et lance le splash screen, appelle callback() quand terminé."""
    import tkinter as _tk
    from PIL import Image as _Img, ImageTk as _ITk, ImageDraw as _IDraw
    import random, math

    W, H = 640, 380

    STEPS = [
        (0.10, "Initialisation du moteur réseau…"),
        (0.25, "Chargement de la base de données…"),
        (0.40, "Connexion au moteur BorIA IA…"),
        (0.55, "Préparation des modules de sécurité…"),
        (0.70, "Chargement des règles IDS…"),
        (0.85, "Initialisation de l'interface…"),
        (1.00, "Démarrage de Netalyx PRO…"),
    ]
    LANCZOS = getattr(_Img, "Resampling", _Img).LANCZOS

    root = _tk.Tk()
    root.overrideredirect(True)
    root.configure(bg="#050810")
    root.attributes("-topmost", True)

    alpha_ok = True
    try:
        root.attributes("-alpha", 0.0)
    except Exception:
        alpha_ok = False

    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    W = min(W, max(420, sw - 40))
    H = min(H, max(280, sh - 40))
    root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
    root.resizable(False, False)

    img_refs = []
    canvas = _tk.Canvas(root, width=W, height=H, bg="#050810", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    # ── Fond ──────────────────────────────────────────────────────────
    bg = _Img.new("RGB", (W, H), "#050810")
    draw = _IDraw.Draw(bg)
    for x in range(0, W, 32):
        draw.line([(x, 0), (x, H)], fill="#0a1428", width=1)
    for y in range(0, H, 32):
        draw.line([(0, y), (W, y)], fill="#0a1428", width=1)
    cx, cy = W // 2, H // 2
    for r in range(180, 0, -6):
        a = max(0, int(16 * (1 - r / 180)))
        c = (0, int(35 * a / 16) if a else 0, int(70 * a / 16) if a else 0)
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=c)
    draw.rectangle([(0, 0), (W-1, H-1)], outline="#0f3060", width=2)
    draw.rectangle([(3, 3), (W-4, H-4)], outline="#071020", width=1)
    ph_bg = _ITk.PhotoImage(bg)
    img_refs.append(ph_bg)
    canvas.create_image(0, 0, anchor="nw", image=ph_bg)

    random.seed(42)
    for _ in range(28):
        px = random.randint(20, W - 20)
        py = random.randint(20, H - 20)
        rv = random.randint(1, 3)
        co = random.choice(["#0a2040", "#081830", "#061528"])
        canvas.create_oval(px-rv, py-rv, px+rv, py+rv, fill=co, outline="")

    # ── Logo ──────────────────────────────────────────────────────────
    try:
        import os as _os, sys as _sys
        base = getattr(_sys, "_MEIPASS", _os.path.abspath("."))
        logo_path = _os.path.join(base, "assets", "logo-2.png")
        lg = _Img.open(logo_path).resize((220, 60), LANCZOS).convert("RGBA")
        ph_logo = _ITk.PhotoImage(lg)
        img_refs.append(ph_logo)
        canvas.create_image(W//2, 95, anchor="center", image=ph_logo)
    except Exception:
        canvas.create_text(W//2, 95, text="NETALYX",
            font=("Consolas", 38, "bold"), fill="#0088ff", anchor="center")

    canvas.create_text(W//2, 152, text="Network Security Monitor",
        font=("Segoe UI", 12), fill="#4488cc", anchor="center")
    canvas.create_text(W//2, 172, text="Version 3.0 PRO",
        font=("Segoe UI", 9), fill="#1a3050", anchor="center")
    canvas.create_line(80, 197, W-80, 197, fill="#0f3060")
    canvas.create_text(W//2, 214, text="⚡ Powered by BorIA AI Engine",
        font=("Segoe UI", 9, "italic"), fill="#225580", anchor="center")

    # ── Barre de progression ───────────────────────────────────────────
    canvas.create_rectangle(60, 268, W-60, 286, fill="#0a1020", outline="#0f2040")
    bar_id  = canvas.create_rectangle(62, 270, 62, 284, fill="#0055cc", outline="")
    glow_id = canvas.create_rectangle(62, 270, 62, 284, fill="#33aaff", outline="")
    status_id = canvas.create_text(W//2, 300, text="Initialisation…",
        font=("Consolas", 9), fill="#336699", anchor="center")
    pct_id = canvas.create_text(W-58, 277, text="0%",
        font=("Consolas", 8, "bold"), fill="#0088ff", anchor="center")
    canvas.create_text(W//2, H-12,
        text="© 2025 Netalyx PRO  •  Tous droits réservés Par JB Link",
        font=("Segoe UI", 7), fill="#2a4060", anchor="center")

    state = {"alpha": 0.0, "progress": 0.0, "step": 0}

    def redraw_bar():
        bw = int((W - 122) * state["progress"])
        x2 = 62 + bw
        canvas.coords(bar_id,  62, 270, x2, 284)
        canvas.coords(glow_id, max(62, x2-10), 270, x2, 284)
        canvas.itemconfig(pct_id, text=f"{int(state['progress']*100)}%")

    def fade_in():
        if not alpha_ok:
            return
        state["alpha"] = min(1.0, state["alpha"] + 0.07)
        try:
            root.attributes("-alpha", state["alpha"])
        except Exception:
            return
        if state["alpha"] < 1.0:
            root.after(25, fade_in)

    def smooth_to(target, done_cb, pause, step=0, steps=20):
        start = state["progress"]
        if step > steps:
            state["progress"] = target
            redraw_bar()
            root.after(pause, done_cb)
            return
        state["progress"] = start + (target - start) * (step / steps)
        redraw_bar()
        root.after(14, lambda: smooth_to(target, done_cb, pause, step+1, steps))

    def next_step():
        if state["step"] >= len(STEPS):
            root.after(400, finish)
            return
        target, label = STEPS[state["step"]]
        state["step"] += 1
        canvas.itemconfig(status_id, text=label)
        smooth_to(target, done_cb=next_step, pause=260)

    def finish():
        def fade_out():
            if not alpha_ok:
                _destroy_and_go()
                return
            try:
                a = root.attributes("-alpha")
                if a > 0.04:
                    root.attributes("-alpha", a - 0.06)
                    root.after(20, fade_out)
                else:
                    _destroy_and_go()
            except Exception:
                _destroy_and_go()
        fade_out()

    def _destroy_and_go():
        try:
            root.destroy()
        except Exception:
            pass
        callback()

    root.after(30, fade_in)
    root.after(600, next_step)
    root.mainloop()


# ══════════════════════════════════════════════════════════════════════
#  APPLICATION PRINCIPALE
# ══════════════════════════════════════════════════════════════════════
def launch_app():
    _log("launch_app: début")
    import tkinter as _tk
    from tkinter import messagebox as _mb
    import ttkbootstrap as _tb
    _log("launch_app: imports tkinter/ttkbootstrap OK")
    from auth.utils import ensure_db as _ensure_db
    from common import resource_path as _rp, CFG as _CFG
    _log("launch_app: imports auth/common OK")
    from gui.dashboard import Dashboard
    _log("launch_app: import gui.dashboard OK")
    from auth.login    import LoginFrame
    from auth.signup   import SignupFrame

    _ensure_db()
    _log("launch_app: base de données OK")
    os.makedirs("logs", exist_ok=True)
    for _, path in _CFG.get("logging", {}).items():
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        if not os.path.exists(path):
            open(path, "a", encoding="utf-8").close()

    app = _tb.Window(title="Netalyx PRO — Network Security Monitor",
                     themename="cyborg")
    app.geometry("1366x768")
    app.minsize(1200, 720)
    try:
        app.state("zoomed")
    except Exception:
        try:
            app.attributes("-zoomed", True)
        except Exception:
            sw, sh = app.winfo_screenwidth(), app.winfo_screenheight()
            app.geometry(f"{sw}x{sh}+0+0")

    for ico in ["tache.ico", "assets/icone.ico"]:
        try:
            app.iconbitmap(_rp(ico))
            break
        except Exception:
            pass

    container = _tk.Frame(app, bg="#070a10")
    container.pack(fill="both", expand=True)
    frames: dict = {}

    def show(name):
        for f in frames.values():
            f.pack_forget()
        frames[name].pack(fill="both", expand=True)

    def on_login(username):
        try:
            dash = Dashboard(container, username=username)
            frames["dashboard"] = dash
            show("dashboard")
        except Exception as e:
            import traceback
            err = traceback.format_exc()
            _log(f"Crash chargement dashboard :\n{err}")
            _mb.showerror(
                "Erreur de démarrage",
                f"Impossible de charger le dashboard :\n\n{e}\n\n"
                "Détails enregistrés dans netalyx_startup_error.log"
            )

    frames["signup"] = SignupFrame(container, on_success=lambda: show("login"))
    frames["login"]  = LoginFrame(container, on_success=on_login,
                                   goto_signup=lambda: show("signup"))
    show("login")
    _log("launch_app: interface login affichée")
    app.mainloop()


# ══════════════════════════════════════════════════════════════════════
#  POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import traceback as _tb
    _set_app_cwd()
    _log(f"Entrée main — cwd={os.getcwd()} argv={sys.argv!r}")

    # 1. Élévation admin EN PREMIER — avant tout import lourd
    try:
        ensure_admin()
    except SystemExit:
        raise  # sys.exit(0) de l'instance non-élevée : normal
    except Exception as e:
        _log(f"ensure_admin crash inattendu :\n{_tb.format_exc()}")

    # 2. Imports lourds (PIL, ttkbootstrap, common…)
    try:
        _log("Imports lourds: début")
        _do_imports()
        _log("Imports lourds: OK")
    except Exception as e:
        _log(f"Crash à l'import des modules :\n{_tb.format_exc()}")
        try:
            import tkinter as _tk
            from tkinter import messagebox as _mb
            _r = _tk.Tk(); _r.withdraw()
            _mb.showerror("Netalyx — Module manquant",
                f"Un module requis est introuvable :\n\n{e}\n\n"
                "Relancez install_v3.py pour installer les dépendances.\n"
                "Détails dans : netalyx_startup_error.log")
            _r.destroy()
        except Exception:
            pass
        sys.exit(1)

    # 3. Splash → Application
    try:
        _log("Splash: début")
        _run_splash_then(launch_app)
    except SystemExit:
        raise
    except Exception as e:
        _log(f"Crash splash/app :\n{_tb.format_exc()}")
        try:
            import tkinter as _tk
            from tkinter import messagebox as _mb
            _r = _tk.Tk(); _r.withdraw()
            _mb.showerror("Netalyx — Erreur fatale",
                f"Erreur au démarrage :\n\n{e}\n\n"
                "Détails dans : netalyx_startup_error.log")
            _r.destroy()
        except Exception:
            pass
        sys.exit(1)
