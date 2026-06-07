# Netalyx PRO v3.0 — Guide de démarrage

## Ce qui a été refait

### Interface complète
- **Splash screen animé** avec barre de progression et fade-in/fade-out
- **Topbar professionnelle** avec horloge temps réel et badge BorIA
- **KPI Bar statique** (4 cartes : paquets, alertes, appareils, score ML)
- **Pages Login / Signup** entièrement redessinées (dark pro, boutons animés)
- **Logs** avec toolbar Vider, limitation 500 lignes, coloration BorIA en violet
- **Graphique** avec palette dark cohérente
- **Onglet BorIA Chat** dédié au chatbot IA dans le dashboard

### Intégrations BorIA (4)
| # | Fichier | Ce que ça fait |
|---|---------|----------------|
| 1 | `security/ml_ids.py` | Vote combiné IsolationForest + score BorIA |
| 2 | `gui/voice_panel.py` | Toute commande vocale → réponse BorIA + TTS |
| 3 | `ids/alerts.py` | Chaque alerte → explication textuelle BorIA |
| 4 | `security/report_pdf.py` | Résumé IA dans le PDF + encadré violet |

### Nouveau fichier
- `boria_bridge.py` — pont REST Python ↔ BorIA, dégradation gracieuse

---

## Installation

```bash
pip install -r requirements.txt
```

## Lancement

```bash
python main.py
```

## Avec BorIA (optionnel)

1. Compilez BorIA : `mvn clean package` dans le dossier `boria/`
2. Copiez `boria-ai-1.0.0.jar` dans un dossier `boria/` à côté de `main.py`
3. Lancez Netalyx normalement — BorIA démarre automatiquement

Sans BorIA : tout fonctionne, les features IA affichent un fallback texte.

## Structure des fichiers modifiés

```
main.py               ← Splash screen PRO + launch maximisé
boria_bridge.py       ← NOUVEAU — pont BorIA REST
gui/dashboard.py      ← Topbar + notebook 11 onglets + BorIA Chat
gui/components.py     ← KPIBar, LogList PRO, BorIAStatusBadge
auth/login.py         ← UI dark professionnelle
auth/signup.py        ← UI dark professionnelle
ids/alerts.py         ← Enrichissement BorIA #3
security/ml_ids.py    ← Vote IsolationForest + BorIA #1
security/report_pdf.py← Section IA + encadré BorIA #4
gui/voice_panel.py    ← BorIA répond aux commandes vocales #2
requirements.txt      ← Dépendances complètes
```
