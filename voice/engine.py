# voice/engine.py — Moteur vocal Netalyx
# Double pipeline : SpeechRecognition (temps réel) + Whisper (précision)
# TTS réponses IA via pyttsx3

import threading
import time
import queue
import logging
import os
import re
from typing import Optional, Callable

logger = logging.getLogger("netalyx.voice")

# ── Détection des dépendances ─────────────────────────────────────────────────
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    logger.warning("SpeechRecognition non installé (pip install SpeechRecognition)")

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logger.warning("pyttsx3 non installé (pip install pyttsx3)")

try:
    import openai
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False


class VoiceEngine:
    """
    Moteur vocal complet pour Netalyx :
    - Écoute continue microphone (SpeechRecognition / Google STT gratuit)
    - Fallback Whisper API pour la précision
    - TTS synthèse vocale des réponses IA
    - Dispatch des commandes vers CommandDispatcher
    """

    WAKE_WORDS = ["netalyx", "neta", "hey neta", "hey netalyx", "réseau"]
    RESPONSE_PHRASES = {
        "zoom": "Zoom appliqué sur la scène.",
        "reset": "Graphe réseau réinitialisé.",
        "block_ip": "IP bloquée dans le pare-feu.",
        "suspect_ip": "IP marquée comme suspecte.",
        "show_alerts": "Affichage des alertes de sécurité.",
        "refresh": "Données réseau actualisées.",
        "show_stats": "Statistiques réseau affichées.",
        "unknown": "Commande non reconnue. Réessayez.",
    }

    def __init__(self, dispatcher=None, bridge=None):
        self.dispatcher = dispatcher
        self.bridge = bridge
        self._running = False
        self._listen_thread: Optional[threading.Thread] = None
        self._tts_thread: Optional[threading.Thread] = None
        self._tts_queue: queue.Queue = queue.Queue()
        self._tts_engine = None
        self._recognizer = None
        self._microphone = None
        self._wake_word_mode = False  # False = toujours actif
        self._sensitivity = 0.5       # seuil énergie micro
        self._on_recognized: Optional[Callable] = None
        self._on_speaking: Optional[Callable] = None

        self._init_components()

    def _init_components(self):
        """Initialise SpeechRecognition et pyttsx3."""
        if SR_AVAILABLE:
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = 300
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.pause_threshold = 0.8
            try:
                self._microphone = sr.Microphone()
                # Calibration bruit ambiant
                with self._microphone as source:
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                logger.info("Microphone calibré")
            except Exception as e:
                logger.warning(f"Microphone non disponible: {e}")
                self._microphone = None

        if TTS_AVAILABLE:
            try:
                self._tts_engine = pyttsx3.init()
                voices = self._tts_engine.getProperty('voices')
                # Préférer une voix française
                for v in voices:
                    if 'fr' in v.id.lower() or 'french' in v.name.lower():
                        self._tts_engine.setProperty('voice', v.id)
                        break
                self._tts_engine.setProperty('rate', 175)
                self._tts_engine.setProperty('volume', 0.9)
                logger.info("TTS initialisé")
            except Exception as e:
                logger.warning(f"TTS non disponible: {e}")
                self._tts_engine = None

    # ── Démarrage / Arrêt ─────────────────────────────────────────────────────
    def start(self):
        """Démarre l'écoute continue en background."""
        if self._running:
            return
        if not SR_AVAILABLE or self._microphone is None:
            logger.warning("Voice engine: pas de micro disponible")
            return
        self._running = True
        self._listen_thread = threading.Thread(
            target=self._listen_loop, daemon=True, name="VoiceListener"
        )
        self._listen_thread.start()
        self._tts_thread = threading.Thread(
            target=self._tts_loop, daemon=True, name="TTSSpeaker"
        )
        self._tts_thread.start()
        logger.info("Voice Engine démarré — écoute active")
        if self.bridge:
            self.bridge.broadcast("voice_status", {"active": True, "mode": "listening"})

    def stop(self):
        self._running = False
        logger.info("Voice Engine arrêté")
        if self.bridge:
            self.bridge.broadcast("voice_status", {"active": False})

    # ── Boucle d'écoute ───────────────────────────────────────────────────────
    def _listen_loop(self):
        """Écoute continue avec SpeechRecognition."""
        logger.info("Boucle d'écoute démarrée")
        while self._running:
            try:
                with self._microphone as source:
                    try:
                        audio = self._recognizer.listen(
                            source, timeout=2, phrase_time_limit=6
                        )
                    except sr.WaitTimeoutError:
                        continue

                # Reconnaissance en thread séparé pour ne pas bloquer
                threading.Thread(
                    target=self._process_audio,
                    args=(audio,),
                    daemon=True
                ).start()

            except Exception as e:
                logger.debug(f"Listen loop: {e}")
                time.sleep(0.5)

    def _process_audio(self, audio):
        """Tente de reconnaître l'audio et dispatche la commande."""
        text = None

        # 1. Essai Google STT (gratuit, pas de clé requise)
        try:
            text = self._recognizer.recognize_google(audio, language="fr-FR")
            logger.debug(f"Reconnu (Google STT): '{text}'")
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            # Fallback: reconnaissance hors ligne si disponible
            try:
                text = self._recognizer.recognize_sphinx(audio)
            except Exception:
                pass

        if not text:
            return

        # Notifier le bridge (pour affichage dans HUD)
        if self.bridge:
            self.bridge.broadcast("voice_recognized", {
                "text": text,
                "timestamp": time.time()
            })

        # Callback UI si défini
        if self._on_recognized:
            self._on_recognized(text)

        # Dispatcher vers les commandes Netalyx
        if self.dispatcher:
            cmd = self.dispatcher.dispatch(text)
            response = self.RESPONSE_PHRASES.get(cmd or "unknown")
            if cmd:
                self.speak(response)
                logger.info(f"Commande exécutée: {cmd}")
        else:
            # Mode direct sans dispatcher
            logger.info(f"Audio reconnu (sans dispatcher): {text}")

    # ── TTS ───────────────────────────────────────────────────────────────────
    def speak(self, text: str, priority: bool = False):
        """Synthétise vocalement le texte donné (async, non-bloquant)."""
        if not text or not TTS_AVAILABLE or self._tts_engine is None:
            return
        if priority:
            # Vider la queue et parler immédiatement
            while not self._tts_queue.empty():
                try:
                    self._tts_queue.get_nowait()
                except queue.Empty:
                    break
        self._tts_queue.put(text)

        # Notifier le frontend (waveform animation)
        if self.bridge:
            self.bridge.broadcast("tts_speaking", {"text": text, "active": True})

    def _tts_loop(self):
        """Loop TTS dans son propre thread (pyttsx3 n'est pas thread-safe)."""
        while self._running:
            try:
                text = self._tts_queue.get(timeout=1)
                if self._tts_engine:
                    self._tts_engine.say(text)
                    self._tts_engine.runAndWait()
                if self.bridge:
                    self.bridge.broadcast("tts_speaking", {"text": "", "active": False})
            except queue.Empty:
                continue
            except Exception as e:
                logger.warning(f"TTS erreur: {e}")

    # ── API publique ──────────────────────────────────────────────────────────
    def set_on_recognized(self, callback: Callable):
        """Callback appelé avec le texte reconnu (pour l'UI)."""
        self._on_recognized = callback

    def set_on_speaking(self, callback: Callable):
        """Callback appelé quand le TTS parle (pour animation)."""
        self._on_speaking = callback

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def available(self) -> bool:
        return SR_AVAILABLE and self._microphone is not None


class VoiceEngineStub:
    """Stub pour les environnements sans micro (tests, CI)."""
    def start(self): pass
    def stop(self): pass
    def speak(self, text, priority=False): print(f"[TTS stub] {text}")
    def set_on_recognized(self, cb): pass
    def set_on_speaking(self, cb): pass
    is_running = False
    available = False


def create_voice_engine(dispatcher=None, bridge=None) -> VoiceEngine:
    """Factory : crée le moteur approprié selon les dépendances disponibles."""
    engine = VoiceEngine(dispatcher=dispatcher, bridge=bridge)
    if not engine.available:
        logger.warning("Micro non disponible → mode stub")
        return VoiceEngineStub()
    return engine
