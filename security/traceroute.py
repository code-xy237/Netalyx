# security/traceroute.py — Traceroute visuel multi-protocoles
import socket
import time
import threading
from scapy.all import IP, ICMP, TCP, UDP, sr1

def traceroute_icmp(target: str, max_hops: int = 20, timeout: float = 2.0) -> list:
    """Traceroute ICMP. Retourne liste de dicts {hop, ip, hostname, rtt_ms}."""
    hops = []
    for ttl in range(1, max_hops + 1):
        pkt  = IP(dst=target, ttl=ttl) / ICMP()
        t0   = time.time()
        resp = sr1(pkt, timeout=timeout, verbose=0)
        rtt  = round((time.time() - t0) * 1000, 1)

        if resp is None:
            hops.append({"hop": ttl, "ip": "*", "hostname": "*", "rtt_ms": None})
            continue

        ip = resp.src
        try:
            hostname = socket.gethostbyaddr(ip)[0]
        except Exception:
            hostname = ip

        hops.append({"hop": ttl, "ip": ip, "hostname": hostname, "rtt_ms": rtt})

        # Destination atteinte : vérifier la couche ICMP (pas resp.type qui est l'EtherType)
        if resp.haslayer(ICMP) and resp[ICMP].type == 0:  # Echo Reply
            break

    return hops


def traceroute_tcp(target: str, dport: int = 80,
                   max_hops: int = 20, timeout: float = 2.0) -> list:
    """Traceroute TCP SYN (traverse mieux les firewalls)."""
    hops = []
    for ttl in range(1, max_hops + 1):
        pkt  = IP(dst=target, ttl=ttl) / TCP(dport=dport, flags="S")
        t0   = time.time()
        resp = sr1(pkt, timeout=timeout, verbose=0)
        rtt  = round((time.time() - t0) * 1000, 1)

        if resp is None:
            hops.append({"hop": ttl, "ip": "*", "hostname": "*", "rtt_ms": None})
            continue

        ip = resp.src
        try:
            hostname = socket.gethostbyaddr(ip)[0]
        except Exception:
            hostname = ip

        hops.append({"hop": ttl, "ip": ip, "hostname": hostname, "rtt_ms": rtt})

        if resp.haslayer(TCP) and resp[TCP].flags in (0x12, 0x14):  # SYN-ACK ou RST
            break

    return hops
