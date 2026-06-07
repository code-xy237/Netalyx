# INTEGRATION_GUIDE.md — Comment activer Netalyx v3.0

## ✅ Activation en 1 ligne

Dans le fichier `gui/dashboard.py`, ajouter ces 3 lignes **à la fin** du fichier,
après la définition de la classe `Dashboard` :

```python
# ── Activation Netalyx v3.0 (voix + gestes + 3D) ──────────────────────────
from gui.dashboard_v3 import patch_dashboard
Dashboard = patch_dashboard(Dashboard)
```

C'est tout. Le patch est non-destructif et s'applique en overlay.

---

## 📁 Nouveaux fichiers créés

```
NETALYX/
├── bridge/
│   ├── __init__.py
│   ├── ws_server.py          ← Serveur WebSocket async
│   └── event_adapter.py      ← Adaptateur réseau + dispatcher commandes
├── voice/
│   ├── __init__.py
│   └── engine.py             ← Reconnaissance vocale + TTS
├── gesture/
│   ├── __init__.py
│   └── engine.py             ← MediaPipe Hands + gestes
├── gui/
│   ├── voice_panel.py        ← Panneau Tkinter voix
│   ├── gesture_panel.py      ← Panneau Tkinter gestes
│   ├── graph3d_tab.py        ← Onglet 3D (WebView ou navigateur)
│   └── dashboard_v3.py       ← Patch dashboard
├── static/
│   └── 3d/
│       └── netalyx3d.html    ← Scène 3D Three.js complète
├── netalyx_core.py           ← Orchestrateur central
├── requirements_v3.txt       ← Nouvelles dépendances
└── install_v3.py             ← Script d'installation
```

---

## 🎙 Commandes vocales disponibles

| Phrase dite         | Action                        |
|---------------------|-------------------------------|
| "Reset"             | Vider le graphe réseau        |
| "Zoom"              | Zoom avant sur la scène 3D    |
| "Bloquer [IP]"      | Bloquer une IP via pare-feu   |
| "Suspect [IP]"      | Marquer une IP comme suspecte |
| "Alertes"           | Afficher les alertes IDS      |
| "Stats"             | Panneau statistiques          |
| "Rafraîchir"        | Actualiser les données        |
| "Rotation"          | Activer la rotation auto      |

---

## ✋ Gestes supportés

| Geste               | Action 3D                     |
|---------------------|-------------------------------|
| Pinch (pouce+index) | Zoom scène 3D                 |
| Pointage (index)    | Sélectionner un nœud réseau   |
| Main ouverte (5)    | Réinitialiser la vue caméra   |
| Swipe gauche        | Rotation gauche               |
| Swipe droite        | Rotation droite               |
| Swipe haut          | Actualiser données            |

---

## 🌐 Architecture WebSocket

```
Python Backend                    Frontend 3D (Three.js)
─────────────────                 ──────────────────────
NetworkGraph.snapshot() ─────────► updateGraph(payload)
IDSService alerts ───────────────► addAlert(payload)
VoiceEngine.speak() ─────────────► setVoiceSpeaking(...)
GestureEngine landmarks ─────────► renderHandCursor(...)
                        ws://8765
Frontend actions ◄───────────────── markSuspect / blockIP
                  ◄───────────────── toggle_voice
                  ◄───────────────── clear_graph
```

---

## 🚀 Installation

```bash
# Option 1 : script automatique
python install_v3.py

# Option 2 : manuel
pip install websockets SpeechRecognition pyttsx3 pyaudio opencv-python mediapipe tkinterweb
```

---

## 📝 Notes

- La vue 3D fonctionne **même sans tkinterweb** : elle s'ouvre dans le navigateur par défaut
- La voix fonctionne **même sans micro** : un stub silencieux est utilisé
- Les gestes fonctionnent **même sans webcam** : le moteur est désactivé gracieusement
- Le bridge WebSocket se reconnecte automatiquement toutes les 3s côté frontend
