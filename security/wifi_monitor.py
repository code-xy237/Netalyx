# security/wifi_monitor.py — Surveillance WiFi passive (Evil Twin, SSIDs)
import threading
from collections import defaultdict

class WifiMonitor:
    """
    Écoute les trames 802.11 Beacon en mode passif.
    Détecte les Evil Twin (même SSID, BSSID différent).
    Nécessite une interface en mode monitor (ex: iwconfig wlan0 mode monitor).
    """

    def __init__(self, on_ap_found=None, on_evil_twin=None, iface: str = None):
        self.on_ap_found   = on_ap_found    # callback(ssid, bssid, channel, crypto)
        self.on_evil_twin  = on_evil_twin   # callback(ssid, bssid_original, bssid_fake)
        self.iface         = iface          # None = auto-detect
        self._stop         = threading.Event()
        self._thread       = None
        self._ssid_map     = defaultdict(set)  # {ssid: {bssid1, bssid2, ...}}

    def _on_packet(self, pkt):
        try:
            from scapy.all import Dot11, Dot11Beacon, Dot11Elt
            if not pkt.haslayer(Dot11Beacon):
                return
            bssid = pkt[Dot11].addr3
            ssid  = pkt[Dot11Elt].info.decode(errors="replace") if pkt.haslayer(Dot11Elt) else "?"

            # Chiffrement
            cap     = pkt[Dot11Beacon].cap
            crypto  = "Open"
            if pkt.haslayer(Dot11Elt):
                elt = pkt[Dot11Elt]
                while elt:
                    if elt.ID == 48:
                        crypto = "WPA2"
                        break
                    if elt.ID == 221 and b"\x00P\xf2\x01" in bytes(elt):
                        crypto = "WPA"
                        break
                    elt = elt.payload if hasattr(elt, "payload") else None

            # Nouveau AP
            if bssid not in self._ssid_map[ssid]:
                self._ssid_map[ssid].add(bssid)
                if self.on_ap_found:
                    self.on_ap_found(ssid, bssid, crypto)

            # Evil Twin : même SSID, plusieurs BSSIDs différents
            if len(self._ssid_map[ssid]) > 1 and self.on_evil_twin:
                bssids = list(self._ssid_map[ssid])
                self.on_evil_twin(ssid, bssids[0], bssid)

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
            from scapy.all import sniff
            kwargs = {"prn": self._on_packet, "store": False,
                      "stop_filter": lambda p: self._stop.is_set()}
            if self.iface:
                kwargs["iface"] = self.iface
            sniff(**kwargs)
        except Exception as e:
            print(f"[WifiMonitor] {e}")

    def stop(self):
        self._stop.set()

    def get_aps(self) -> dict:
        return {ssid: list(bssids) for ssid, bssids in self._ssid_map.items()}
