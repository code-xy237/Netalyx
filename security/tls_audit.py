# security/tls_audit.py — Audit de configuration TLS/SSL
import ssl
import socket
from datetime import datetime

WEAK_CIPHERS = {"RC4", "DES", "3DES", "MD5", "NULL", "EXPORT", "anon"}
WEAK_PROTOCOLS = {ssl.PROTOCOL_TLSv1, ssl.PROTOCOL_TLSv1_1} if hasattr(ssl, "PROTOCOL_TLSv1") else set()

def audit_tls(host: str, port: int = 443, timeout: float = 5.0) -> dict:
    """Audit complet TLS : protocole, cipher, certificat, score."""
    result = {
        "host": host, "port": port,
        "tls_version": None, "cipher": None, "cert_cn": None,
        "cert_expiry": None, "cert_expired": False,
        "cert_self_signed": False, "weak_cipher": False,
        "score": "?", "issues": []
    }
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                result["tls_version"] = ssock.version()
                cipher = ssock.cipher()
                result["cipher"] = cipher[0] if cipher else "?"

                cert = ssock.getpeercert()
                if cert:
                    subject = dict(x[0] for x in cert.get("subject", []))
                    issuer  = dict(x[0] for x in cert.get("issuer", []))
                    result["cert_cn"]     = subject.get("commonName", "?")
                    result["cert_expiry"] = cert.get("notAfter", "?")
                    # Expiré ?
                    try:
                        expiry = datetime.strptime(result["cert_expiry"], "%b %d %H:%M:%S %Y %Z")
                        result["cert_expired"] = datetime.utcnow() > expiry
                    except Exception:
                        pass
                    # Auto-signé ?
                    result["cert_self_signed"] = subject == issuer

        # Analyse des problèmes
        ver = result["tls_version"] or ""
        if "TLSv1.0" in ver or "TLSv1.1" in ver or "SSLv3" in ver:
            result["issues"].append(f"Protocole obsolète : {ver}")
        cipher_name = result["cipher"] or ""
        if any(w in cipher_name for w in WEAK_CIPHERS):
            result["weak_cipher"] = True
            result["issues"].append(f"Cipher faible : {cipher_name}")
        if result["cert_expired"]:
            result["issues"].append("Certificat expiré !")
        if result["cert_self_signed"]:
            result["issues"].append("Certificat auto-signé (MITM possible)")

        # Score
        if not result["issues"]:
            result["score"] = "A"
        elif len(result["issues"]) == 1:
            result["score"] = "B"
        elif len(result["issues"]) == 2:
            result["score"] = "C"
        else:
            result["score"] = "F"

    except Exception as e:
        result["issues"].append(f"Connexion impossible : {e}")
        result["score"] = "F"

    return result
