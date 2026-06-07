# security/os_fingerprint.py — OS fingerprinting passif (analyse TTL + fenêtre TCP)
from scapy.all import IP, TCP

# TTL initiaux typiques par OS
TTL_MAP = [
    (64,  ["Linux", "Android", "FreeBSD"]),
    (128, ["Windows"]),
    (255, ["Cisco IOS", "macOS (récent)", "OpenBSD"]),
    (60,  ["macOS (ancien)"]),
    (32,  ["Windows 9x (ancien)"]),
]

# Tailles de fenêtre TCP caractéristiques
WINDOW_MAP = {
    65535: "Windows XP/Vista",
    8192:  "Windows 7/8",
    64240: "Windows 10/11",
    29200: "Linux (récent)",
    65340: "macOS",
    5840:  "Linux (ancien)",
}

def guess_os_from_ttl(ttl: int) -> str:
    """Devine l'OS depuis le TTL observé (sans envoyer de paquets)."""
    for threshold, candidates in sorted(TTL_MAP, key=lambda x: x[0]):
        if ttl <= threshold:
            return " / ".join(candidates)
    return f"Inconnu (TTL={ttl})"

def guess_os_from_window(window: int) -> str:
    return WINDOW_MAP.get(window, f"Inconnu (win={window})")

def fingerprint_packet(pkt) -> dict | None:
    """Extrait les indices OS depuis un paquet Scapy."""
    if IP not in pkt:
        return None
    result = {
        "src":     pkt[IP].src,
        "ttl":     pkt[IP].ttl,
        "os_ttl":  guess_os_from_ttl(pkt[IP].ttl),
        "os_win":  None,
        "window":  None,
    }
    if TCP in pkt:
        result["window"] = pkt[TCP].window
        result["os_win"] = guess_os_from_window(pkt[TCP].window)
    return result

class OSFingerprintCache:
    """Accumule les fingerprints par IP source pour affichage dans le dashboard."""
    def __init__(self):
        self._data = {}

    def update(self, pkt):
        fp = fingerprint_packet(pkt)
        if fp:
            self._data[fp["src"]] = fp

    def get_all(self) -> dict:
        return dict(self._data)

    def get(self, ip: str) -> dict | None:
        return self._data.get(ip)
