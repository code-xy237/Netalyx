# security/notifier.py — Notifications bureau + email + Telegram
import threading
import smtplib
from email.mime.text import MIMEText
from common import CFG

def notify_desktop(title: str, message: str):
    """Notification bureau native (plyer, cross-platform)."""
    try:
        from plyer import notification
        notification.notify(title=title, message=message[:256],
                            app_name="Netalyx", timeout=8)
    except Exception:
        pass

def notify_email(subject: str, body: str):
    cfg = CFG.get("notifications", {})
    if not cfg.get("email_enabled"):
        return
    try:
        msg = MIMEText(body)
        msg["Subject"] = f"[Netalyx] {subject}"
        msg["From"]    = cfg["email_user"]
        msg["To"]      = cfg["email_to"]
        with smtplib.SMTP(cfg["email_smtp"], cfg["email_port"]) as s:
            s.starttls()
            s.login(cfg["email_user"], cfg["email_password"])
            s.send_message(msg)
    except Exception as e:
        print(f"[Notifier Email] {e}")

def notify_telegram(message: str):
    cfg = CFG.get("notifications", {})
    if not cfg.get("telegram_enabled"):
        return
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{cfg['telegram_token']}/sendMessage",
            data={"chat_id": cfg["telegram_chat_id"], "text": message, "parse_mode": "Markdown"},
            timeout=5
        )
    except Exception as e:
        print(f"[Notifier Telegram] {e}")

def alert(kind: str, detail: dict):
    """Point d'entrée unique — envoie sur tous les canaux activés en parallèle."""
    title = f"Alerte Netalyx : {kind}"
    src   = detail.get("src", "?")
    body  = f"Type : {kind}\nSource : {src}\nDétails : {detail}"
    tg    = f"🚨 *{kind}*\nIP : `{src}`\n`{detail}`"

    threading.Thread(target=notify_desktop, args=(title, body), daemon=True).start()
    threading.Thread(target=notify_email,   args=(title, body), daemon=True).start()
    threading.Thread(target=notify_telegram, args=(tg,),        daemon=True).start()
