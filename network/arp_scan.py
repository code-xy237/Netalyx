# network/arp_scan.py
import socket
import subprocess
import platform
import logging
from scapy.all import ARP, Ether, srp, conf

logger = logging.getLogger("netalyx.arp")


def arp_scan(ip_range: str, timeout: float = 3.0) -> dict:
    """
    Retourne {ip: mac} pour tous les hôtes actifs sur le réseau.

    Corrections vs version originale :
      1. timeout augmenté à 3s (2s trop court sur Wi-Fi)
      2. retry=2 : Scapy renvoie le paquet 2 fois si pas de réponse
      3. conf.verb = 0 : supprime les warnings Scapy sous Windows
      4. Fallback ARP cache Windows/Linux si Scapy échoue (droits admin)
      5. Détection automatique de l'interface réseau active
    """
    # ── Tentative principale : Scapy ARP broadcast ─────────────────────
    try:
        conf.verb = 0
        ans, _ = srp(
            Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip_range),
            timeout=timeout,
            retry=2,       # renvoie si pas de réponse au premier envoi
            verbose=0
        )
        results = {r.psrc: r.hwsrc for _, r in ans}
        if results:
            logger.info(f"ARP scan : {len(results)} appareil(s) trouvé(s)")
            return results
        # Si résultat vide, on tente le fallback (probablement pas admin)
        logger.warning("ARP scan Scapy : 0 résultat — tentative fallback ARP cache")
    except Exception as e:
        logger.warning(f"ARP scan Scapy échoué ({e}) — tentative fallback")

    # ── Fallback : lecture du cache ARP OS ─────────────────────────────
    return _arp_cache_fallback()


def _arp_cache_fallback() -> dict:
    """
    Lit le cache ARP du système d'exploitation.
    Fonctionne sans droits administrateur, mais ne liste que les
    appareils avec lesquels la machine a déjà communiqué.
    """
    devices = {}
    try:
        system = platform.system()
        if system == "Windows":
            out = subprocess.check_output(["arp", "-a"], timeout=5,
                                          encoding="cp850", errors="replace")
            for line in out.splitlines():
                parts = line.split()
                # Format : "  192.168.1.X    aa-bb-cc-dd-ee-ff   dynamique"
                if len(parts) >= 2 and _is_valid_ip(parts[0]) and "-" in parts[1]:
                    ip  = parts[0]
                    mac = parts[1].replace("-", ":").lower()
                    devices[ip] = mac
        else:  # Linux / macOS
            out = subprocess.check_output(["arp", "-n"], timeout=5,
                                          encoding="utf-8", errors="replace")
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 3 and _is_valid_ip(parts[0]) and ":" in parts[2]:
                    devices[parts[0]] = parts[2].lower()
    except Exception as e:
        logger.error(f"Fallback ARP cache échoué : {e}")

    logger.info(f"ARP cache fallback : {len(devices)} appareil(s)")
    return devices


def _is_valid_ip(s: str) -> bool:
    try:
        parts = s.split(".")
        return len(parts) == 4 and all(0 <= int(p) <= 255 for p in parts)
    except Exception:
        return False
