# sniffer/capture.py
import threading
import time
import json
from queue import Queue
from scapy.all import sniff, wrpcap, rdpcap, IP, TCP, UDP, ICMP
from common import CFG, resource_path

TRAFFIC_LOG = CFG["logging"]["traffic_log"]

class SnifferService:
    """Capture réseau + export/import PCAP."""

    def __init__(self, gui_queue: Queue | None, ids_queue: Queue | None):
        self.gui_queue  = gui_queue
        self.ids_queue  = ids_queue
        self._stop      = threading.Event()
        self._thread    = None
        self._captured  = []   # pour export PCAP

    def _log(self, line: str):
        try:
            with open(TRAFFIC_LOG, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def _on_packet(self, pkt):
        try:
            if IP not in pkt:
                return
            src = pkt[IP].src
            dst = pkt[IP].dst
            if TCP in pkt:
                l4, sport, dport = "TCP", int(pkt[TCP].sport), int(pkt[TCP].dport)
                flags = int(pkt[TCP].flags)
            elif UDP in pkt:
                l4, sport, dport = "UDP", int(pkt[UDP].sport), int(pkt[UDP].dport)
                flags = 0
            elif ICMP in pkt:
                l4, sport, dport, flags = "ICMP", None, None, 0
            else:
                l4, sport, dport, flags = str(pkt[IP].proto), None, None, 0

            rec = {"time": time.time(), "src": src, "dst": dst,
                   "proto": l4, "sport": sport, "dport": dport, "flags": flags}

            self._captured.append(pkt)
            if self.gui_queue: self.gui_queue.put(rec)
            if self.ids_queue: self.ids_queue.put(rec)
            self._log(json.dumps(rec, ensure_ascii=False))
        except Exception:
            pass

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            sniff(prn=self._on_packet, store=False, stop_filter=lambda p: self._stop.is_set())
        except Exception:
            pass

    def stop(self):
        self._stop.set()

    def export_pcap(self, filepath: str) -> bool:
        """Exporte les paquets capturés au format .pcap (compatible Wireshark)."""
        try:
            if not self._captured:
                return False
            wrpcap(filepath, self._captured)
            return True
        except Exception:
            return False

    def load_pcap(self, filepath: str, ids_queue: Queue | None = None) -> int:
        """Charge un fichier .pcap et rejoue les paquets dans l'IDS pour analyse offline."""
        try:
            pkts = rdpcap(filepath)
            count = 0
            for pkt in pkts:
                self._on_packet(pkt)
                count += 1
            return count
        except Exception:
            return 0
