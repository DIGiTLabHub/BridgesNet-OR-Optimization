"""Run the reproducible BridgesNet MILP scalability experiment.

Each reported run solves one maximum-final-functionality problem.  The script
does not run the epsilon-constraint Pareto procedure, so its runtimes must not
be mixed with complete-frontier runtimes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shlex
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import gurobipy as gp


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bridgesnet.config import GraphConfig, TeamConfig
from bridgesnet.graph import build_graph, force_city_depots, list_bridges, list_cities
from bridgesnet.model import build_model
from bridgesnet.paths import compute_shortest_paths
from bridgesnet.solver import SolverConfig, runtime_metadata, solve_maximum_functionality


DEFAULT_INSTANCE_SPECS = ((15, 2), (30, 2), (45, 3), (60, 4))
RUN_FIELDNAMES = [
    "bridges",
    "depots",
    "replication",
    "graph_seed",
    "instance_sha256",
    "total_nodes",
    "candidate_directed_arcs",
    "binary_variables",
    "continuous_variables",
    "constraints",
    "nonzeros",
    "status_code",
    "status",
    "runtime_seconds",
    "solution_count",
    "incumbent_objective",
    "best_bound",
    "gap_percent",
    "restoration_cost_thousand_usd",
    "restored_bridges",
    "error",
    "solver_log",
    "instance_file",
]


def parse_instance_specs(value: str) -> list[tuple[int, int]]:
    """Parse comma-separated BRIDGES:DEPOTS pairs."""

    specs: list[tuple[int, int]] = []
    for token in value.split(","):
        token = token.strip()
        if not token:
            continue
        parts = token.split(":")
        if len(parts) != 2:
            raise argparse.ArgumentTypeError(
                "Instance sizes must be comma-separated BRIDGES:DEPOTS pairs"
            )
        try:
            bridges, depots = (int(part) for part in parts)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"Invalid integer pair: {token!r}"
            ) from exc
        validate_instance_spec(bridges, depots)
        specs.append((bridges, depots))
    if not specs:
        raise argparse.ArgumentTypeError("At least one instance size is required")
    if len(set(specs)) != len(specs):
        raise argparse.ArgumentTypeError("Duplicate instance sizes are not allowed")
    return specs


def validate_instance_spec(bridge_count: int, depot_count: int) -> None:
    """Validate sizes for the fixed six-city scalability protocol."""

    if bridge_count <= 0 or bridge_count % 15 != 0:
        raise argparse.ArgumentTypeError(
            "Bridge count must be a positive multiple of 15 for six city pairs"
        )
    if not 1 <= depot_count <= 6:
        raise argparse.ArgumentTypeError("Depot count must be between 1 and 6")


def force_depots(graph, depot_count: int) -> list[str]:
    """Select the first D city nodes as depots, deterministically."""

    return force_city_depots(graph, depot_count)


def build_scalability_graph(
    bridge_count: int,
    depot_count: int,
    seed: int,
    team_config: TeamConfig | None = None,
):
    """Build one exact-size synthetic graph for the scalability protocol."""

    validate_instance_spec(bridge_count, depot_count)
    team_config = team_config or TeamConfig()
    bridges_per_city_pair = bridge_count // 15
    graph_config = GraphConfig(
        n_cities=6,
        seed=seed,
        bridge_count_range=(bridges_per_city_pair, bridges_per_city_pair),
    )
    graph = build_graph(graph_config, team_config)
    depots = force_depots(graph, depot_count)
    actual_bridges = len(list_bridges(graph))
    if actual_bridges != bridge_count:
        raise RuntimeError(
            f"Generated {actual_bridges} bridges; expected {bridge_count}"
        )
    return graph, graph_config, depots


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def instance_payload(
    graph,
    graph_config: GraphConfig,
    team_config: TeamConfig,
    depots: Sequence[str],
    planning_horizon: int,
) -> dict[str, Any]:
    """Return a complete, JSON-serializable snapshot of a generated instance."""

    nodes = [
        {"id": str(node), "attributes": _jsonable(dict(graph.nodes[node]))}
        for node in graph.nodes()
    ]
    edges = [
        {
            "source": str(source),
            "target": str(target),
            "attributes": _jsonable(dict(attributes)),
        }
        for source, target, attributes in graph.edges(data=True)
    ]
    return {
        "protocol": {
            "physical_network": "six cities; equal bridges per city pair",
            "depot_selection": "first D city nodes",
            "planning_horizon_time_points": list(range(planning_horizon)),
            "travel_time": "deterministic all-pairs shortest path; edge length/speed in hours, divided by 24 in MILP",
            "reported_runtime_scope": "one maximum-final-functionality MILP",
        },
        "graph_config": _jsonable(graph_config.__dict__),
        "team_config": _jsonable(team_config.__dict__),
        "depots": list(depots),
        "nodes": nodes,
        "edges": edges,
    }


def write_instance(path: Path, payload: dict[str, Any]) -> str:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.write_bytes(encoded)
    return hashlib.sha256(encoded).hexdigest()


def write_csv(path: Path, rows: Sequence[dict[str, Any]], fieldnames: Sequence[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def model_statistics(model: gp.Model, graph) -> dict[str, int]:
    model.update()
    return {
        "total_nodes": len(graph),
        "candidate_directed_arcs": len(graph) * (len(graph) - 1),
        "binary_variables": model.NumBinVars,
        "continuous_variables": model.NumVars - model.NumIntVars,
        "constraints": model.NumConstrs,
        "nonzeros": model.NumNZs,
    }


def selected_bridge_count(artifacts) -> int:
    selected = {
        bridge
        for (bridge, _, _), variable in artifacts.y.items()
        if variable.X > 0.5
    }
    return len(selected)


def numeric_values(rows: Iterable[dict[str, Any]], field: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = row.get(field)
        if value not in (None, ""):
            values.append(float(value))
    return values


def summarize_runs(
    rows: Sequence[dict[str, Any]],
    specs: Sequence[tuple[int, int]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(int(row["bridges"]), int(row["depots"]))].append(row)

    summaries: list[dict[str, Any]] = []
    for bridges, depots in specs:
        group = grouped[(bridges, depots)]
        if not group:
            continue
        runtimes = numeric_values(group, "runtime_seconds")
        gaps = numeric_values(group, "gap_percent")
        objectives = numeric_values(group, "incumbent_objective")
        costs = numeric_values(group, "restoration_cost_thousand_usd")
        statuses = Counter(str(row["status"]) for row in group)
        first = group[0]
        summaries.append(
            {
                "bridges": bridges,
                "depots": depots,
                "replications": len(group),
                "binary_variables": first["binary_variables"],
                "continuous_variables": first["continuous_variables"],
                "constraints": first["constraints"],
                "runtime_median_seconds": (
                    round(statistics.median(runtimes), 6) if runtimes else ""
                ),
                "gap_max_percent": round(max(gaps), 6) if gaps else "",
                "objective_median": (
                    round(statistics.median(objectives), 6) if objectives else ""
                ),
                "cost_median_thousand_usd": (
                    round(statistics.median(costs), 6) if costs else ""
                ),
                "optimal_runs": statuses.get("OPTIMAL", 0),
                "status_summary": "; ".join(
                    f"{status}={count}" for status, count in sorted(statuses.items())
                ),
            }
        )
    return summaries


def write_markdown_table(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    lines = [
        "# Scalability experiment summary",
        "",
        "Each runtime is the median across replications for one maximum-final-functionality MILP. Gap is the maximum final gap among replications with an incumbent.",
        "",
        "| Bridges | Depots | Binary variables | Continuous variables | Constraints | Median runtime (s) | Maximum gap (%) | Solver status |",
        "|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {bridges} | {depots} | {binary_variables} | "
            "{continuous_variables} | {constraints} | {runtime_median_seconds} | "
            "{gap_max_percent} | {status_summary} |".format(**row)
        )
    path.write_text("\n".join(lines) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run exact-size replicated scalability experiments. Each run solves one "
            "maximum-final-functionality MILP, not a Pareto frontier."
        )
    )
    parser.add_argument(
        "--instances",
        type=parse_instance_specs,
        default=list(DEFAULT_INSTANCE_SPECS),
        help="Comma-separated BRIDGES:DEPOTS pairs (default: 15:2,30:2,45:3,60:4)",
    )
    parser.add_argument("--replications", type=int, default=10)
    parser.add_argument("--seed-start", type=int, default=20260806)
    parser.add_argument("--planning-horizon", type=int, default=8)
    parser.add_argument("--time-limit", type=float, default=3600.0)
    parser.add_argument("--mip-gap", type=float, default=1e-4)
    parser.add_argument("--threads", type=int, default=10)
    parser.add_argument("--gurobi-seed", type=int, default=20260806)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("results") / "scalability"
    )
    parser.add_argument(
        "--model-stats-only",
        action="store_true",
        help="Build models and export counts/instances without presolving or optimizing",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacement of summary files with the same output path",
    )
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.replications <= 0:
        raise ValueError("--replications must be positive")
    if args.planning_horizon <= 0:
        raise ValueError("--planning-horizon must be positive")
    if args.time_limit <= 0:
        raise ValueError("--time-limit must be positive")
    if not 0 <= args.mip_gap < 1:
        raise ValueError("--mip-gap must be in [0,1)")
    if args.threads < 0:
        raise ValueError("--threads cannot be negative")
    if not 0 <= args.gurobi_seed <= 2_000_000_000:
        raise ValueError("--gurobi-seed must be in [0,2000000000]")


def prepare_output(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    output_dir = args.output_dir.resolve()
    summary_targets = [
        output_dir / "scalability_runs.csv",
        output_dir / "scalability_summary.csv",
        output_dir / "scalability_table.md",
        output_dir / "experiment_metadata.json",
    ]
    existing = [path for path in summary_targets if path.exists()]
    if existing and not args.overwrite:
        names = ", ".join(path.name for path in existing)
        raise FileExistsError(
            f"Output files already exist ({names}); use --overwrite or another --output-dir"
        )
    log_dir = output_dir / "logs"
    instance_dir = output_dir / "instances"
    log_dir.mkdir(parents=True, exist_ok=True)
    instance_dir.mkdir(parents=True, exist_ok=True)
    return output_dir, log_dir, instance_dir


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate_args(args)
    output_dir, log_dir, instance_dir = prepare_output(args)
    team_config = TeamConfig()
    solver_config = SolverConfig(
        time_limit=args.time_limit,
        mip_gap=args.mip_gap,
        threads=args.threads,
        seed=args.gurobi_seed,
        log_to_console=False,
    )
    started = datetime.now(timezone.utc)

    metadata = {
        **runtime_metadata(PROJECT_ROOT),
        "started_utc": started.isoformat(),
        "command": shlex.join([sys.executable, *sys.argv]),
        "experiment_scope": "one maximum-final-functionality MILP per replication",
        "complete_pareto_procedure": False,
        "instances": args.instances,
        "replications": args.replications,
        "graph_seeds": [args.seed_start + index for index in range(args.replications)],
        "planning_horizon_time_points": list(range(args.planning_horizon)),
        "gurobi_parameters": {
            "TimeLimit": args.time_limit,
            "MIPGap": args.mip_gap,
            "Threads": args.threads,
            "Seed": args.gurobi_seed,
            "LogToConsole": 0,
        },
        "model_stats_only": args.model_stats_only,
        "generation_protocol": {
            "cities": 6,
            "bridges_per_city_pair": "bridge_count / 15",
            "depot_nodes": "C1 through CD",
            "teams_per_depot": list(team_config.teams),
            "graph_and_team_defaults": "src/bridgesnet/config.py",
            "cost_and_post_bfi_generation": "src/bridgesnet/graph.py",
            "shortest_paths": "src/bridgesnet/paths.py",
        },
    }
    metadata_path = output_dir / "experiment_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")

    rows: list[dict[str, Any]] = []
    runs_path = output_dir / "scalability_runs.csv"
    for bridge_count, depot_count in args.instances:
        for replication in range(1, args.replications + 1):
            graph_seed = args.seed_start + replication - 1
            stem = (
                f"b{bridge_count:03d}_d{depot_count}_r{replication:02d}_s{graph_seed}"
            )
            instance_path = instance_dir / f"instance_{stem}.json"
            log_path = log_dir / f"gurobi_{stem}.log"
            graph, graph_config, depots = build_scalability_graph(
                bridge_count, depot_count, graph_seed, team_config
            )
            payload = instance_payload(
                graph,
                graph_config,
                team_config,
                depots,
                args.planning_horizon,
            )
            instance_digest = write_instance(instance_path, payload)
            shortest_paths = compute_shortest_paths(graph)
            artifacts, objectives = build_model(
                graph,
                shortest_paths,
                team_config,
                planning_horizon=args.planning_horizon,
            )
            model = artifacts.model
            stats = model_statistics(model, graph)
            row: dict[str, Any] = {
                "bridges": bridge_count,
                "depots": depot_count,
                "replication": replication,
                "graph_seed": graph_seed,
                "instance_sha256": instance_digest,
                **stats,
                "status_code": "",
                "status": "MODEL_STATS_ONLY" if args.model_stats_only else "NOT_STARTED",
                "runtime_seconds": "",
                "solution_count": "",
                "incumbent_objective": "",
                "best_bound": "",
                "gap_percent": "",
                "restoration_cost_thousand_usd": "",
                "restored_bridges": "",
                "error": "",
                "solver_log": (
                    "" if args.model_stats_only else str(log_path.relative_to(output_dir))
                ),
                "instance_file": str(instance_path.relative_to(output_dir)),
            }

            try:
                if not args.model_stats_only:
                    record = solve_maximum_functionality(
                        model,
                        objectives,
                        solver_config,
                        log_path=log_path,
                    )
                    row["status_code"] = record.status_code or ""
                    row["status"] = record.status
                    row["runtime_seconds"] = (
                        round(record.runtime_seconds, 6)
                        if record.runtime_seconds is not None
                        else ""
                    )
                    row["solution_count"] = record.solution_count
                    row["best_bound"] = (
                        record.best_bound if record.best_bound is not None else ""
                    )
                    row["error"] = record.error or ""
                    if record.has_incumbent:
                        row["incumbent_objective"] = record.incumbent_objective
                        row["gap_percent"] = record.gap_percent
                        row["restoration_cost_thousand_usd"] = (
                            objectives.cost.getValue()
                        )
                        row["restored_bridges"] = selected_bridge_count(artifacts)
            except gp.GurobiError as exc:
                row["status"] = "GUROBI_ERROR"
                row["error"] = f"{exc.errno}: {exc}"
            except Exception as exc:  # preserve evidence for an unexpected failed run
                row["status"] = "ERROR"
                row["error"] = f"{type(exc).__name__}: {exc}"
            finally:
                model.dispose()

            rows.append(row)
            write_csv(runs_path, rows, RUN_FIELDNAMES)
            print(
                f"B={bridge_count} D={depot_count} replication={replication} "
                f"seed={graph_seed} status={row['status']}"
            )

    summaries = summarize_runs(rows, args.instances)
    summary_path = output_dir / "scalability_summary.csv"
    if summaries:
        write_csv(summary_path, summaries, list(summaries[0].keys()))
    write_markdown_table(output_dir / "scalability_table.md", summaries)

    metadata["finished_utc"] = datetime.now(timezone.utc).isoformat()
    metadata["run_count"] = len(rows)
    metadata["status_counts"] = dict(Counter(str(row["status"]) for row in rows))
    failed_runs = [
        row for row in rows if row["status"] in {"GUROBI_ERROR", "ERROR"}
    ]
    metadata["completed_without_run_errors"] = not failed_runs
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {len(rows)} run records to {runs_path}")
    print(f"Wrote {len(summaries)} summary rows to {summary_path}")
    if failed_runs:
        print(f"Experiment recorded {len(failed_runs)} failed run(s); see the run CSV")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
