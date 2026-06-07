# security/misconfig_checker.py — Détection de services mal configurés
import socket
import ftplib
import threading
import concurrent.futures

CHECKS = []

def _check(name, port):
    def decorator(fn):
        CHECKS.append({"name": name, "port": port, "fn": fn})
        return fn
    return decorator

@_check("FTP anonyme", 21)
def _ftp_anon(ip):
    try:
        ftp = ftplib.FTP(timeout=3)
        ftp.connect(ip, 21)
        ftp.login("anonymous", "test@test.com")
        ftp.quit()
        return True, "Login anonyme accepté"
    except ftplib.error_perm:
        return False, "Refusé"
    except Exception as e:
        return None, str(e)

@_check("Telnet ouvert", 23)
def _telnet(ip):
    try:
        with socket.create_connection((ip, 23), timeout=2):
            return True, "Port Telnet ouvert (protocole non chiffré)"
    except Exception:
        return False, "Fermé"

@_check("Redis sans auth", 6379)
def _redis(ip):
    try:
        with socket.create_connection((ip, 6379), timeout=2) as s:
            s.send(b"PING\r\n")
            r = s.recv(64)
            if b"+PONG" in r:
                return True, "Redis répond sans authentification"
    except Exception:
        pass
    return False, "Non accessible"

@_check("MongoDB sans auth", 27017)
def _mongo(ip):
    try:
        with socket.create_connection((ip, 27017), timeout=2):
            return True, "Port MongoDB ouvert (vérifier l'auth manuellement)"
    except Exception:
        return False, "Fermé"

@_check("SNMP community 'public'", 161)
def _snmp(ip):
    try:
        from scapy.all import IP, UDP, SNMP, SNMPget, SNMPvarbind, ASN1_OID, sr1
        pkt = IP(dst=ip)/UDP(dport=161)/SNMP(
            community=b"public",
            PDU=SNMPget(varbindlist=[SNMPvarbind(oid=ASN1_OID("1.3.6.1.2.1.1.1.0"))])
        )
        resp = sr1(pkt, timeout=2, verbose=0)
        if resp and resp.haslayer(SNMP):
            return True, "SNMP community 'public' acceptée"
    except Exception:
        pass
    return False, "Non accessible ou sécurisé"

@_check("HTTP Basic Auth désactivée", 80)
def _http_no_auth(ip):
    try:
        with socket.create_connection((ip, 80), timeout=2) as s:
            s.send(b"GET / HTTP/1.0\r\nHost: " + ip.encode() + b"\r\n\r\n")
            resp = s.recv(512).decode(errors="replace")
            if "200 OK" in resp:
                return True, "HTTP répond 200 sans authentification"
    except Exception:
        pass
    return False, "Non concerné"

def run_all_checks(ip: str) -> list:
    """Lance tous les checks en parallèle et retourne les résultats."""
    results = []

    def _run(check):
        vulnerable, detail = False, "Erreur"
        try:
            res = check["fn"](ip)
            if res is not None:
                vulnerable, detail = res[0], res[1]
        except Exception as e:
            detail = str(e)
        return {
            "check":      check["name"],
            "port":       check["port"],
            "vulnerable": vulnerable,
            "detail":     detail
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        futures = [ex.submit(_run, c) for c in CHECKS]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    return sorted(results, key=lambda x: (not x["vulnerable"], x["port"]))
