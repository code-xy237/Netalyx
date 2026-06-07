#!/usr/bin/env python3
# install_v3.py — Script d'installation Netalyx v3.0 (voix + gestes + 3D)
# Exécuter : python install_v3.py

import subprocess
import sys
import os

def run(cmd, label):
    print(f"\n{'─'*50}")
    print(f"📦  {label}")
    print(f"{'─'*50}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"  ⚠  Avertissement : {label} a rencontré une erreur (non bloquant)")
    else:
        print(f"  ✓  {label} installé")
    return result.returncode == 0

print("\n" + "═"*55)
print("  NETALYX v3.0 — Installation modules avancés")
print("═"*55)
print("\nCe script installe :")
print("  • Bridge WebSocket (websockets)")
print("  • Reconnaissance vocale (SpeechRecognition + pyttsx3)")
print("  • Détection gestuelle (MediaPipe + OpenCV)")
print("  • WebView 3D embarquée (tkinterweb)\n")

pip = f'"{sys.executable}" -m pip install --quiet --break-system-packages'

steps = [
    (f"{pip} websockets>=12.0", "WebSocket bridge"),
    (f"{pip} SpeechRecognition>=3.10", "Reconnaissance vocale"),
    (f"{pip} pyttsx3>=2.90", "Synthèse vocale (TTS)"),
    (f"{pip} pyaudio>=0.2.13", "Accès microphone (PyAudio)"),
    (f"{pip} opencv-python>=4.8", "OpenCV (webcam + vision)"),
    (f"{pip} mediapipe>=0.10", "MediaPipe (détection main)"),
    (f"{pip} tkinterweb>=3.23", "WebView 3D embarquée"),
]

results = []
for cmd, label in steps:
    ok = run(cmd, label)
    results.append((label, ok))

print("\n" + "═"*55)
print("  RÉSUMÉ D'INSTALLATION")
print("═"*55)
for label, ok in results:
    icon = "✓" if ok else "✗"
    status = "installé" if ok else "ERREUR (voir ci-dessus)"
    print(f"  {icon}  {label:<35} {status}")

print("\n" + "─"*55)
print("  Installation terminée.")
print("  Relancer Netalyx pour activer les nouvelles fonctions.")
print("─"*55 + "\n")

# Vérification rapide
print("🔍  Vérification des imports...")
checks = [
    ("websockets", "Bridge WebSocket"),
    ("speech_recognition", "Voix"),
    ("pyttsx3", "TTS"),
    ("cv2", "OpenCV"),
    ("mediapipe", "MediaPipe"),
    ("tkinterweb", "WebView 3D"),
]
for module, label in checks:
    try:
        __import__(module)
        print(f"  ✓  {label}")
    except ImportError:
        print(f"  ✗  {label} (non disponible)")
print()
