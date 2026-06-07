# network/monitor.py
import json, time, threading, socket
from network.arp_scan import arp_scan
from network.port_scanner import scan_ports
from common import CFG

DEVICES_LOG = CFG["logging"]["devices_log"]

class NetworkMonitor:
    def __init__(self, ip_range: str, ports: list, on_new_device):
        self.ip_range      = ip_range
        self.ports         = ports
        self.on_new_device = on_new_device
        self._known        = set()
        self._stop         = threading.Event()
        self._thread       = None

    def _log(self, line: str):
        with open(DEVICES_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while not self._stop.is_set():
            try:
                devices = arp_scan(self.ip_range)
                new_ips = set(devices.keys()) - self._known
                for ip in new_ips:
                    mac        = devices.get(ip)
                    open_ports = scan_ports(ip, self.ports)
                    try:
                        hostname = socket.gethostbyaddr(ip)[0]
                    except Exception:
                        hostname = "Inconnu"
                    self._log(json.dumps({
                        "ip": ip, "mac": mac, "hostname": hostname,
                        "open_ports": open_ports, "time": time.time()
                    }))
                    self.on_new_device(ip, mac, open_ports, hostname)
                self._known = set(devices.keys())
            except Exception:
                pass
            time.sleep(2)

    def stop(self):
        self._stop.set()
