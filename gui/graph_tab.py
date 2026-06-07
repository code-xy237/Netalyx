# gui/graph_tab.py — Onglet cartographie réseau (matplotlib + networkx dans Tkinter)
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb
import threading
import math

import networkx as nx
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as mpatches

from security.network_graph import NetworkGraph, STATUS_COLORS, STATUS_NORMAL


# Layout algorithms disponibles
LAYOUTS = {
    "Spring (forcé)":    "spring",
    "Circulaire":        "circular",
    "Kamada-Kawai":      "kamada_kawai",
    "Aléatoire":         "random",
    "Shell":             "shell",
}


class GraphTab(tb.Frame):
    """Onglet de cartographie réseau en temps réel."""

    def __init__(self, master, net_graph: NetworkGraph):
        super().__init__(master, padding=8)
        self.ng           = net_graph
        self._layout      = "spring"
        self._pos         = {}          # positions des nœuds (mises en cache)
        self._auto_update = tk.BooleanVar(value=True)
        self._show_labels = tk.BooleanVar(value=True)
        self._show_ports  = tk.BooleanVar(value=False)
        self._filter_var  = tk.StringVar(value="")
        self._update_interval = 2000   # ms

        self._build_ui()
        self._schedule_update()

    # ── Construction UI ───────────────────────────────────────────────────
    def _build_ui(self):
        # Barre de contrôle
        ctrl = tb.Frame(self)
        ctrl.pack(fill="x", pady=(0, 8))

        tb.Label(ctrl, text="Layout :").pack(side="left")
        self._layout_var = tk.StringVar(value="Spring (forcé)")
        combo = tb.Combobox(ctrl, textvariable=self._layout_var,
                            values=list(LAYOUTS.keys()), width=18, state="readonly")
        combo.pack(side="left", padx=(4, 12))
        combo.bind("<<ComboboxSelected>>", lambda e: self._change_layout())

        tb.Checkbutton(ctrl, text="Auto-refresh",
                       variable=self._auto_update, bootstyle="success").pack(side="left", padx=4)
        tb.Checkbutton(ctrl, text="Labels IP",
                       variable=self._show_labels, bootstyle="info").pack(side="left", padx=4)
        tb.Checkbutton(ctrl, text="Ports",
                       variable=self._show_ports, bootstyle="secondary").pack(side="left", padx=4)

        tb.Label(ctrl, text="  Filtrer IP :").pack(side="left", padx=(12, 2))
        tb.Entry(ctrl, textvariable=self._filter_var, width=16).pack(side="left")

        tb.Button(ctrl, text="↺ Recalculer layout",
                  bootstyle="secondary-outline",
                  command=self._reset_layout).pack(side="left", padx=8)

        tb.Button(ctrl, text="🗑 Vider le graphe",
                  bootstyle="danger-outline",
                  command=self._clear).pack(side="left", padx=4)

        # Légende
        legend_frame = tb.Frame(self)
        legend_frame.pack(fill="x", pady=(0, 6))
        legend_items = [
            ("Local / privé",  "#A78BFA"),
            ("Normal",         "#4CAF50"),
            ("Suspect",        "#FF8800"),
            ("Bloqué",         "#FF2222"),
            ("Gateway",        "#00BFFF"),
        ]
        for label, color in legend_items:
            dot = tk.Canvas(legend_frame, width=12, height=12,
                            bg="#0e0f12", highlightthickness=0)
            dot.create_oval(1, 1, 11, 11, fill=color, outline="")
            dot.pack(side="left", padx=(8, 2))
            tb.Label(legend_frame, text=label,
                     font=("Segoe UI", 9)).pack(side="left", padx=(0, 8))

        # Zone graphique principale + panneau latéral
        body = tb.Frame(self)
        body.pack(fill="both", expand=True)

        # Figure matplotlib
        graph_frame = tb.Frame(body)
        graph_frame.pack(side="left", fill="both", expand=True)

        self.fig = Figure(figsize=(8, 5.5), dpi=96)
        self.fig.patch.set_facecolor("#0e0f12")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#0e0f12")
        self.ax.axis("off")

        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        widget = self.canvas.get_tk_widget()
        widget.pack(fill="both", expand=True)

        # Clic sur le canvas → sélection de nœud
        self.canvas.mpl_connect("button_press_event", self._on_click)
        self._selected_node = None

        # Panneau latéral : top IPs + infos nœud sélectionné
        right = tb.Frame(body, width=210)
        right.pack(side="right", fill="y", padx=(8, 0))
        right.pack_propagate(False)

        # Compteurs
        stat_frame = tb.Labelframe(right, text="Statistiques", bootstyle="secondary", padding=8)
        stat_frame.pack(fill="x", pady=(0, 8))
        self._lbl_nodes = tb.Label(stat_frame, text="Nœuds : 0",
                                   font=("Segoe UI", 10))
        self._lbl_nodes.pack(anchor="w")
        self._lbl_edges = tb.Label(stat_frame, text="Connexions : 0",
                                   font=("Segoe UI", 10))
        self._lbl_edges.pack(anchor="w")

        # Top IPs
        top_frame = tb.Labelframe(right, text="Top IPs actives", bootstyle="info", padding=8)
        top_frame.pack(fill="x", pady=(0, 8))
        self._top_text = tk.Text(top_frame, height=10, bg="#0f1116", fg="#d6e2ff",
                                  font=("Consolas", 9), bd=0, relief="flat",
                                  state="disabled")
        self._top_text.pack(fill="both")

        # Infos nœud sélectionné
        self._info_frame = tb.Labelframe(right, text="Nœud sélectionné",
                                          bootstyle="primary", padding=8)
        self._info_frame.pack(fill="x", pady=(0, 8))
        self._lbl_node_info = tk.Text(self._info_frame, height=6,
                                       bg="#0f1116", fg="#d6e2ff",
                                       font=("Consolas", 9), bd=0, relief="flat",
                                       state="disabled", wrap="word")
        self._lbl_node_info.pack(fill="both")

        # Actions sur nœud sélectionné
        action_frame = tb.Frame(right)
        action_frame.pack(fill="x")
        self._btn_suspect = tb.Button(action_frame, text="⚠ Marquer suspect",
                                       bootstyle="warning-outline",
                                       command=self._mark_selected_suspect)
        self._btn_suspect.pack(fill="x", pady=2)
        self._btn_block = tb.Button(action_frame, text="🚫 Bloquer IP",
                                     bootstyle="danger-outline",
                                     command=self._block_selected)
        self._btn_block.pack(fill="x", pady=2)

    # ── Rendu du graphe ───────────────────────────────────────────────────
    def _render(self):
        snap    = self.ng.snapshot()
        nodes   = snap["nodes"]
        edges   = snap["edges"]
        filter_ = self._filter_var.get().strip()

        if not nodes:
            self.ax.clear()
            self.ax.set_facecolor("#0e0f12")
            self.ax.axis("off")
            self.ax.text(0.5, 0.5, "En attente de trafic réseau…",
                         ha="center", va="center", color="#555",
                         fontsize=12, transform=self.ax.transAxes)
            self.canvas.draw_idle()
            return

        # Construire sous-graphe filtré
        G = nx.DiGraph()
        for n in nodes:
            if filter_ and filter_ not in n["id"]:
                continue
            G.add_node(n["id"], **n)
        for e in edges:
            if e["src"] in G.nodes and e["dst"] in G.nodes:
                G.add_edge(e["src"], e["dst"],
                           weight=e["weight"], proto=e["proto"], dport=e["dport"])

        if not G.nodes:
            return

        # Calcul du layout (mis en cache si le graphe n'a pas changé de taille)
        if (not self._pos or
                set(G.nodes) != set(self._pos.keys()) or
                self._layout == "random"):
            self._pos = self._compute_layout(G)

        # Couleurs et tailles des nœuds
        node_colors = [G.nodes[n].get("color", "#4CAF50") for n in G.nodes]
        volumes     = [G.nodes[n].get("volume", 1) for n in G.nodes]
        max_vol     = max(volumes) if volumes else 1
        node_sizes  = [200 + 1200 * (v / max_vol) for v in volumes]

        # Couleurs des arêtes selon le protocole
        edge_colors = []
        for u, v in G.edges():
            proto = G[u][v].get("proto", "?")
            if proto == "TCP":    edge_colors.append("#4FC3F7")
            elif proto == "UDP":  edge_colors.append("#81C784")
            elif proto == "ICMP": edge_colors.append("#FFB74D")
            else:                 edge_colors.append("#78909C")

        # Épaisseur des arêtes selon le poids
        max_w = max((G[u][v].get("weight", 1) for u, v in G.edges()), default=1)
        edge_widths = [0.5 + 2.5 * (G[u][v].get("weight", 1) / max_w)
                       for u, v in G.edges()]

        self.ax.clear()
        self.ax.set_facecolor("#0e0f12")
        self.ax.axis("off")

        # Dessin arêtes
        nx.draw_networkx_edges(
            G, self._pos, ax=self.ax,
            edge_color=edge_colors,
            width=edge_widths,
            alpha=0.6,
            arrows=True,
            arrowsize=12,
            arrowstyle="-|>",
            connectionstyle="arc3,rad=0.08",
            min_source_margin=15,
            min_target_margin=15,
        )

        # Dessin nœuds
        nx.draw_networkx_nodes(
            G, self._pos, ax=self.ax,
            node_color=node_colors,
            node_size=node_sizes,
            alpha=0.92,
        )

        # Nœud sélectionné : contour blanc
        if self._selected_node and self._selected_node in self._pos:
            nx.draw_networkx_nodes(
                G, self._pos, ax=self.ax,
                nodelist=[self._selected_node],
                node_color="none",
                node_size=[node_sizes[list(G.nodes).index(self._selected_node)] + 120],
                edgecolors="white",
                linewidths=2.5,
            )

        # Labels
        if self._show_labels.get():
            # Afficher IPs courtes (derniers octets)
            labels = {n: ".".join(n.split(".")[-2:]) if "." in n else n
                      for n in G.nodes}
            nx.draw_networkx_labels(
                G, self._pos, labels=labels, ax=self.ax,
                font_size=7, font_color="white", font_weight="bold"
            )

        # Labels arêtes (ports)
        if self._show_ports.get():
            edge_labels = {(u, v): f"{G[u][v].get('proto','?')}:{G[u][v].get('dport','?')}"
                           for u, v in G.edges()
                           if G[u][v].get("dport")}
            nx.draw_networkx_edge_labels(
                G, self._pos, edge_labels=edge_labels, ax=self.ax,
                font_size=6, font_color="#aaa", label_pos=0.35
            )

        self.canvas.draw_idle()

        # Mise à jour panneau latéral
        self._lbl_nodes.config(text=f"Nœuds : {snap['node_count']}")
        self._lbl_edges.config(text=f"Connexions : {snap['edge_count']}")
        self._update_top_ips()

    def _compute_layout(self, G) -> dict:
        name = LAYOUTS.get(self._layout_var.get(), "spring")
        try:
            if name == "spring":
                return nx.spring_layout(G, k=2.5 / math.sqrt(max(len(G.nodes), 1)),
                                        iterations=60, seed=42)
            elif name == "circular":
                return nx.circular_layout(G)
            elif name == "kamada_kawai":
                return nx.kamada_kawai_layout(G)
            elif name == "shell":
                return nx.shell_layout(G)
            else:
                return nx.random_layout(G, seed=42)
        except Exception:
            return nx.random_layout(G, seed=42)

    # ── Mise à jour périodique ────────────────────────────────────────────
    def _schedule_update(self):
        if self._auto_update.get():
            self.ng.prune_old_edges()
            threading.Thread(target=self._render_async, daemon=True).start()
        self.after(self._update_interval, self._schedule_update)

    def _render_async(self):
        """Lance le rendu dans le thread principal via after()."""
        self.after(0, self._render)

    # ── Interactions utilisateur ──────────────────────────────────────────
    def _change_layout(self):
        self._layout = LAYOUTS.get(self._layout_var.get(), "spring")
        self._pos = {}   # force recalcul
        self._render()

    def _reset_layout(self):
        self._pos = {}
        self._render()

    def _clear(self):
        if messagebox.askyesno("Vider", "Effacer tout le graphe réseau ?"):
            self.ng.reset()
            self._pos = {}
            self._render()

    def _on_click(self, event):
        """Sélectionne le nœud le plus proche du clic."""
        if event.inaxes != self.ax or not self._pos:
            return
        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return
        closest, min_dist = None, float("inf")
        for node, (nx_coord, ny_coord) in self._pos.items():
            dist = math.hypot(x - nx_coord, y - ny_coord)
            if dist < min_dist:
                min_dist, closest = dist, node
        if min_dist < 0.15 and closest:
            self._selected_node = closest
            self._show_node_info(closest)
            self._render()

    def _show_node_info(self, ip: str):
        snap = self.ng.snapshot()
        node = next((n for n in snap["nodes"] if n["id"] == ip), None)
        out_edges = [e for e in snap["edges"] if e["src"] == ip]
        in_edges  = [e for e in snap["edges"] if e["dst"] == ip]
        info = (
            f"IP : {ip}\n"
            f"Statut : {node['status'] if node else '?'}\n"
            f"Volume : {node['volume'] if node else '?'} paquets\n"
            f"Connexions sortantes : {len(out_edges)}\n"
            f"Connexions entrantes : {len(in_edges)}\n"
        )
        self._lbl_node_info.configure(state="normal")
        self._lbl_node_info.delete("1.0", "end")
        self._lbl_node_info.insert("end", info)
        self._lbl_node_info.configure(state="disabled")

    def _update_top_ips(self):
        top = self.ng.get_top_ips(10)
        self._top_text.configure(state="normal")
        self._top_text.delete("1.0", "end")
        for ip, vol in top:
            self._top_text.insert("end", f"{ip:<18} {vol:>5} pkts\n")
        self._top_text.configure(state="disabled")

    def _mark_selected_suspect(self):
        if self._selected_node:
            self.ng.mark_suspect(self._selected_node)
            self._render()

    def _block_selected(self):
        if not self._selected_node:
            return
        ip = self._selected_node
        if messagebox.askyesno("Bloquer", f"Bloquer l'IP {ip} via le pare-feu ?"):
            self.ng.mark_blocked(ip)
            self._render()
