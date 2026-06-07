# auth/utils.py
import os
import sqlite3
import hashlib
import secrets
import re
from datetime import datetime, timedelta
from common import resource_path

DB_PATH = os.path.join("auth", "users.db")

def get_db_path():
    return DB_PATH

def ensure_db():
    os.makedirs("auth", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS otps(
            username TEXT PRIMARY KEY,
            code TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
    """)
    con.commit()
    con.close()

def validate_credentials(username: str, password: str) -> str | None:
    """Retourne un message d'erreur ou None si valide."""
    if not username or len(username.strip()) < 3:
        return "Le nom d'utilisateur doit contenir au moins 3 caractères."
    if not re.match(r'^[a-zA-Z0-9_\-]+$', username):
        return "Nom d'utilisateur : lettres, chiffres, _ et - uniquement."
    if len(password) < 8:
        return "Le mot de passe doit contenir au moins 8 caractères."
    return None

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${h}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, h = stored_hash.split("$", 1)
        return hashlib.sha256((salt + password).encode()).hexdigest() == h
    except Exception:
        return False

def create_user(username: str, password: str) -> bool:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    try:
        cur.execute(
            "INSERT INTO users(username, password_hash, created_at) VALUES(?,?,?)",
            (username, hash_password(password), datetime.utcnow().isoformat())
        )
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        con.close()

def get_user(username: str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT username, password_hash FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    con.close()
    return row

def set_otp(username: str, code: str, ttl_seconds: int = 300):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    expires = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
    cur.execute("REPLACE INTO otps(username, code, expires_at) VALUES(?,?,?)", (username, code, expires))
    con.commit()
    con.close()

def verify_otp(username: str, code: str) -> bool:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT code, expires_at FROM otps WHERE username = ?", (username,))
    row = cur.fetchone()
    con.close()
    if not row:
        return False
    stored_code, expires_at = row
    try:
        if datetime.utcnow() > datetime.fromisoformat(expires_at):
            return False
    except Exception:
        return False
    return secrets.compare_digest(stored_code, code)

def authenticate_user(username: str, password: str) -> bool:
    user = get_user(username)
    if not user:
        return False
    _, stored_hash = user
    return verify_password(password, stored_hash)
