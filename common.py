# common.py — utilitaires partagés (resource_path, config)
import os
import sys
import json

def resource_path(relative_path: str) -> str:
    """Chemin absolu vers une ressource, compatible PyInstaller et mode dev."""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)

def load_config() -> dict:
    with open(resource_path("config.json"), "r", encoding="utf-8") as f:
        return json.load(f)

CFG = load_config()
