# security/network_graph.py — Cartographie réseau temps réel (networkx)
#
# Maintient un graphe dirigé des connexions réseau :
#   - Nœuds  : IPs (taille = volume de trafic)
#   - Arêtes : flux (src → dst), poids = nombre de paquets
#   - Couleur des nœuds selon le statut (normal / suspect / bloqué / gateway)
#
import threading
import time
import ipaddress
from collections import defaultdict
import networkx as nx

# Statuts possibles d'un nœud
STATUS_NORMAL   = "normal"
STATUS_SUSPECT  = "suspect"
STATUS_BLOCKED  = "blocked"
STATUS_GATEWAY  = "gateway"
STATUS_LOCAL    = "local"

# Couleurs associées (pour matplotlib)
STATUS_COLORS = {
    STATUS_NORMAL:  "#4CAF50",   # vert
    STATUS_SUSPECT: "#FF8800",   # orange
    STATUS_BLOCKED: "#FF2222",   # rouge
    STATUS_GATEWAY: "#00BFFF",   # bleu clair
    STATUS_LOCAL:   "#A78BFA",   # violet
}

MAX_NODES = 80   # limite pour les performances
EDGE_TTL  = 120  # secondes avant qu'une arête soit retirée si pas de trafic


class NetworkGraph:
    """
    Graphe réseau mis à jour en temps réel depuis le flux de paquets.
    Thread-safe via un verrou.
    """

    def __init__(self):
        self.G        = nx.DiGraph()
        self._lock    = threading.Lock()
        self._edge_ts = {}           # {(src, dst): last_seen_ts}
        self._node_vol = defaultdict(int)  # {ip: total paquets}
        self._suspects = set()
        self._blocked  = set()
        self._gateway  = None

    # ── Alimentation depuis le sniffer ────────────────────────────────────
    def feed(self, rec: dict):
        src = rec.get("src")
        dst = rec.get("dst")
        if not src or not dst:
            return

        now = time.time()
        with self._lock:
            # Limiter le nombre de nœuds
            if (src not in self.G.nodes and
                    dst not in self.G.nodes and
                    len(self.G.nodes) >= MAX_NODES):
                return

            # Ajouter / mettre à jour les nœuds
            for ip in (src, dst):
                if ip not in self.G.nodes:
                    self.G.add_node(ip, status=self._classify(ip), volume=0)
                self._node_vol[ip] += 1
                self.G.nodes[ip]["volume"] = self._node_vol[ip]

            # Ajouter / mettre à jour l'arête
            if self.G.has_edge(src, dst):
                self.G[src][dst]["weight"] += 1
            else:
                self.G.add_edge(src, dst, weight=1,
                                proto=rec.get("proto", "?"),
                                dport=rec.get("dport"))
            self._edge_ts[(src, dst)] = now

    def _classify(self, ip: str) -> str:
        if ip in self._blocked:  return STATUS_BLOCKED
        if ip in self._suspects: return STATUS_SUSPECT
        if ip == self._gateway:  return STATUS_GATEWAY
        if self._is_private(ip): return STATUS_LOCAL
        return STATUS_NORMAL

    @staticmethod
    def _is_private(ip: str) -> bool:
        try:
            return ipaddress.ip_address(ip).is_private
        except ValueError:
            return False

    # ── Mise à jour des statuts ───────────────────────────────────────────
    def mark_suspect(self, ip: str):
        with self._lock:
            self._suspects.add(ip)
            if ip in self.G.nodes:
                self.G.nodes[ip]["status"] = STATUS_SUSPECT

    def mark_blocked(self, ip: str):
        with self._lock:
            self._blocked.add(ip)
            self._suspects.discard(ip)
            if ip in self.G.nodes:
                self.G.nodes[ip]["status"] = STATUS_BLOCKED

    def set_gateway(self, ip: str):
        with self._lock:
            self._gateway = ip
            if ip in self.G.nodes:
                self.G.nodes[ip]["status"] = STATUS_GATEWAY

    def clear_suspect(self, ip: str):
        with self._lock:
            self._suspects.discard(ip)
            if ip in self.G.nodes:
                self.G.nodes[ip]["status"] = self._classify(ip)

    # ── Nettoyage des arêtes anciennes ────────────────────────────────────
    def prune_old_edges(self):
        now = time.time()
        with self._lock:
            stale = [(s, d) for (s, d), ts in self._edge_ts.items()
                     if now - ts > EDGE_TTL]
            for s, d in stale:
                if self.G.has_edge(s, d):
                    self.G.remove_edge(s, d)
                del self._edge_ts[(s, d)]
            # Supprimer les nœuds isolés (sauf si volumineux)
            isolated = [n for n in list(self.G.nodes)
                        if self.G.degree(n) == 0 and self._node_vol[n] < 5]
            self.G.remove_nodes_from(isolated)

    # ── Snapshot pour le rendu ────────────────────────────────────────────
    def snapshot(self) -> dict:
        """Retourne une copie légère du graphe pour le rendu (thread-safe)."""
        with self._lock:
            nodes = [
                {
                    "id":     n,
                    "status": data.get("status", STATUS_NORMAL),
                    "volume": data.get("volume", 1),
                    "color":  STATUS_COLORS.get(data.get("status", STATUS_NORMAL), "#4CAF50"),
                }
                for n, data in self.G.nodes(data=True)
            ]
            edges = [
                {
                    "src":    u,
                    "dst":    v,
                    "weight": data.get("weight", 1),
                    "proto":  data.get("proto", "?"),
                    "dport":  data.get("dport"),
                }
                for u, v, data in self.G.edges(data=True)
            ]
            return {"nodes": nodes, "edges": edges,
                    "node_count": len(nodes), "edge_count": len(edges)}

    def get_top_ips(self, n: int = 10) -> list:
        """Retourne les N IPs les plus actives."""
        with self._lock:
            return sorted(self._node_vol.items(), key=lambda x: -x[1])[:n]

    def reset(self):
        with self._lock:
            self.G.clear()
            self._edge_ts.clear()
            self._node_vol.clear()
