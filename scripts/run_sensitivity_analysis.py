"""Run named manuscript sensitivity cases on one parameterized network."""

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
from bridgesnet.graph import build_graph, force_city_depots
from bridgesnet.model import build_model
from bridgesnet.paths import compute_shortest_paths
from bridgesnet.plots import plot_cumulative_profile, plot_gantt
from bridgesnet.results import cumulative_profile, extract_solution
from bridgesnet.scenarios import manuscript_scenarios
from bridgesnet.solver import SolverConfig, runtime_metadata, solve_maximum_functionality


TEAM_COLORS = {"RRU": "#4477AA", "ERT": "#EE6677", "CIRS": "#228833"}
DEFAULT_SCENARIOS = (
    "base",
    "service_time_1_2_2",
    "due_minus_1",
    "initial_bfi_plus_0_10",
)


def parse_range(value: str, cast=float) -> tuple[Any, Any]:
    parts = value.split(":")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("Range must be formatted MIN:MAX")
    try:
        low, high = cast(parts[0]), cast(parts[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid range {value!r}") from exc
    if low > high:
        raise argparse.ArgumentTypeError("Range minimum cannot exceed maximum")
    return low, high


def parse_scenarios(value: str) -> list[str]:
    names = [name.strip() for name in value.split(",") if name.strip()]
    invalid = set(names) - set(DEFAULT_SCENARIOS)
    if not names or invalid:
        raise argparse.ArgumentTypeError(
            f"Scenario names must be drawn from {', '.join(DEFAULT_SCENARIOS)}"
        )
    return names


def write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def save_figure(fig, output_dir: Path, name: str) -> None:
    fig.savefig(output_dir / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(output_dir / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the four named manuscript sensitivity cases on one generated "
            "parameterized network"
        )
    )
    parser.add_argument("--cities", type=int, default=6)
    parser.add_argument("--seed", type=int, default=2)
    parser.add_argument(
        "--depots",
        type=int,
        help="Force C1 through CD to be depots; default preserves seeded selection",
    )
    parser.add_argument("--planning-horizon", type=int, default=8)
    parser.add_argument("--depot-bias", type=float, default=0.90)
    parser.add_argument(
        "--bridge-count-range", type=lambda value: parse_range(value, int), default=(1, 1)
    )
    parser.add_argument("--bfi-range", type=parse_range, default=(0.2, 0.4))
    parser.add_argument(
        "--start-range", type=lambda value: parse_range(value, int), default=(0, 2)
    )
    parser.add_argument(
        "--due-offset-range", type=lambda value: parse_range(value, int), default=(2, 5)
    )
    parser.add_argument(
        "--scenarios", type=parse_scenarios, default=list(DEFAULT_SCENARIOS)
    )
    parser.add_argument("--time-limit", type=float, default=3600.0)
    parser.add_argument("--mip-gap", type=float, default=1e-4)
    parser.add_argument("--threads", type=int, default=0)
    parser.add_argument("--gurobi-seed", type=int, default=0)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("results") / "sensitivity"
    )
    parser.add_argument(
        "--model-stats-only",
        action="store_true",
        help="Build and record every case without calling optimize",
    )
    parser.add_argument("--write-lp", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def _scenario_payload(scenario, graph_config: GraphConfig) -> dict[str, Any]:
    return {
        "name": scenario.name,
        "description": scenario.description,
        "graph_config": asdict(graph_config),
        "team_config": asdict(scenario.team_config),
        "nodes": [
            {"id": str(node), "attributes": dict(scenario.graph.nodes[node])}
            for node in scenario.graph.nodes
        ],
        "edges": [
            {"source": str(source), "target": str(target), "attributes": dict(data)}
            for source, target, data in scenario.graph.edges(data=True)
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cities < 2:
        raise ValueError("--cities must be at least 2")
    if not 0 <= args.depot_bias <= 1:
        raise ValueError("--depot-bias must be in [0, 1]")
    output_dir = args.output_dir.resolve()
    sentinel = output_dir / "sensitivity_results.csv"
    if sentinel.exists() and not args.overwrite:
        raise FileExistsError(
            f"{sentinel} already exists; use --overwrite or another --output-dir"
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    base_team = TeamConfig()
    graph_config = GraphConfig(
        n_cities=args.cities,
        seed=args.seed,
        depot_bias=args.depot_bias,
        bridge_count_range=args.bridge_count_range,
        bridge_bfi_range=args.bfi_range,
        bridge_start_range=args.start_range,
        bridge_due_offset_range=args.due_offset_range,
    )
    base_graph = build_graph(graph_config, base_team)
    if args.depots is not None:
        force_city_depots(base_graph, args.depots)
    scenarios = {
        scenario.name: scenario
        for scenario in manuscript_scenarios(base_graph, base_team)
    }
    solver_config = SolverConfig(
        time_limit=args.time_limit,
        mip_gap=args.mip_gap,
        threads=args.threads,
        seed=args.gurobi_seed,
        log_to_console=True,
    )
    rows: list[dict[str, Any]] = []
    failures = 0
    for name in args.scenarios:
        scenario = scenarios[name]
        scenario_dir = output_dir / name
        scenario_dir.mkdir(parents=True, exist_ok=True)
        (scenario_dir / "scenario_input.json").write_text(
            json.dumps(_scenario_payload(scenario, graph_config), indent=2, sort_keys=True)
            + "\n"
        )
        shortest_paths = compute_shortest_paths(scenario.graph)
        artifacts, objectives = build_model(
            scenario.graph,
            shortest_paths,
            scenario.team_config,
            planning_horizon=args.planning_horizon,
        )
        artifacts.model.update()
        row: dict[str, Any] = {
            "scenario": name,
            "description": scenario.description,
            "cities": args.cities,
            "bridges": objectives.bridges_count,
            "depots": len(artifacts.depots),
            "planning_horizon": args.planning_horizon,
            "binary_variables": artifacts.model.NumBinVars,
            "continuous_variables": artifacts.model.NumVars - artifacts.model.NumIntVars,
            "constraints": artifacts.model.NumConstrs,
            "status": "MODEL_STATS_ONLY" if args.model_stats_only else "NOT_STARTED",
            "solution_count": "",
            "objective_sense": "maximize",
            "final_network_functionality": "",
            "restoration_cost_thousand_usd": "",
            "restored_bridges": "",
            "runtime_seconds": "",
            "best_bound": "",
            "gap_percent": "",
            "error": "",
        }
        if args.write_lp:
            artifacts.model.setObjective(objectives.final_functionality, GRB.MAXIMIZE)
            artifacts.model.write(str(scenario_dir / "model.lp"))
        if not args.model_stats_only:
            record = solve_maximum_functionality(
                artifacts.model,
                objectives,
                solver_config,
                scenario_dir / "gurobi.log",
            )
            row.update(
                {
                    "status": record.status,
                    "solution_count": record.solution_count,
                    "runtime_seconds": record.runtime_seconds or "",
                    "best_bound": record.best_bound if record.best_bound is not None else "",
                    "gap_percent": record.gap_percent if record.gap_percent is not None else "",
                    "error": record.error or "",
                }
            )
            (scenario_dir / "solve_record.json").write_text(
                json.dumps(record.to_dict(), indent=2, sort_keys=True) + "\n"
            )
            if record.has_incumbent:
                solution = extract_solution(
                    scenario.graph, artifacts, objectives, scenario.team_config
                )
                profile = cumulative_profile(
                    scenario.graph, solution.schedule, args.planning_horizon
                )
                row.update(
                    {
                        "final_network_functionality": solution.final_functionality,
                        "restoration_cost_thousand_usd": solution.cost,
                        "restored_bridges": solution.visited_bridges,
                    }
                )
                write_csv(
                    scenario_dir / "solution_schedule.csv",
                    [item.to_dict() for item in solution.schedule],
                )
                write_csv(
                    scenario_dir / "cumulative_profile.csv",
                    [item.to_dict() for item in profile],
                )
                save_figure(
                    plot_gantt(solution.schedule, TEAM_COLORS), scenario_dir, "gantt"
                )
                save_figure(
                    plot_cumulative_profile(profile),
                    scenario_dir,
                    "cumulative_profile",
                )
            else:
                failures += 1
        rows.append(row)
        artifacts.model.dispose()
        write_csv(sentinel, rows)
        print(f"{name}: {row['status']}")

    metadata = {
        **runtime_metadata(PROJECT_ROOT),
        "interpretation": (
            "The default seed-2, six-city network and its reported outputs are one "
            "manuscript presentation case within this parameterized workflow."
        ),
        "graph_config": asdict(graph_config),
        "planning_horizon": args.planning_horizon,
        "selected_scenarios": args.scenarios,
        "solver_config": asdict(solver_config),
        "model_stats_only": args.model_stats_only,
    }
    (output_dir / "experiment_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )
    print(f"Wrote {len(rows)} scenario records to {sentinel}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
