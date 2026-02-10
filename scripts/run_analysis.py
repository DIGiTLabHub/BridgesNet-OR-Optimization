"""Run the full bridge sensitivity workflow and save figures."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.rcParams["font.family"] = "Arial"

from bridgesnet.config import GraphConfig, TeamConfig
from bridgesnet.graph import build_graph, compute_layout, node_colors, node_labels
from bridgesnet.model import build_model
from bridgesnet.pareto import pareto_frontier
from bridgesnet.paths import compute_shortest_paths
from bridgesnet.plots import plot_gantt, plot_network, plot_pareto, plot_routes_by_team
from bridgesnet.results import extract_solution


TEAM_COLORS = {"RRU": "blue", "ERT": "orange", "CIRS": "green"}


def save_figure(fig, output_dir: Path, name: str) -> None:
    fig.savefig(output_dir / f"{name}.png", dpi=200)
    fig.savefig(output_dir / f"{name}.pdf")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run bridge sensitivity analysis")
    parser.add_argument("--cities", type=int, default=6, help="Number of cities")
    parser.add_argument("--seed", type=int, default=2, help="Random seed")
    parser.add_argument(
        "--planning-horizon", type=int, default=8, help="Planning horizon"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("results"), help="Output folder"
    )
    parser.add_argument(
        "--pareto", action="store_true", help="Generate Pareto frontier"
    )
    parser.add_argument(
        "--write-lp", action="store_true", help="Write LP file to output folder"
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    team_config = TeamConfig()
    graph_config = GraphConfig(n_cities=args.cities, seed=args.seed)
    G = build_graph(graph_config, team_config)

    shortest_paths = compute_shortest_paths(G)
    artifacts, objectives = build_model(
        G, shortest_paths, team_config, planning_horizon=args.planning_horizon
    )

    artifacts.model.setObjective(
        (objectives.resilience + objectives.resilience_raw) / objectives.bridges_count
    )
    artifacts.model.optimize()

    if artifacts.model.Status == 3:
        artifacts.model.computeIIS()
        for c in artifacts.model.getConstrs():
            if c.IISConstr:
                print(f" - {c.ConstrName}")
        return

    solution = extract_solution(G, artifacts, objectives, team_config)

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.write_lp:
        artifacts.model.write(str(output_dir / "bridge.lp"))

    pos = compute_layout(G, seed=graph_config.layout_seed)
    colors = node_colors(G)
    labels = node_labels(G)

    fig = plot_network(G, pos, colors, labels)
    save_figure(fig, output_dir, "network")

    fig = plot_routes_by_team(
        G, pos, colors, solution.active_edges_by_team, TEAM_COLORS
    )
    save_figure(fig, output_dir, "routes")

    fig = plot_gantt(solution.schedule_data, TEAM_COLORS)
    save_figure(fig, output_dir, "gantt")

    if args.pareto:
        resilience_array, cost_array = pareto_frontier(artifacts, objectives)
        fig = plot_pareto(resilience_array, cost_array)
        save_figure(fig, output_dir, "pareto")

    print(f"Objective: {solution.objective:.4f}")
    print(f"Cost: {solution.cost:.4f}")
    print(f"Resilience: {solution.resilience:.4f}")
    print(f"Visited bridges: {solution.visited_bridges}")


if __name__ == "__main__":
    main()
