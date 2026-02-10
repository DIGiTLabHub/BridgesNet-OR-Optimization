"""Graph construction and helpers for bridge networks."""

from __future__ import annotations

import random
from typing import Dict, List, Tuple

import networkx as nx

from .config import GraphConfig, TeamConfig


def biased_choice(p_one: float, rng: random.Random) -> int:
    """Return 1 with a biased coin, matching notebook logic."""

    return 1 if rng.random() >= p_one else 0


def list_bridges(G: nx.DiGraph) -> List[str]:
    return [node for node in G.nodes() if str(node).startswith("B")]


def list_cities(G: nx.DiGraph) -> List[str]:
    return [node for node in G.nodes() if str(node).startswith("C")]


def build_graph(config: GraphConfig, team_config: TeamConfig) -> nx.DiGraph:
    """Build a synthetic bridge network with node and edge attributes."""

    rng = random.Random(config.seed)
    G = nx.DiGraph()

    cities = [f"C{i}" for i in range(1, config.n_cities + 1)]
    G.graph["cities"] = cities

    for city in cities:
        G.add_node(city)
        G.nodes[city]["Depot"] = biased_choice(config.depot_bias, rng)

    for i in range(len(cities)):
        for j in range(i + 1, len(cities)):
            city1, city2 = cities[i], cities[j]
            num_bridges = rng.randint(*config.bridge_count_range)
            prev_node = city1

            for b in range(num_bridges):
                bridge_node = f"B{city1}{city2}{b}"
                G.add_node(bridge_node)
                G.nodes[bridge_node]["Start"] = rng.randint(*config.bridge_start_range)
                G.nodes[bridge_node]["BFI"] = round(
                    rng.uniform(*config.bridge_bfi_range), 2
                )
                G.nodes[bridge_node]["Due"] = (
                    G.nodes[bridge_node]["Start"]
                    + rng.randint(*config.bridge_due_offset_range)
                )
                G.nodes[bridge_node]["cost"] = {}
                G.nodes[bridge_node]["NewBFI"] = {}

                for team in team_config.teams:
                    base_cost = team_config.base_cost[team]
                    bfi = G.nodes[bridge_node]["BFI"]
                    G.nodes[bridge_node]["cost"][team] = round(
                        base_cost * (1 + team_config.alpha * (1 - bfi)), 2
                    )
                    G.nodes[bridge_node]["NewBFI"][team] = min(
                        round(bfi + team_config.delta_functionality[team], 2), 1
                    )

                G.add_edge(prev_node, bridge_node)
                G.add_edge(bridge_node, prev_node)

                speed = rng.choice(config.speed_choices)
                capacity = rng.choice(config.capacity_choices)
                length = rng.randint(*config.length_range)
                time = length / speed

                for u, v in [(prev_node, bridge_node), (bridge_node, prev_node)]:
                    G[u][v]["speed"] = speed
                    G[u][v]["capacity"] = capacity
                    G[u][v]["length"] = length
                    G[u][v]["Time"] = time

                prev_node = bridge_node

            G.add_edge(prev_node, city2)
            G.add_edge(city2, prev_node)

            speed = rng.choice(config.speed_choices)
            capacity = rng.choice(config.capacity_choices)
            length = rng.randint(*config.final_length_range)
            time = length / speed

            for u, v in [(prev_node, city2), (city2, prev_node)]:
                G[u][v]["speed"] = speed
                G[u][v]["capacity"] = capacity
                G[u][v]["length"] = length
                G[u][v]["Time"] = time

    return G


def compute_layout(G: nx.DiGraph, seed: int) -> Dict[str, Tuple[float, float]]:
    return nx.spring_layout(G, seed=seed, weight="length")


def node_colors(G: nx.DiGraph) -> List[str]:
    colors: List[str] = []
    for node in G.nodes():
        if G.nodes[node].get("Depot", 0) == 1:
            colors.append("red")
        elif str(node).startswith("C"):
            colors.append("green")
        else:
            colors.append("lightgray")
    return colors


def node_labels(G: nx.DiGraph) -> Dict[str, str]:
    return {node: "" for node in G.nodes()}
