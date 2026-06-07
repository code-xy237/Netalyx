# security/banner_grab.py — Banner grabbing & détection de services
import socket
import ssl
import concurrent.futures

COMMON_BANNERS = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
    80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS",
    3306: "MySQL", 5432: "PostgreSQL", 6379: "Redis",
}

def grab_banner(ip: str, port: int, timeout: float = 2.0) -> dict:
    """Tente de lire la bannière d'un service."""
    result = {"ip": ip, "port": port, "service": COMMON_BANNERS.get(port, "?"), "banner": None, "error": None}
    try:
        if port == 443:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with ctx.wrap_socket(socket.create_connection((ip, port), timeout=timeout)) as s:
                s.send(b"HEAD / HTTP/1.0\r\n\r\n")
                result["banner"] = s.recv(512).decode(errors="replace").strip()
        else:
            with socket.create_connection((ip, port), timeout=timeout) as s:
                try:
                    s.send(b"\r\n")
                    data = s.recv(512).decode(errors="replace").strip()
                    result["banner"] = data if data else "(pas de bannière)"
                except Exception:
                    result["banner"] = "(pas de bannière)"
    except Exception as e:
        result["error"] = str(e)
    return result

def grab_all(ip: str, open_ports: list, max_workers: int = 10) -> list:
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(grab_banner, ip, p): p for p in open_ports}
        return [f.result() for f in concurrent.futures.as_completed(futures)]
