# network/monitor.py
import json
import time
import threading
import socket
import logging
from network.arp_scan import arp_scan
from network.port_scanner import scan_ports
from common import CFG

logger = logging.getLogger("netalyx.monitor")
DEVICES_LOG = CFG["logging"]["devices_log"]


class NetworkMonitor:
    """
    Scan périodique du réseau local par ARP.

    Corrections vs version originale :
      1. Exception dans _run avalée silencieusement → remplacée par log
      2. interval configurable (défaut 30s au lieu de 2s)
         → 2s = spam ARP toutes les 2s sur le réseau, inutile et bruyant
      3. Scan initial au démarrage (au lieu d'attendre le premier sleep)
      4. on_new_device appelé via after() déjà géré côté dashboard ;
         ici on s'assure de ne jamais lever d'exception depuis le thread
      5. Appel port_scanner uniquement si nécessaire (avec timeout réduit)
    """

    def __init__(self, ip_range: str, ports: list, on_new_device,
                 interval: int = 30):
        self.ip_range      = ip_range
        self.ports         = ports
        self.on_new_device = on_new_device
        self.interval      = interval   # secondes entre deux scans
        self._known        = {}         # {ip: mac} — appareils déjà vus
        self._stop         = threading.Event()
        self._thread       = None

    def _log(self, line: str):
        try:
            with open(DEVICES_LOG, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            logger.warning(f"Impossible d'écrire devices_log : {e}")

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run,
                                        daemon=True, name="NetMonitor")
        self._thread.start()
        logger.info(f"NetworkMonitor démarré (plage={self.ip_range}, intervalle={self.interval}s)")

    def _run(self):
        # Scan immédiat au démarrage — ne pas attendre interval secondes
        self._do_scan()
        while not self._stop.wait(timeout=self.interval):
            self._do_scan()

    def _do_scan(self):
        try:
            devices = arp_scan(self.ip_range)
        except Exception as e:
            logger.error(f"ARP scan exception : {e}")
            return

        if not devices:
            logger.debug("Aucun appareil détecté (réseau vide ou droits insuffisants)")
            return

        new_ips = set(devices.keys()) - set(self._known.keys())
        logger.debug(f"Scan : {len(devices)} appareil(s), {len(new_ips)} nouveau(x)")

        for ip in new_ips:
            mac = devices.get(ip, "??:??:??:??:??:??")
            try:
                open_ports = scan_ports(ip, self.ports, timeout=0.4)
            except Exception as e:
                logger.warning(f"Port scan {ip} échoué : {e}")
                open_ports = []
            try:
                hostname = socket.gethostbyaddr(ip)[0]
            except Exception:
                hostname = "Inconnu"

            self._log(json.dumps({
                "ip": ip, "mac": mac, "hostname": hostname,
                "open_ports": open_ports, "time": time.time()
            }))

            try:
                self.on_new_device(ip, mac, open_ports, hostname)
            except Exception as e:
                logger.error(f"on_new_device callback erreur : {e}")

        # Mise à jour de la liste connue (y compris les appareils qui disparaissent)
        self._known = dict(devices)

    def stop(self):
        self._stop.set()
        logger.info("NetworkMonitor arrêté")

    def get_known_devices(self) -> dict:
        """Retourne le dernier snapshot {ip: mac} des appareils connus."""
        return dict(self._known)
