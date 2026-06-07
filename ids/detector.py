# ids/detector.py — IDS avec cooldown, corrélation, blocage IP
import time
import platform
import subprocess
from collections import defaultdict, deque
from queue import Queue, Empty
from ids.rules import IDSConfig
from ids.alerts import log_alert

class IDSService:
    def __init__(self, packet_queue: Queue, alert_sink):
        self.packet_queue   = packet_queue
        self.alert_sink     = alert_sink
        self._running       = False
        self.by_src_times   = defaultdict(deque)
        self.by_src_ports   = defaultdict(set)
        self._cooldowns     = {}       # {(src, kind): last_alert_time}
        self._incidents     = defaultdict(list)  # corrélation par IP
        self.blocked_ips    = set()

    # ------------------------------------------------------------------ #
    def start(self):  self._running = True
    def stop(self):   self._running = False

    # ------------------------------------------------------------------ #
    def _can_alert(self, src: str, kind: str) -> bool:
        """Cooldown par (IP, type) pour éviter le flood d'alertes."""
        key = (src, kind)
        now = time.time()
        last = self._cooldowns.get(key, 0)
        if now - last >= IDSConfig.alert_cooldown_seconds:
            self._cooldowns[key] = now
            return True
        return False

    def _fire(self, kind: str, detail: dict):
        src = detail.get("src", "?")
        if self._can_alert(src, kind):
            log_alert(kind, detail)
            self.alert_sink(kind, detail)
            # Corrélation : enregistrer l'événement par IP
            self._incidents[src].append({"kind": kind, "time": time.time()})
            self._check_incident_severity(src)

    def _check_incident_severity(self, src: str):
        """Si une IP cumule 3 types d'alertes différents → INCIDENT CRITIQUE."""
        events = self._incidents[src]
        recent = [e for e in events if time.time() - e["time"] < 120]
        kinds  = {e["kind"] for e in recent}
        if len(kinds) >= 3 and self._can_alert(src, "CRITICAL_INCIDENT"):
            detail = {"src": src, "alert_types": list(kinds), "count": len(recent)}
            log_alert("CRITICAL_INCIDENT", detail)
            self.alert_sink("CRITICAL_INCIDENT", detail)

    # ------------------------------------------------------------------ #
    def block_ip(self, ip: str) -> bool:
        """Bloque une IP via iptables (Linux) ou netsh (Windows)."""
        if ip in self.blocked_ips:
            return False
        try:
            system = platform.system()
            if system == "Linux":
                subprocess.run(["iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"], check=True)
            elif system == "Windows":
                subprocess.run([
                    "netsh", "advfirewall", "firewall", "add", "rule",
                    f"name=Netalyx_Block_{ip}", "dir=in", "action=block",
                    f"remoteip={ip}"
                ], check=True)
            self.blocked_ips.add(ip)
            log_alert("IP_BLOCKED", {"ip": ip, "system": system})
            return True
        except Exception as e:
            log_alert("BLOCK_FAILED", {"ip": ip, "error": str(e)})
            return False

    def unblock_ip(self, ip: str) -> bool:
        try:
            system = platform.system()
            if system == "Linux":
                subprocess.run(["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"], check=True)
            elif system == "Windows":
                subprocess.run([
                    "netsh", "advfirewall", "firewall", "delete", "rule",
                    f"name=Netalyx_Block_{ip}"
                ], check=True)
            self.blocked_ips.discard(ip)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    def poll(self):
        if not self._running:
            return
        tnow = time.time()
        try:
            while True:
                rec  = self.packet_queue.get_nowait()
                src  = rec.get("src")
                dport = rec.get("dport")
                flags = rec.get("flags", 0)

                # -- Débit de paquets --
                self.by_src_times[src].append(rec["time"])
                dq = self.by_src_times[src]
                while dq and (tnow - dq[0]) > IDSConfig.burst_window_seconds:
                    dq.popleft()
                if len(dq) >= IDSConfig.packet_rate_threshold:
                    self._fire("HIGH_PACKET_RATE", {
                        "src": src, "rate_window_s": IDSConfig.burst_window_seconds, "count": len(dq)
                    })

                # -- SYN Scan (flag SYN seul, pas ACK) --
                if flags and (flags & 0x02) and not (flags & 0x10):
                    syn_count = sum(1 for t in dq if tnow - t < IDSConfig.burst_window_seconds)
                    if syn_count >= IDSConfig.syn_scan_threshold:
                        self._fire("SYN_SCAN", {"src": src, "syn_count": syn_count})

                # -- Port probing --
                if dport:
                    self.by_src_ports[src].add(dport)
                    if len(self.by_src_ports[src]) >= IDSConfig.port_probe_threshold:
                        self._fire("PORT_PROBING", {
                            "src": src, "distinct_ports": len(self.by_src_ports[src])
                        })
        except Empty:
            pass
