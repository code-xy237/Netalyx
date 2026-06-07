# network/port_scanner.py — scan TCP + UDP
import socket
from scapy.all import IP, UDP, ICMP, sr1

def scan_ports(ip: str, ports: list, timeout: float = 0.5) -> list:
    """Scan TCP connect rapide."""
    open_ports = []
    for port in ports:
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                open_ports.append(port)
        except Exception:
            pass
    return open_ports

def scan_udp_ports(ip: str, ports: list, timeout: float = 1.0) -> list:
    """Scan UDP via Scapy — détecte les ports ouverts/filtrés."""
    open_ports = []
    for port in ports:
        try:
            pkt = IP(dst=ip) / UDP(dport=port)
            resp = sr1(pkt, timeout=timeout, verbose=0)
            if resp is None:
                open_ports.append(port)  # pas de réponse = probablement ouvert/filtré
            elif resp.haslayer(ICMP):
                icmp = resp.getlayer(ICMP)
                if int(icmp.type) != 3 or int(icmp.code) != 3:
                    open_ports.append(port)
        except Exception:
            pass
    return open_ports
