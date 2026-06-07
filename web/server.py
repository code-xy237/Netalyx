# web/server.py — Serveur Flask embarqué avec WebSocket temps réel
#
# Lance un micro-serveur Flask dans un thread daemon.
# Le dashboard est accessible depuis n'importe quel appareil du réseau local :
#   http://<IP-machine>:5000
#
# Données transmises en temps réel via Socket.IO :
#   - Trafic réseau (paquets)
#   - Alertes IDS (règles + ML)
#   - Statistiques globales
#   - Graphe réseau (snapshot)
#
import threading
import time
import json
import os
from collections import deque
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
from flask_cors import CORS

app     = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(__file__), "templates"),
                static_folder=os.path.join(os.path.dirname(__file__), "static"))
app.config["SECRET_KEY"] = "netalyx-secret-2025"
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ── Stockage partagé des données (alimenté depuis le dashboard Tkinter) ───────
_data = {
    "packets":     deque(maxlen=200),
    "alerts":      deque(maxlen=500),
    "stats":       {"packets_total": 0, "alerts_total": 0, "devices_total": 0},
    "graph":       {"nodes": [], "edges": []},
    "ml_stats":    {},
    "devices":     deque(maxlen=100),
    "top_ips":     [],
}
_lock = threading.Lock()


# ── API REST ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/stats")
def api_stats():
    with _lock:
        return jsonify(_data["stats"])

@app.route("/api/alerts")
def api_alerts():
    limit = int(request.args.get("limit", 50))
    with _lock:
        return jsonify(list(_data["alerts"])[-limit:])

@app.route("/api/packets")
def api_packets():
    limit = int(request.args.get("limit", 50))
    with _lock:
        return jsonify(list(_data["packets"])[-limit:])

@app.route("/api/graph")
def api_graph():
    with _lock:
        return jsonify(_data["graph"])

@app.route("/api/devices")
def api_devices():
    with _lock:
        return jsonify(list(_data["devices"]))

@app.route("/api/ml")
def api_ml():
    with _lock:
        return jsonify(_data["ml_stats"])

@app.route("/api/top_ips")
def api_top_ips():
    with _lock:
        return jsonify(_data["top_ips"])


# ── WebSocket events ──────────────────────────────────────────────────────────

@socketio.on("connect")
def on_connect():
    """Envoie un snapshot complet à la connexion."""
    with _lock:
        socketio.emit("snapshot", {
            "stats":   _data["stats"],
            "alerts":  list(_data["alerts"])[-50:],
            "packets": list(_data["packets"])[-50:],
            "graph":   _data["graph"],
            "devices": list(_data["devices"])[-20:],
            "ml":      _data["ml_stats"],
        })


# ── Fonctions appelées depuis le dashboard Tkinter ────────────────────────────

def push_packet(rec: dict):
    """Reçoit un paquet du sniffer et le diffuse aux clients web."""
    payload = {
        "time":  datetime.utcfromtimestamp(rec.get("time", time.time())).strftime("%H:%M:%S"),
        "src":   rec.get("src", "?"),
        "dst":   rec.get("dst", "?"),
        "proto": rec.get("proto", "?"),
        "sport": rec.get("sport"),
        "dport": rec.get("dport"),
    }
    with _lock:
        _data["packets"].append(payload)
        _data["stats"]["packets_total"] += 1
    socketio.emit("packet", payload)

def push_alert(kind: str, detail: dict):
    """Reçoit une alerte IDS et la diffuse."""
    payload = {
        "time":   datetime.utcnow().strftime("%H:%M:%S"),
        "kind":   kind,
        "src":    detail.get("src", "?"),
        "detail": str(detail)[:200],
        "critical": kind in ("CRITICAL_INCIDENT", "ANOMALY_DETECTED", "IP_BLOCKED"),
    }
    with _lock:
        _data["alerts"].append(payload)
        _data["stats"]["alerts_total"] += 1
    socketio.emit("alert", payload)

def push_device(ip: str, mac: str, hostname: str, open_ports: list):
    payload = {
        "time":       datetime.utcnow().strftime("%H:%M:%S"),
        "ip":         ip,
        "mac":        mac,
        "hostname":   hostname,
        "open_ports": open_ports[:10],
    }
    with _lock:
        _data["devices"].appendleft(payload)
        _data["stats"]["devices_total"] += 1
    socketio.emit("device", payload)

def update_graph(snapshot: dict):
    with _lock:
        _data["graph"] = snapshot
    socketio.emit("graph_update", snapshot)

def update_ml_stats(stats: dict):
    with _lock:
        _data["ml_stats"] = stats
    socketio.emit("ml_update", stats)

def update_top_ips(top: list):
    with _lock:
        _data["top_ips"] = [{"ip": ip, "volume": vol} for ip, vol in top]


# ── Démarrage du serveur ──────────────────────────────────────────────────────

_server_thread = None

def start_server(host: str = "0.0.0.0", port: int = 5000):
    """Démarre le serveur Flask dans un thread daemon."""
    global _server_thread
    if _server_thread and _server_thread.is_alive():
        return False
    def _run():
        import logging
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)   # silencer les logs HTTP dans la console
        socketio.run(app, host=host, port=port, debug=False, use_reloader=False)
    _server_thread = threading.Thread(target=_run, daemon=True)
    _server_thread.start()
    return True

def stop_server():
    """Arrêt gracieux (le thread est daemon, s'arrête avec l'app principale)."""
    pass

def is_running() -> bool:
    return _server_thread is not None and _server_thread.is_alive()
