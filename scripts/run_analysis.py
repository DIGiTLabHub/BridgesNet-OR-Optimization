"""Run one parameterized bridge-network analysis and export auditable results."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

MATPLOTLIB_CACHE = Path(tempfile.gettempdir()) / "bridgesnet-matplotlib-cache"
MATPLOTLIB_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MATPLOTLIB_CACHE))
XDG_CACHE = Path(tempfile.gettempdir()) / "bridgesnet-xdg-cache"
XDG_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("XDG_CACHE_HOME", str(XDG_CACHE))

import matplotlib
from gurobipy import GRB
matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.rcParams["font.family"] = "DejaVu Sans"
import matplotlib.pyplot as plt

from bridgesnet.config import GraphConfig, TeamConfig
from bridgesnet.graph import (
    build_graph,
    compute_layout,
    force_city_depots,
    node_colors,
    node_labels,
)
from bridgesnet.model import build_model
from bridgesnet.pareto import pareto_frontier
from bridgesnet.paths import compute_shortest_paths
from bridgesnet.plots import (
    plot_cumulative_profile,
    plot_gantt,
    plot_network,
    plot_pareto,
    plot_routes_by_team,
)
from bridgesnet.results import cumulative_profile, extract_solution
from bridgesnet.solver import SolverConfig, runtime_metadata, solve_maximum_functionality


TEAM_COLORS = {"RRU": "#4477AA", "ERT": "#EE6677", "CIRS": "#228833"}


def save_figure(fig, output_dir: Path, name: str) -> None:
    fig.savefig(output_dir / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(output_dir / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Solve one parameterized bridge-network recovery instance"
    )
    parser.add_argument("--cities", type=int, default=6)
    parser.add_argument("--seed", type=int, default=2)
    parser.add_argument(
        "--depots",
        type=int,
        help="Force C1 through CD to be depots; default preserves seeded selection",
    )
    parser.add_argument("--planning-horizon", type=int, default=8)
    parser.add_argument("--time-limit", type=float, default=3600.0)
    parser.add_argument("--mip-gap", type=float, default=1e-4)
    parser.add_argument("--threads", type=int, default=0)
    parser.add_argument("--gurobi-seed", type=int, default=0)
    parser.add_argument("--output-dir", type=Path, default=Path("results") / "analysis")
    parser.add_argument("--pareto", action="store_true")
    parser.add_argument("--pareto-points", type=int, default=10)
    parser.add_argument("--write-lp", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def _instance_payload(graph, graph_config: GraphConfig, team_config: TeamConfig) -> dict[str, Any]:
    return {
        "graph_config": asdict(graph_config),
        "team_config": asdict(team_config),
        "nodes": [
            {"id": str(node), "attributes": dict(graph.nodes[node])}
            for node in graph.nodes
        ],
        "edges": [
            {"source": str(source), "target": str(target), "attributes": dict(data)}
            for source, target, data in graph.edges(data=True)
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cities < 2:
        raise ValueError("--cities must be at least 2")
    if args.pareto_points < 2:
        raise ValueError("--pareto-points must be at least 2")
    output_dir = args.output_dir.resolve()
    sentinel = output_dir / "solve_record.json"
    if sentinel.exists() and not args.overwrite:
        raise FileExistsError(
            f"{sentinel} already exists; use --overwrite or another --output-dir"
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    team_config = TeamConfig()
    graph_config = GraphConfig(n_cities=args.cities, seed=args.seed)
    graph = build_graph(graph_config, team_config)
    if args.depots is not None:
        force_city_depots(graph, args.depots)
    shortest_paths = compute_shortest_paths(graph)
    artifacts, objectives = build_model(
        graph, shortest_paths, team_config, planning_horizon=args.planning_horizon
    )
    artifacts.model.update()
    model_statistics = {
        "nodes": len(graph),
        "edges": graph.number_of_edges(),
        "binary_variables": artifacts.model.NumBinVars,
        "continuous_variables": artifacts.model.NumVars - artifacts.model.NumIntVars,
        "constraints": artifacts.model.NumConstrs,
        "nonzeros": artifacts.model.NumNZs,
    }
    (output_dir / "instance.json").write_text(
        json.dumps(_instance_payload(graph, graph_config, team_config), indent=2, sort_keys=True)
        + "\n"
    )
    (output_dir / "model_statistics.json").write_text(
        json.dumps(model_statistics, indent=2, sort_keys=True) + "\n"
    )
    (output_dir / "experiment_metadata.json").write_text(
        json.dumps(
            {
                **runtime_metadata(PROJECT_ROOT),
                "graph_config": asdict(graph_config),
                "team_config": asdict(team_config),
                "planning_horizon": args.planning_horizon,
                "solver_config": {
                    "time_limit": args.time_limit,
                    "mip_gap": args.mip_gap,
                    "threads": args.threads,
                    "seed": args.gurobi_seed,
                },
                "objective": "maximize final network functionality",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    pos = compute_layout(graph, seed=graph_config.layout_seed)
    save_figure(
        plot_network(graph, pos, node_colors(graph), node_labels(graph)),
        output_dir,
        "network",
    )

    solver_config = SolverConfig(
        time_limit=args.time_limit,
        mip_gap=args.mip_gap,
        threads=args.threads,
        seed=args.gurobi_seed,
        log_to_console=True,
    )
    record = solve_maximum_functionality(
        artifacts.model,
        objectives,
        solver_config,
        output_dir / "gurobi_primary.log",
    )
    (output_dir / "solve_record.json").write_text(
        json.dumps(record.to_dict(), indent=2, sort_keys=True) + "\n"
    )
    if args.write_lp:
        artifacts.model.write(str(output_dir / "bridge.lp"))
    if not record.has_incumbent:
        if record.status == "INFEASIBLE":
            artifacts.model.computeIIS()
            artifacts.model.write(str(output_dir / "infeasible.ilp"))
        print(f"No incumbent solution: {record.status} ({record.error or 'no solver error'})")
        artifacts.model.dispose()
        return 1

    solution = extract_solution(graph, artifacts, objectives, team_config)
    profile = cumulative_profile(graph, solution.schedule, args.planning_horizon)
    write_csv(output_dir / "solution_schedule.csv", [row.to_dict() for row in solution.schedule])
    write_csv(output_dir / "cumulative_profile.csv", [row.to_dict() for row in profile])
    solution_payload = {
        "objective": solution.objective,
        "final_network_functionality": solution.final_functionality,
        "restoration_cost_thousand_usd": solution.cost,
        "restored_bridges": solution.visited_bridges,
        "solver": record.to_dict(),
    }
    (output_dir / "solution_summary.json").write_text(
        json.dumps(solution_payload, indent=2, sort_keys=True) + "\n"
    )
    save_figure(
        plot_routes_by_team(
            graph,
            pos,
            node_colors(graph),
            solution.active_edges_by_team,
            TEAM_COLORS,
        ),
        output_dir,
        "routes",
    )
    save_figure(plot_gantt(solution.schedule, TEAM_COLORS), output_dir, "gantt")
    save_figure(plot_cumulative_profile(profile), output_dir, "cumulative_profile")

    if args.pareto:
        pareto_artifacts, pareto_objectives = build_model(
            graph, shortest_paths, team_config, planning_horizon=args.planning_horizon
        )
        result = pareto_frontier(
            pareto_artifacts,
            pareto_objectives,
            solver_config,
            num_epsilons=args.pareto_points,
            log_dir=output_dir / "pareto_logs",
        )
        write_csv(
            output_dir / "pareto_subproblems.csv",
            [subproblem.to_dict() for subproblem in result.subproblems],
        )
        write_csv(output_dir / "pareto_points.csv", [point.to_dict() for point in result.points])
        endpoints = {
            "maximum_functionality": result.maximum_functionality_endpoint.to_dict(),
            "minimum_cost": (
                result.minimum_cost_endpoint.to_dict()
                if result.minimum_cost_endpoint is not None
                else None
            ),
        }
        (output_dir / "pareto_endpoints.json").write_text(
            json.dumps(endpoints, indent=2, sort_keys=True) + "\n"
        )
        if result.points:
            save_figure(
                plot_pareto(
                    [point.final_functionality for point in result.points],
                    [point.cost_thousand_usd for point in result.points],
                ),
                output_dir,
                "pareto",
            )
        pareto_artifacts.model.dispose()

    print(json.dumps(solution_payload, indent=2, sort_keys=True))
    artifacts.model.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
