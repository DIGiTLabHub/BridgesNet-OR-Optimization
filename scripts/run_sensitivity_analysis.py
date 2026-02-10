"""Run parametric sensitivity studies and report summary results."""

from __future__ import annotations

import argparse
import csv
import itertools
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import matplotlib

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.rcParams["font.family"] = "Arial"

import matplotlib.pyplot as plt
import numpy as np
from gurobipy import GRB

from bridgesnet.config import GraphConfig, TeamConfig
from bridgesnet.graph import build_graph
from bridgesnet.model import build_model
from bridgesnet.paths import compute_shortest_paths
from bridgesnet.results import extract_solution


DEFAULT_SWEEP = {
    "alpha": [0.3, 0.5, 0.7],
    "planning_horizon": [6, 8, 10],
    "depot_bias": [0.7, 0.9],
    "bridge_bfi_range": [(0.1, 0.3), (0.2, 0.4)],
    "base_cost_scale": [0.8, 1.0, 1.2],
    "delta_functionality_scale": [0.8, 1.0, 1.2],
    "seed": [1, 2, 3],
}


def save_figure(fig, output_dir: Path, name: str) -> None:
    fig.savefig(output_dir / f"{name}.png", dpi=200)
    fig.savefig(output_dir / f"{name}.pdf")


def _parse_float_list(value: str) -> List[float]:
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def _parse_int_list(value: str) -> List[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def _parse_range_list(value: str) -> List[Tuple[float, float]]:
    items = []
    for token in value.split(","):
        token = token.strip()
        if not token:
            continue
        parts = token.split(":")
        if len(parts) != 2:
            raise ValueError("Range list items must be formatted as low:high")
        items.append((float(parts[0]), float(parts[1])))
    return items


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run parametric sensitivity analysis sweeps"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results") / "sensitivity",
        help="Output folder for CSV and plots",
    )
    parser.add_argument(
        "--cities", type=int, default=6, help="Number of cities"
    )
    parser.add_argument(
        "--alpha",
        type=_parse_float_list,
        help="Comma-separated alpha values (default: 0.3,0.5,0.7)",
    )
    parser.add_argument(
        "--planning-horizon",
        type=_parse_int_list,
        help="Comma-separated planning horizons (default: 6,8,10)",
    )
    parser.add_argument(
        "--depot-bias",
        type=_parse_float_list,
        help="Comma-separated depot bias values (default: 0.7,0.9)",
    )
    parser.add_argument(
        "--bridge-bfi-range",
        type=_parse_range_list,
        help="Comma-separated low:high pairs (default: 0.1:0.3,0.2:0.4)",
    )
    parser.add_argument(
        "--base-cost-scale",
        type=_parse_float_list,
        help="Comma-separated base cost scales (default: 0.8,1.0,1.2)",
    )
    parser.add_argument(
        "--delta-functionality-scale",
        type=_parse_float_list,
        help="Comma-separated delta functionality scales (default: 0.8,1.0,1.2)",
    )
    parser.add_argument(
        "--seed",
        type=_parse_int_list,
        help="Comma-separated seeds (default: 1,2,3)",
    )
    return parser


def _scaled_team_config(
    base: TeamConfig, base_cost_scale: float, delta_scale: float, alpha: float
) -> TeamConfig:
    base_cost = {
        team: value * base_cost_scale for team, value in base.base_cost.items()
    }
    delta_functionality = {
        team: value * delta_scale
        for team, value in base.delta_functionality.items()
    }
    return TeamConfig(
        teams=list(base.teams),
        base_cost=base_cost,
        delta_functionality=delta_functionality,
        service_time=dict(base.service_time),
        alpha=alpha,
    )


def _write_csv(rows: List[Dict[str, float | int | str]], output_path: Path) -> None:
    if not rows:
        return
    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _group_mean(
    rows: Iterable[Dict[str, float | int | str]],
    key: str,
    metric: str,
) -> Tuple[List[str], List[float]]:
    buckets: Dict[str, List[float]] = {}
    for row in rows:
        if row.get("status") != "optimal":
            continue
        bucket_key = str(row[key])
        buckets.setdefault(bucket_key, []).append(float(row[metric]))

    labels = list(buckets.keys())
    values = [float(np.mean(buckets[label])) for label in labels]
    return labels, values


def _plot_metric_by_param(
    rows: Iterable[Dict[str, float | int | str]],
    param: str,
    metric: str,
    output_dir: Path,
) -> None:
    labels, values = _group_mean(rows, param, metric)
    if not labels:
        return
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(labels, values, marker="o")
    ax.set_title(f"Mean {metric} vs {param}")
    ax.set_xlabel(param)
    ax.set_ylabel(metric)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    save_figure(fig, output_dir, f"summary_{param}_{metric}")


def _plot_metric_histogram(
    rows: Iterable[Dict[str, float | int | str]],
    metric: str,
    output_dir: Path,
) -> None:
    values = [
        float(row[metric])
        for row in rows
        if row.get("status") == "optimal" and row.get(metric) not in ("", None)
    ]
    if not values:
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(values, bins=12, color="steelblue", edgecolor="black", alpha=0.8)
    ax.set_title(f"Histogram of {metric}")
    ax.set_xlabel(metric)
    ax.set_ylabel("Count")
    ax.grid(True, linestyle="--", alpha=0.3)
    fig.tight_layout()
    save_figure(fig, output_dir, f"hist_{metric}")


def _plot_metric_boxplot(
    rows: Iterable[Dict[str, float | int | str]],
    param: str,
    metric: str,
    output_dir: Path,
) -> None:
    buckets: Dict[str, List[float]] = {}
    for row in rows:
        if row.get("status") != "optimal":
            continue
        bucket_key = str(row[param])
        buckets.setdefault(bucket_key, []).append(float(row[metric]))

    if not buckets:
        return
    labels = list(buckets.keys())
    data = [buckets[label] for label in labels]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.boxplot(data, labels=labels, showmeans=True)
    ax.set_title(f"{metric} by {param}")
    ax.set_xlabel(param)
    ax.set_ylabel(metric)
    ax.grid(True, linestyle="--", alpha=0.3)
    fig.tight_layout()
    save_figure(fig, output_dir, f"box_{param}_{metric}")


def main() -> None:
    args = build_parser().parse_args()
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    base_team = TeamConfig()

    sweep = {
        "alpha": args.alpha or DEFAULT_SWEEP["alpha"],
        "planning_horizon": args.planning_horizon or DEFAULT_SWEEP["planning_horizon"],
        "depot_bias": args.depot_bias or DEFAULT_SWEEP["depot_bias"],
        "bridge_bfi_range": args.bridge_bfi_range or DEFAULT_SWEEP["bridge_bfi_range"],
        "base_cost_scale": args.base_cost_scale or DEFAULT_SWEEP["base_cost_scale"],
        "delta_functionality_scale": args.delta_functionality_scale
        or DEFAULT_SWEEP["delta_functionality_scale"],
        "seed": args.seed or DEFAULT_SWEEP["seed"],
    }
    rows: List[Dict[str, float | int | str]] = []

    keys = [
        "alpha",
        "planning_horizon",
        "depot_bias",
        "bridge_bfi_range",
        "base_cost_scale",
        "delta_functionality_scale",
        "seed",
    ]
    values = [sweep[key] for key in keys]

    for (
        alpha,
        planning_horizon,
        depot_bias,
        bridge_bfi_range,
        base_cost_scale,
        delta_scale,
        seed,
    ) in itertools.product(*values):
        team_config = _scaled_team_config(
            base_team, base_cost_scale, delta_scale, alpha
        )
        graph_config = GraphConfig(
            n_cities=args.cities,
            seed=seed,
            depot_bias=depot_bias,
            bridge_bfi_range=bridge_bfi_range,
        )
        G = build_graph(graph_config, team_config)
        shortest_paths = compute_shortest_paths(G)
        artifacts, objectives = build_model(
            G, shortest_paths, team_config, planning_horizon=planning_horizon
        )

        artifacts.model.setObjective(
            (objectives.resilience + objectives.resilience_raw)
            / objectives.bridges_count
        )
        artifacts.model.optimize()

        status = artifacts.model.Status
        if status == GRB.INFEASIBLE:
            rows.append(
                {
                    "alpha": alpha,
                    "planning_horizon": planning_horizon,
                    "depot_bias": depot_bias,
                    "bridge_bfi_low": bridge_bfi_range[0],
                    "bridge_bfi_high": bridge_bfi_range[1],
                    "base_cost_scale": base_cost_scale,
                    "delta_functionality_scale": delta_scale,
                    "seed": seed,
                    "objective": "",
                    "cost": "",
                    "resilience": "",
                    "visited_bridges": "",
                    "status": "infeasible",
                }
            )
            continue

        if status not in (GRB.OPTIMAL, GRB.SUBOPTIMAL):
            rows.append(
                {
                    "alpha": alpha,
                    "planning_horizon": planning_horizon,
                    "depot_bias": depot_bias,
                    "bridge_bfi_low": bridge_bfi_range[0],
                    "bridge_bfi_high": bridge_bfi_range[1],
                    "base_cost_scale": base_cost_scale,
                    "delta_functionality_scale": delta_scale,
                    "seed": seed,
                    "objective": "",
                    "cost": "",
                    "resilience": "",
                    "visited_bridges": "",
                    "status": f"status_{status}",
                }
            )
            continue

        solution = extract_solution(G, artifacts, objectives, team_config)
        rows.append(
            {
                "alpha": alpha,
                "planning_horizon": planning_horizon,
                "depot_bias": depot_bias,
                "bridge_bfi_low": bridge_bfi_range[0],
                "bridge_bfi_high": bridge_bfi_range[1],
                "base_cost_scale": base_cost_scale,
                "delta_functionality_scale": delta_scale,
                "seed": seed,
                "objective": round(solution.objective, 6),
                "cost": round(solution.cost, 6),
                "resilience": round(solution.resilience, 6),
                "visited_bridges": solution.visited_bridges,
                "status": "optimal",
            }
        )

    csv_path = output_dir / "sensitivity_results.csv"
    _write_csv(rows, csv_path)

    for param in [
        "alpha",
        "planning_horizon",
        "depot_bias",
        "bridge_bfi_low",
        "bridge_bfi_high",
        "base_cost_scale",
        "delta_functionality_scale",
    ]:
        _plot_metric_by_param(rows, param, "resilience", output_dir)
        _plot_metric_by_param(rows, param, "cost", output_dir)
        _plot_metric_boxplot(rows, param, "resilience", output_dir)
        _plot_metric_boxplot(rows, param, "cost", output_dir)

    _plot_metric_histogram(rows, "resilience", output_dir)
    _plot_metric_histogram(rows, "cost", output_dir)

    print(f"Saved {len(rows)} rows to {csv_path}")


if __name__ == "__main__":
    main()
