# gui/security_tabs.py — Onglets sécurité : Banner/CVE, TLS, Misconfig, Traceroute, Timeline, Rapport
import tkinter as tk
from tkinter import messagebox, filedialog
import ttkbootstrap as tb
import threading
from gui.components import LogList


def _safe_append(widget, line: str):
    """Appelle LogList.append() depuis n'importe quel thread via after(0,...)."""
    widget.after(0, widget.append, line)

def _safe_clear(widget):
    """Appelle LogList.clear() depuis n'importe quel thread via after(0,...)."""
    widget.after(0, widget.clear)

def _safe_config(widget, **kwargs):
    """Appelle widget.config() depuis n'importe quel thread via after(0,...)."""
    widget.after(0, lambda: widget.config(**kwargs))


class BannerCVETab(tb.Frame):
    """Banner grabbing + CVE lookup sur une IP."""
    def __init__(self, master):
        super().__init__(master, padding=10)
        row = tb.Frame(self)
        row.pack(fill="x", pady=(0, 8))
        tb.Label(row, text="IP cible :").pack(side="left")
        self.ip_entry = tb.Entry(row, width=20)
        self.ip_entry.pack(side="left", padx=8)
        tb.Label(row, text="Ports (virgules) :").pack(side="left")
        self.ports_entry = tb.Entry(row, width=30)
        self.ports_entry.insert(0, "22,80,443,21,25,3306,6379")
        self.ports_entry.pack(side="left", padx=8)
        tb.Button(row, text="Analyser", bootstyle="info",
                  command=self._run).pack(side="left", padx=8)

        self.log = LogList(self, title="Résultats Banner + CVE", height=22,
                           color_map={"CRITICAL": "#ff4444", "HIGH": "#ff8800",
                                      "MEDIUM": "#ffcc00", "CVE": "#00bfff"})
        self.log.pack(fill="both", expand=True)

    def _run(self):
        ip = self.ip_entry.get().strip()
        if not ip:
            return
        try:
            ports = [int(p.strip()) for p in self.ports_entry.get().split(",") if p.strip()]
        except ValueError:
            messagebox.showerror("Erreur", "Ports invalides")
            return
        self.log.append(f"Démarrage banner grabbing sur {ip}:{ports}…")
        threading.Thread(target=self._analyze, args=(ip, ports), daemon=True).start()

    def _analyze(self, ip, ports):
        from security.banner_grab import grab_all
        from security.cve_lookup import enrich_banner
        results = grab_all(ip, ports)
        for r in results:
            banner = r.get("banner") or r.get("error") or "?"
            _safe_append(self.log, f"[{r['port']}/{r['service']}] {banner[:100]}")
            if r.get("banner"):
                enriched = enrich_banner(r["banner"])
                svc = enriched.get("service")
                ver = enriched.get("version")
                if svc:
                    _safe_append(self.log, f"  -> Détecté : {svc} {ver}")
                for cve in enriched.get("cves", []):
                    score    = cve.get("score") or "?"
                    severity = cve.get("severity", "?")
                    _safe_append(self.log, f"  CVE {cve['id']} — Score {score} {severity} — {cve['desc'][:80]}")


class TLSAuditTab(tb.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        row = tb.Frame(self)
        row.pack(fill="x", pady=(0, 8))
        tb.Label(row, text="Hôte :").pack(side="left")
        self.host_entry = tb.Entry(row, width=25)
        self.host_entry.pack(side="left", padx=8)
        tb.Label(row, text="Port :").pack(side="left")
        self.port_entry = tb.Entry(row, width=8)
        self.port_entry.insert(0, "443")
        self.port_entry.pack(side="left", padx=8)
        tb.Button(row, text="Auditer TLS", bootstyle="warning",
                  command=self._run).pack(side="left", padx=8)

        self.log = LogList(self, title="Audit TLS/SSL", height=22,
                           color_map={"F": "#ff4444", "A": "#00cc66",
                                      "expiré": "#ff4444", "auto-signé": "#ff8800",
                                      "faible": "#ff8800"})
        self.log.pack(fill="both", expand=True)

    def _run(self):
        host = self.host_entry.get().strip()
        try:
            port = int(self.port_entry.get())
        except ValueError:
            port = 443
        if not host:
            return
        self.log.append(f"Audit TLS de {host}:{port}…")
        threading.Thread(target=self._audit, args=(host, port), daemon=True).start()

    def _audit(self, host, port):
        from security.tls_audit import audit_tls
        r = audit_tls(host, port)
        _safe_append(self.log, f"Score TLS : {r['score']}")
        _safe_append(self.log, f"Protocole : {r['tls_version']} | Cipher : {r['cipher']}")
        _safe_append(self.log, f"Certificat CN : {r['cert_cn']} | Expiration : {r['cert_expiry']}")
        if r["cert_expired"]:     _safe_append(self.log, "Certificat expiré !")
        if r["cert_self_signed"]: _safe_append(self.log, "Certificat auto-signé (MITM possible)")
        if r["weak_cipher"]:      _safe_append(self.log, "Cipher faible détecté")
        for issue in r["issues"]:
            _safe_append(self.log, f"  Problème : {issue}")
        if not r["issues"]:
            _safe_append(self.log, "Aucun problème TLS détecté")


class MisconfigTab(tb.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        row = tb.Frame(self)
        row.pack(fill="x", pady=(0, 8))
        tb.Label(row, text="IP cible :").pack(side="left")
        self.ip_entry = tb.Entry(row, width=20)
        self.ip_entry.pack(side="left", padx=8)
        tb.Button(row, text="Vérifier misconfigs", bootstyle="danger",
                  command=self._run).pack(side="left", padx=8)

        self.log = LogList(self, title="Détection de services mal configurés", height=22,
                           color_map={"VULNERABLE": "#ff4444", "OK": "#00cc66",
                                      "anonyme": "#ff8800", "ouvert": "#ff8800"})
        self.log.pack(fill="both", expand=True)

    def _run(self):
        ip = self.ip_entry.get().strip()
        if not ip:
            return
        self.log.append(f"Scan de misconfigs sur {ip}...")
        threading.Thread(target=self._check, args=(ip,), daemon=True).start()

    def _check(self, ip):
        from security.misconfig_checker import run_all_checks
        results = run_all_checks(ip)
        for r in results:
            status = "VULNERABLE" if r["vulnerable"] else "OK"
            _safe_append(self.log, f"[{status}] {r['check']} (port {r['port']}) — {r['detail']}")


class TracerouteTab(tb.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        row = tb.Frame(self)
        row.pack(fill="x", pady=(0, 8))
        tb.Label(row, text="Cible :").pack(side="left")
        self.target_entry = tb.Entry(row, width=25)
        self.target_entry.pack(side="left", padx=8)
        self.proto_var = tk.StringVar(value="ICMP")
        tb.Combobox(row, textvariable=self.proto_var,
                    values=["ICMP", "TCP"], width=8).pack(side="left", padx=8)
        tb.Button(row, text="Traceroute", bootstyle="success",
                  command=self._run).pack(side="left", padx=8)

        self.log = LogList(self, title="Traceroute visuel", height=22)
        self.log.pack(fill="both", expand=True)

    def _run(self):
        target = self.target_entry.get().strip()
        if not target:
            return
        proto = self.proto_var.get()
        self.log.append(f"Traceroute {proto} vers {target}...")
        threading.Thread(target=self._trace, args=(target, proto), daemon=True).start()

    def _trace(self, target, proto):
        from security.traceroute import traceroute_icmp, traceroute_tcp
        hops = traceroute_icmp(target) if proto == "ICMP" else traceroute_tcp(target)
        for h in hops:
            rtt = f"{h['rtt_ms']} ms" if h['rtt_ms'] else "timeout"
            _safe_append(self.log, f"  Hop {h['hop']:2d}  {h['ip']:18s}  {h['hostname']:30s}  {rtt}")


class TimelineTab(tb.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        row = tb.Frame(self)
        row.pack(fill="x", pady=(0, 8))
        tb.Label(row, text="Dernières :").pack(side="left")
        self.hours_entry = tb.Entry(row, width=6)
        self.hours_entry.insert(0, "24")
        self.hours_entry.pack(side="left", padx=4)
        tb.Label(row, text="heures | IP filtre :").pack(side="left")
        self.ip_filter = tb.Entry(row, width=18)
        self.ip_filter.pack(side="left", padx=4)
        tb.Label(row, text="Sévérité :").pack(side="left")
        self.sev_var = tk.StringVar(value="Toutes")
        tb.Combobox(row, textvariable=self.sev_var,
                    values=["Toutes", "CRITIQUE", "ELEVE", "INFO"], width=10).pack(side="left", padx=4)
        tb.Button(row, text="Charger", bootstyle="primary",
                  command=self._load).pack(side="left", padx=8)

        self.log = LogList(self, title="Timeline des incidents", height=24,
                           color_map={"CRITIQUE": "#ff4444", "ELEVE": "#ff8800",
                                      "ALERTE": "#ff6666", "APPAREIL": "#66ccff"})
        self.log.pack(fill="both", expand=True)

    def _load(self):
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        from security.incident_timeline import load_timeline, filter_timeline
        try:
            hours = int(self.hours_entry.get())
        except ValueError:
            hours = 24
        events = load_timeline(hours)
        ip  = self.ip_filter.get().strip() or None
        sev = self.sev_var.get()
        if sev != "Toutes":
            events = filter_timeline(events, ip=ip, severity=sev)
        elif ip:
            events = filter_timeline(events, ip=ip)

        _safe_clear(self.log)
        if not events:
            _safe_append(self.log, "Aucun événement trouvé pour ces filtres.")
            return
        from datetime import datetime
        for e in events:
            dt = datetime.utcfromtimestamp(e["time"]).strftime("%d/%m %H:%M:%S")
            _safe_append(self.log,
                f"[{e['severity']:8s}] {dt}  {e['type']:8s}  {e['kind']:22s}  src={e['src']}  {e['detail'][:60]}")


class ReportTab(tb.Frame):
    def __init__(self, master, username: str = "admin"):
        super().__init__(master, padding=10)
        self.username = username
        tb.Label(self, text="Générer un rapport PDF forensique",
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 12))
        tb.Label(self, text="Le rapport inclut : résumé des alertes, top IPs, "
                             "appareils détectés, recommandations.").pack(anchor="w")
        tb.Button(self, text="Exporter le rapport PDF", bootstyle="success",
                  command=self._export, width=30).pack(pady=20, ipady=8)
        self.status = tb.Label(self, text="", bootstyle="secondary")
        self.status.pack()

    def _export(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile="netalyx_rapport.pdf"
        )
        if not path:
            return
        self.status.config(text="Génération en cours...")
        threading.Thread(target=self._generate, args=(path,), daemon=True).start()

    def _generate(self, path):
        from security.report_pdf import generate_report
        from common import CFG
        ok = generate_report(
            output_path=path,
            alerts_log=CFG["logging"]["alerts_log"],
            devices_log=CFG["logging"]["devices_log"],
            username=self.username
        )
        _safe_config(self.status,
                     text=f"Rapport exporté : {path}" if ok else "Erreur génération")
