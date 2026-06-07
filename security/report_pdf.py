# security/report_pdf.py — Rapport PDF forensique PRO + Intégration BorIA #4
import json
import os
from datetime import datetime
from fpdf import FPDF


class NetalyxReport(FPDF):
    """PDF forensique Netalyx PRO avec section analyse IA BorIA."""

    def header(self):
        # Bandeau noir
        self.set_fill_color(7, 10, 16)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 14, "  NETALYX PRO  —  Rapport de Sécurité Réseau", fill=True, ln=True)
        # Sous-ligne bleue
        self.set_fill_color(0, 85, 204)
        self.cell(0, 2, "", fill=True, ln=True)
        self.set_text_color(100, 120, 140)
        self.set_font("Helvetica", "", 8)
        self.cell(0, 6, f"  Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}  |  Netalyx PRO v3.0", ln=True)
        self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(80, 100, 120)
        self.cell(0, 8, f"NETALYX PRO  —  Rapport confidentiel  —  Page {self.page_no()}", align="C")

    def section_title(self, title: str, color: tuple = (0, 85, 204)):
        self.set_fill_color(*color)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 10, f"  {title}", fill=True, ln=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def kv_row(self, key: str, value: str, highlight: bool = False):
        if highlight:
            self.set_fill_color(255, 235, 235)
            self.set_text_color(160, 0, 0)
        else:
            self.set_fill_color(240, 244, 248)
            self.set_text_color(30, 40, 50)
        self.set_font("Helvetica", "B", 9)
        self.cell(55, 7, f"  {key}", fill=True, border="B")
        self.set_font("Helvetica", "", 9)
        self.set_fill_color(255, 255, 255)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 7, f"  {value}", fill=True, border="B")

    def ai_box(self, text: str):
        """Encadré violet pour le résumé IA BorIA."""
        self.set_fill_color(30, 10, 50)
        self.set_draw_color(100, 50, 180)
        self.set_text_color(200, 160, 255)
        self.set_font("Helvetica", "B", 9)
        self.cell(0, 8, "  ⚡ Analyse IA BorIA", fill=True, ln=True, border=1)
        self.set_fill_color(245, 240, 255)
        self.set_text_color(50, 20, 80)
        self.set_font("Helvetica", "", 9)
        self.multi_cell(0, 6, f"  {text}", fill=True, border=1)
        self.set_draw_color(0, 0, 0)
        self.set_text_color(0, 0, 0)
        self.ln(4)


def generate_report(output_path: str,
                    alerts_log: str,
                    devices_log: str,
                    username: str = "admin") -> bool:
    try:
        pdf = NetalyxReport()
        pdf.add_page()

        # ── Résumé exécutif ────────────────────────────────────────────
        pdf.section_title("Résumé exécutif")
        pdf.kv_row("Analyste",  username)
        pdf.kv_row("Date",      datetime.now().strftime("%d/%m/%Y %H:%M"))
        pdf.kv_row("Rapport",   "Audit réseau automatisé — Netalyx PRO v3.0")
        pdf.kv_row("Moteur IA", "BorIA AI Engine intégré")
        pdf.ln(4)

        # ── Analyse IA BorIA (Intégration #4) ─────────────────────────
        try:
            from ids.alerts import get_boria_summary, get_session_alerts
            summary = get_boria_summary()
            pdf.section_title("Analyse Intelligente — BorIA", color=(60, 20, 100))
            pdf.ai_box(summary)
        except Exception:
            pass

        # ── Alertes IDS ────────────────────────────────────────────────
        pdf.section_title("Alertes IDS détectées")
        alerts = []
        if os.path.exists(alerts_log):
            with open(alerts_log, encoding="utf-8") as f:
                for line in f:
                    try:
                        alerts.append(json.loads(line.strip()))
                    except Exception:
                        pass

        pdf.kv_row("Total alertes", str(len(alerts)))

        by_kind = {}
        for a in alerts:
            k = a.get("kind", "?")
            by_kind[k] = by_kind.get(k, 0) + 1
        for kind, count in sorted(by_kind.items(), key=lambda x: -x[1]):
            critical = kind in ("CRITICAL_INCIDENT", "IP_BLOCKED")
            expl = ""
            # Ajoute explication BorIA si disponible
            for a in alerts:
                if a.get("kind") == kind and a.get("boria_explication"):
                    expl = f"  [{a['boria_explication'][:80]}]"
                    break
            pdf.kv_row(kind, f"{count} occurrence(s){expl}", highlight=critical)

        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 7, "  Dernières alertes :", ln=True)
        pdf.set_font("Helvetica", "", 8)
        for a in alerts[-12:]:
            t    = a.get("time", "")[:19].replace("T", " ")
            kind = a.get("kind", "?")
            src  = a.get("detail", {}).get("src", "?")
            score = a.get("detail", {}).get("score", "")
            score_txt = f"  score:{score}" if score else ""
            if kind == "CRITICAL_INCIDENT":
                pdf.set_fill_color(255, 235, 235)
            elif kind == "ANOMALY_DETECTED":
                pdf.set_fill_color(255, 245, 220)
            else:
                pdf.set_fill_color(248, 250, 252)
            pdf.cell(0, 6,
                     f"  [{t}]  {kind}  —  src:{src}{score_txt}",
                     fill=True, ln=True)
        pdf.ln(4)

        # ── Appareils détectés ─────────────────────────────────────────
        pdf.section_title("Appareils détectés sur le réseau")
        devices = []
        if os.path.exists(devices_log):
            with open(devices_log, encoding="utf-8") as f:
                for line in f:
                    try:
                        devices.append(json.loads(line.strip()))
                    except Exception:
                        pass

        pdf.kv_row("Total appareils", str(len(devices)))
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 8)
        for col, w in [("IP", 38), ("MAC", 45), ("Hostname", 62), ("Ports ouverts", 0)]:
            pdf.cell(w, 7, f"  {col}", border=1)
        pdf.ln()
        pdf.set_font("Helvetica", "", 8)
        for d in devices[-20:]:
            ports = ", ".join(str(p) for p in d.get("open_ports", [])[:6])
            for val, w in [
                (d.get("ip", "?"),            38),
                (d.get("mac", "?"),           45),
                (d.get("hostname", "?")[:26], 62),
                (ports,                        0),
            ]:
                pdf.cell(w, 6, f"  {val}", border=1)
            pdf.ln()
        pdf.ln(4)

        # ── Statistiques ML ────────────────────────────────────────────
        try:
            from ids.alerts import get_session_alerts
            s_alerts = get_session_alerts()
            anomalies = [a for a in s_alerts if a.get("kind") == "ANOMALY_DETECTED"]
            pdf.section_title("Statistiques Machine Learning", color=(0, 80, 60))
            pdf.kv_row("Total paquets analysés", "—")
            pdf.kv_row("Anomalies ML détectées", str(len(anomalies)))
            pdf.kv_row("Moteur ML",
                       "IsolationForest (sklearn) + BorIA Neural Network (Encog)")
            pdf.ln(3)
        except Exception:
            pass

        # ── Recommandations ────────────────────────────────────────────
        pdf.section_title("Recommandations de sécurité")
        recs = [
            "Mettre à jour les services présentant des CVE identifiés.",
            "Désactiver Telnet, FTP anonyme et SNMP community 'public'.",
            "Vérifier et renouveler les certificats TLS expirés.",
            "Activer le blocage automatique des IPs (AbuseIPDB > 80).",
            "Conserver les journaux au moins 90 jours (forensique).",
            "Activer l'authentification 2FA sur tous les accès administrateurs.",
            "Segmenter le réseau pour isoler les appareils IoT sensibles.",
        ]
        pdf.set_font("Helvetica", "", 9)
        for i, rec in enumerate(recs, 1):
            pdf.cell(0, 7, f"  {i}. {rec}", ln=True)

        pdf.output(output_path)
        return True

    except Exception as e:
        print(f"[Report] Erreur génération PDF : {e}")
        return False
