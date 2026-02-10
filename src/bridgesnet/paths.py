"""Shortest-path utilities."""

from __future__ import annotations

from typing import Dict, Tuple

import networkx as nx


def compute_shortest_paths(
    G: nx.DiGraph, weight: str = "Time"
) -> Dict[Tuple[str, str], Tuple[list[str] | None, float]]:
    """Compute shortest paths and travel times for all node pairs."""

    for u, v in G.edges():
        if weight not in G[u][v]:
            raise ValueError(f"Edge {u}->{v} missing '{weight}' attribute")

    shortest_paths: Dict[Tuple[str, str], Tuple[list[str] | None, float]] = {}
    for source in G.nodes:
        for target in G.nodes:
            if source == target:
                continue
            try:
                path = nx.shortest_path(G, source=source, target=target, weight=weight)
                time = nx.shortest_path_length(
                    G, source=source, target=target, weight=weight
                )
                shortest_paths[(source, target)] = (path, time)
            except nx.NetworkXNoPath:
                shortest_paths[(source, target)] = (None, float("inf"))
    return shortest_paths
