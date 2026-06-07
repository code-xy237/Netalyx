# sniffer/analyzer.py — OS fingerprinting passif + reconstruction TCP
from collections import deque, defaultdict

class RecentPackets:
    def __init__(self, maxlen=500):
        self._q = deque(maxlen=maxlen)

    def push(self, rec): self._q.appendleft(rec)
    def all(self): return list(self._q)


# ── OS Fingerprinting passif ──────────────────────────────────────────────────
# Basé sur TTL initial et taille de fenêtre TCP (heuristique p0f-like)
OS_TTL_MAP = [
    (64,  "Linux / Android"),
    (128, "Windows"),
    (255, "Cisco / BSD / macOS"),
    (60,  "macOS (old)"),
]

def guess_os(ttl: int, window_size: int = None) -> str:
    """Devine l'OS à partir du TTL observé (sans envoyer de paquets)."""
    # Le TTL décroît en transit — on cherche la valeur initiale probable
    for threshold, name in sorted(OS_TTL_MAP, key=lambda x: x[0]):
        if ttl <= threshold:
            return name
    return f"Inconnu (TTL={ttl})"


# ── Reconstruction de sessions TCP ───────────────────────────────────────────
class TCPSessionRebuilder:
    """Réassemble les flux TCP par (src_ip, src_port, dst_ip, dst_port)."""

    def __init__(self):
        self._sessions = defaultdict(lambda: {"data": [], "seq": None})

    def feed(self, rec: dict, payload: bytes = b""):
        if rec.get("proto") != "TCP":
            return
        key = (rec["src"], rec.get("sport"), rec["dst"], rec.get("dport"))
        self._sessions[key]["data"].append(payload)

    def get_session(self, src, sport, dst, dport) -> bytes:
        key = (src, sport, dst, dport)
        return b"".join(self._sessions.get(key, {}).get("data", []))

    def sessions_summary(self) -> list:
        return [
            {"src": k[0], "sport": k[1], "dst": k[2], "dport": k[3],
             "bytes": sum(len(d) for d in v["data"])}
            for k, v in self._sessions.items()
        ]
