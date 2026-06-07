# auth/otp.py — génération OTP + envoi par email/Telegram
import secrets
import smtplib
import threading
from email.mime.text import MIMEText
from auth.utils import set_otp
from common import CFG

def generate_otp(username: str) -> str:
    code = str(secrets.randbelow(900000) + 100000)  # 6 chiffres
    set_otp(username, code, ttl_seconds=300)
    return code

def _send_email(code: str):
    cfg = CFG.get("notifications", {})
    if not cfg.get("email_enabled"):
        return
    try:
        msg = MIMEText(f"Votre code OTP Netalyx : {code}\n\nValide 5 minutes.")
        msg["Subject"] = "Netalyx — Code OTP"
        msg["From"] = cfg["email_user"]
        msg["To"] = cfg["email_to"]
        with smtplib.SMTP(cfg["email_smtp"], cfg["email_port"]) as s:
            s.starttls()
            s.login(cfg["email_user"], cfg["email_password"])
            s.send_message(msg)
    except Exception as e:
        print(f"[OTP Email] Erreur : {e}")

def _send_telegram(code: str):
    cfg = CFG.get("notifications", {})
    if not cfg.get("telegram_enabled"):
        return
    try:
        import requests
        url = f"https://api.telegram.org/bot{cfg['telegram_token']}/sendMessage"
        requests.post(url, data={
            "chat_id": cfg["telegram_chat_id"],
            "text": f"🔐 Netalyx OTP : *{code}*\nValide 5 minutes.",
            "parse_mode": "Markdown"
        }, timeout=5)
    except Exception as e:
        print(f"[OTP Telegram] Erreur : {e}")

def send_otp(username: str) -> str:
    """Génère et envoie l'OTP. Retourne le code (pour affichage local si aucun canal configuré)."""
    code = generate_otp(username)
    cfg = CFG.get("notifications", {})
    sent = False
    if cfg.get("email_enabled"):
        threading.Thread(target=_send_email, args=(code,), daemon=True).start()
        sent = True
    if cfg.get("telegram_enabled"):
        threading.Thread(target=_send_telegram, args=(code,), daemon=True).start()
        sent = True
    # Si aucun canal configuré, on retourne le code pour l'afficher localement
    return code if not sent else None
