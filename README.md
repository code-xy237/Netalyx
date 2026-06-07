# Netalyx v2.0 — Network Security Monitor

Projet Python complet : **Sniffer + IDS avancé + Threat Intelligence + Audit de sécurité + Interface graphique moderne**.

> ⚠️ **Droits administrateur nécessaires** pour la capture réseau (Scapy).
> Windows : lancer en tant qu'Administrateur. Linux : `sudo python main.py`

---

## Fonctionnalités

### Surveillance temps réel
- Capture réseau (Scapy) avec export/import `.pcap` (compatible Wireshark)
- IDS avec cooldown, corrélation d'incidents et détection SYN scan
- Blocage IP automatique via `iptables` (Linux) / `netsh` (Windows)
- Détection de nouveaux appareils sur le réseau (ARP scan)
- OS Fingerprinting passif (TTL + fenêtre TCP, sans envoyer de paquets)
- Graphique temps réel Paquets/minute

### Sécurité & Audit
- **Banner Grabbing** : identification des services et versions sur chaque port
- **CVE Lookup** : corrélation automatique avec la base NVD (gratuite, sans clé)
- **Audit TLS/SSL** : protocole, cipher, certificat, score A/B/C/F
- **Misconfig Checker** : FTP anonyme, Redis sans auth, Telnet, SNMP public…
- **Scan de ports UDP** (DNS, SNMP, NTP, TFTP…)
- **Traceroute visuel** ICMP et TCP

### Threat Intelligence
- Enrichissement IP via **AbuseIPDB** et **VirusTotal** (clés API optionnelles)
- Score de réputation automatique : PROPRE / FAIBLE / SUSPECT / CRITIQUE

### Analyse & Forensique
- **Timeline d'incidents** multi-logs avec filtres (IP, type, sévérité)
- **Export PDF** : rapport forensique complet avec recommandations
- **Surveillance WiFi passive** : détection Evil Twin (nécessite interface monitor)

### Notifications
- **Notifications bureau** natives (plyer, cross-platform)
- **Alertes email** (SMTP configurable)
- **Alertes Telegram** (Bot API)

### Authentification
- Signup/Login avec hash salé (`secrets` + `sha256`)
- OTP 6 chiffres avec expiration 5 min, envoyé par email ou Telegram
- Validation des entrées (longueur, caractères autorisés)

---

## Installation

```bash
python -m venv venv
# Windows : venv\Scripts\activate
# Linux/Mac : source venv/bin/activate

pip install -r requirements.txt
sudo python main.py   # Linux
# Windows : lancer en tant qu'Administrateur
```

## Configuration

Éditer `config.json` ou utiliser le panneau **Paramètres** dans l'interface :
- Plage IP à surveiller
- Seuils IDS (packet rate, SYN scan, port probing, cooldown)
- Clés API (AbuseIPDB, VirusTotal)
- Email SMTP et/ou Telegram Bot pour les notifications
- Profils prédéfinis (domestique / bureau / serveur)
- Blocage IP automatique

## Compilation en .exe (Windows)

```bash
python -m PyInstaller --onefile --windowed --icon=tache.ico \
  --add-data "tache.ico;." \
  --add-data "assets/fond_2.png;assets" \
  --add-data "assets/fond_1.jpeg;assets" \
  --add-data "assets/logo-2.png;assets" \
  --add-data "config.json;." \
  main.py
```

## Structure du projet

```
Netalyx/
├── main.py                  # Point d'entrée
├── common.py                # resource_path + config partagés
├── config.json              # Configuration globale
├── requirements.txt
├── auth/                    # Authentification (login, signup, OTP)
├── gui/
│   ├── dashboard.py         # Dashboard principal (7 onglets)
│   ├── components.py        # StatCard, Carousel, LogList
│   ├── settings_panel.py    # Panneau de configuration
│   └── security_tabs.py     # Onglets Banner/CVE, TLS, Misconfig, Traceroute, Timeline, Rapport
├── ids/                     # IDS (règles, détecteur, alertes)
├── sniffer/                 # Capture réseau + fingerprinting
├── network/                 # ARP scan, port scanner TCP+UDP
└── security/                # Modules de sécurité avancés
    ├── banner_grab.py        # Banner grabbing multi-ports
    ├── cve_lookup.py         # Corrélation CVE via NVD API
    ├── tls_audit.py          # Audit TLS/SSL complet
    ├── misconfig_checker.py  # Détection services mal configurés
    ├── traceroute.py         # Traceroute ICMP + TCP
    ├── os_fingerprint.py     # OS fingerprinting passif
    ├── threat_intel.py       # AbuseIPDB + VirusTotal
    ├── notifier.py           # Desktop + Email + Telegram
    ├── report_pdf.py         # Génération rapport PDF
    ├── incident_timeline.py  # Timeline multi-logs
    └── wifi_monitor.py       # Surveillance WiFi passive (Evil Twin)
```

---

## ML IDS — Détection d'anomalies par Machine Learning

### Fonctionnement en 2 phases

**Phase 1 — Apprentissage** (5–15 min recommandées)
1. Ouvre l'onglet **🧬 ML IDS**
2. Clique **Démarrer l'apprentissage**
3. Utilise ton réseau normalement (navigation, streaming, etc.)
4. Clique **Arrêter & Entraîner** — le modèle Isolation Forest s'entraîne

**Phase 2 — Détection**
- Clique **Activer la détection ML**
- Chaque paquet est désormais scoré en temps réel
- Tout comportement statistiquement anormal déclenche `ANOMALY_DETECTED`
- Le modèle est sauvegardé dans `logs/ml_model.joblib` et rechargé automatiquement au démarrage

### Features analysées par le modèle (14 dimensions)
- Protocole, ports source/destination, ports sensibles
- Débit de paquets par IP (fenêtre 10 secondes)
- Diversité des ports visités (fenêtre 30 secondes)
- Heure normalisée, flags TCP (SYN scan, RST)
- Nature des IPs (privée/publique)

### Paramètre contamination
- **5%** (défaut) : adapté à un réseau domestique propre
- **10–15%** : si tu vois déjà du trafic suspect pendant l'apprentissage
- **1–2%** : réseau très contrôlé (serveur isolé)
