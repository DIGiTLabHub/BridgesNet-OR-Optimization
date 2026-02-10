"""Visualize a generated bridge network and report basic stats."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

SHOW_FLAG = "--show" in sys.argv
if not SHOW_FLAG:
    matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.rcParams["font.family"] = "Arial"

import matplotlib.pyplot as plt

from bridgesnet.config import GraphConfig, TeamConfig
from bridgesnet.graph import (
    build_graph,
    compute_layout,
    list_bridges,
    list_cities,
    node_colors,
    node_labels,
)
from bridgesnet.paths import compute_shortest_paths
from bridgesnet.plots import plot_network


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Visualize bridge network and print basic statistics"
    )
    parser.add_argument("--cities", type=int, default=6, help="Number of cities")
    parser.add_argument("--seed", type=int, default=2, help="Random seed")
    parser.add_argument(
        "--output", type=Path, default=Path("results") / "network.pdf"
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display the plot in an interactive window",
    )
    return parser


def total_shortest_path_distance(shortest_paths) -> float:
    total = 0.0
    for (_, _), (_, distance) in shortest_paths.items():
        if distance != float("inf"):
            total += float(distance)
    return total


def main() -> None:
    args = build_parser().parse_args()

    team_config = TeamConfig()
    graph_config = GraphConfig(n_cities=args.cities, seed=args.seed)
    G = build_graph(graph_config, team_config)

    pos = compute_layout(G, seed=graph_config.layout_seed)
    colors = node_colors(G)
    labels = node_labels(G)

    shortest_paths = compute_shortest_paths(G)
    total_distance = total_shortest_path_distance(shortest_paths)

    bridge_count = len(list_bridges(G))
    city_count = len(list_cities(G))

    print(f"Bridge nodes: {bridge_count}")
    print(f"Cities: {city_count}")
    print(f"Total shortest-path distance (Time): {total_distance:.4f}")

    output_path: Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig = plot_network(G, pos, colors, labels)
    fig.savefig(output_path)
    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
