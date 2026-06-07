# network/arp_scan.py
from scapy.all import ARP, Ether, srp

def arp_scan(ip_range: str, timeout: float = 2.0) -> dict:
    """Retourne {ip: mac} pour tous les hôtes actifs."""
    try:
        ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip_range),
                     timeout=timeout, verbose=0)
        return {r.psrc: r.hwsrc for _, r in ans}
    except Exception:
        return {}
