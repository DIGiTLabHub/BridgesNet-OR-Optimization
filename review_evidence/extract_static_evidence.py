"""Export reproducible, non-optimization evidence for CODE_REVIEW_FEEDBACK.md.

This script imports the repository implementation without modifying it.  It does
not call Model.optimize(), because the available Gurobi license is size-limited.
"""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import gurobipy as gp
import matplotlib
import networkx as nx
import numpy as np

from bridgesnet.config import GraphConfig, TeamConfig
from bridgesnet.graph import build_graph, list_bridges, list_cities
from bridgesnet.model import build_model
from bridgesnet.paths import compute_shortest_paths


OUT = ROOT / "review_evidence"


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def force_depot_count(graph, depot_count: int) -> list[str]:
    cities = list_cities(graph)
    if depot_count > len(cities):
        raise ValueError("Depot count exceeds the fixed six-city set")
    depots = cities[:depot_count]
    for city in cities:
        graph.nodes[city]["Depot"] = int(city in depots)
    return depots


def model_row(bridge_count: int, depot_count: int) -> dict:
    if bridge_count % 15:
        raise ValueError("Protocol requires an integer bridges-per-city-pair value")
    per_pair = bridge_count // 15
    graph = build_graph(
        GraphConfig(n_cities=6, seed=2, bridge_count_range=(per_pair, per_pair)),
        TeamConfig(),
    )
    depots = force_depot_count(graph, depot_count)
    shortest_paths = compute_shortest_paths(graph)
    artifacts, _ = build_model(graph, shortest_paths, TeamConfig(), planning_horizon=8)
    model = artifacts.model
    model.update()
    row = {
        "bridges": bridge_count,
        "cities": len(list_cities(graph)),
        "total_nodes": len(graph),
        "depots": depot_count,
        "teams_per_depot": 3,
        "time_points": 8,
        "candidate_directed_arcs": len(graph) * (len(graph) - 1),
        "binary_variables": model.NumBinVars,
        "continuous_variables": model.NumVars - model.NumIntVars,
        "total_variables": model.NumVars,
        "constraints": model.NumConstrs,
        "nonzeros": model.NumNZs,
        "depot_nodes": ";".join(depots),
    }
    model.dispose()
    return row


def main() -> None:
    OUT.mkdir(exist_ok=True)
    team = TeamConfig()
    graph = build_graph(GraphConfig(n_cities=6, seed=2), team)
    shortest_paths = compute_shortest_paths(graph)
    artifacts, _ = build_model(graph, shortest_paths, team, planning_horizon=8)
    model = artifacts.model
    model.update()

    bridges = list_bridges(graph)
    input_rows = []
    for bridge in bridges:
        node = graph.nodes[bridge]
        input_rows.append(
            {
                "bridge": bridge,
                "earliest_start_day": node["Start"],
                "latest_completion_day": node["Due"],
                "initial_bfi": f'{node["BFI"]:.2f}',
                "rru_cost_usd": f'{node["cost"]["RRU"] * 1000:.0f}',
                "rru_post_bfi": f'{node["NewBFI"]["RRU"]:.2f}',
                "ert_cost_usd": f'{node["cost"]["ERT"] * 1000:.0f}',
                "ert_post_bfi": f'{node["NewBFI"]["ERT"]:.2f}',
                "cirs_cost_usd": f'{node["cost"]["CIRS"] * 1000:.0f}',
                "cirs_post_bfi": f'{node["NewBFI"]["CIRS"]:.2f}',
            }
        )
    write_csv(
        OUT / "base_case_inputs.csv",
        list(input_rows[0]),
        input_rows,
    )

    nodes = list(graph.nodes())
    for unit, divisor in (("hours", 1.0), ("days", 24.0)):
        rows = []
        for source in nodes:
            row = {"source": source}
            for target in nodes:
                row[target] = (
                    "0"
                    if source == target
                    else f"{shortest_paths[source, target][1] / divisor:.10f}"
                )
            rows.append(row)
        write_csv(OUT / f"travel_time_matrix_{unit}.csv", ["source", *nodes], rows)

    path_rows = []
    for (source, target), (path, hours) in shortest_paths.items():
        path_rows.append(
            {
                "source": source,
                "target": target,
                "shortest_path": "->".join(path or []),
                "hours": f"{hours:.10f}",
                "days_used_by_model": f"{hours / 24:.10f}",
            }
        )
    write_csv(
        OUT / "shortest_paths.csv",
        ["source", "target", "shortest_path", "hours", "days_used_by_model"],
        path_rows,
    )

    # This schedule is reconstructed from manuscript lines 365-369 and 387-388
    # plus Fig. 4.  It is explicitly not solver-certified in this review.
    claimed_assignments = [
        ("BC1C20", "C1", "ERT", 1, 2.0),
        ("BC1C60", "C1", "ERT", 2, 4.0),
        ("BC4C60", "C1", "RRU", 1, 2.0),
        ("BC2C50", "C1", "RRU", 2, 4.0),
        ("BC4C50", "C1", "CIRS", 1, 3.0),
        ("BC2C30", "C1", "CIRS", 2, 5.0),
        ("BC3C50", "C2", "ERT", 1, 3.0),
        ("BC1C30", "C2", "ERT", 2, 5.0),
        ("BC2C60", "C2", "RRU", 1, 2.0),
        ("BC1C50", "C2", "RRU", 2, 4.0),
        ("BC3C40", "C2", "CIRS", 1, 2.0),
        ("BC1C40", "C2", "CIRS", 2, 4.0),
        ("BC2C40", "C2", "CIRS", 3, 6.0),
    ]
    schedule_rows = []
    for bridge, depot, team_name, route_position, start in claimed_assignments:
        node = graph.nodes[bridge]
        completion = start + team.service_time[team_name]
        schedule_rows.append(
            {
                "bridge": bridge,
                "depot": depot,
                "team": team_name,
                "route_position": route_position,
                "start_day": f"{start:.1f}",
                "completion_day": f"{completion:.1f}",
                "initial_bfi": f'{node["BFI"]:.2f}',
                "restored_bfi": f'{node["NewBFI"][team_name]:.2f}',
                "cost_usd": f'{node["cost"][team_name] * 1000:.0f}',
                "provenance": "reconstructed from manuscript and Fig. 4; not solver-certified",
            }
        )
    write_csv(OUT / "reconstructed_base_schedule.csv", list(schedule_rows[0]), schedule_rows)

    initial_total = sum(graph.nodes[b]["BFI"] for b in bridges)
    cumulative_increment = 0.0
    cumulative_cost = 0.0
    profile_rows = []
    for time in range(8):
        completed = [
            row for row in schedule_rows if float(row["completion_day"]) == float(time)
        ]
        increment = sum(
            float(row["restored_bfi"]) - float(row["initial_bfi"])
            for row in completed
        ) / len(bridges)
        cost_increment = sum(float(row["cost_usd"]) for row in completed)
        cumulative_increment += increment
        cumulative_cost += cost_increment
        profile_rows.append(
            {
                "time_day": time,
                "bridges_completed": ";".join(row["bridge"] for row in completed),
                "incremental_functionality": f"{increment:.6f}",
                "cumulative_functionality": f"{initial_total / len(bridges) + cumulative_increment:.6f}",
                "incremental_cost_usd": f"{cost_increment:.0f}",
                "cumulative_cost_usd": f"{cumulative_cost:.0f}",
                "provenance": "derived from reconstructed_base_schedule.csv; not solver-certified",
            }
        )
    write_csv(OUT / "reconstructed_base_cumulative_profile.csv", list(profile_rows[0]), profile_rows)

    scenario_specs = {
        "service_time_1_2_2": {
            "service": {"RRU": 1.0, "ERT": 2.0, "CIRS": 2.0},
            "bfi_shift": 0.0,
            "assignments": [
                ("BC2C60", "C2", "RRU", 1, 2.0),
                ("BC2C50", "C2", "CIRS", 1, 3.0),
                ("BC1C30", "C2", "ERT", 1, 4.0),
                ("BC2C30", "C2", "RRU", 2, 5.0),
                ("BC4C50", "C1", "RRU", 1, 2.0),
                ("BC1C40", "C1", "CIRS", 1, 3.0),
                ("BC1C50", "C1", "ERT", 1, 3.0),
                ("BC1C60", "C1", "RRU", 2, 4.0),
                ("BC2C40", "C1", "RRU", 3, 6.0),
            ],
        },
        "latest_completion_minus_1": {
            "service": {"RRU": 1.0, "ERT": 1.0, "CIRS": 1.0},
            "bfi_shift": 0.0,
            "assignments": [
                ("BC3C40", "C2", "CIRS", 1, 2.0),
                ("BC3C50", "C2", "ERT", 1, 2.0),
                ("BC5C60", "C2", "RRU", 1, 2.0),
                ("BC1C30", "C2", "RRU", 2, 4.0),
                ("BC1C60", "C2", "ERT", 2, 4.0),
                ("BC2C30", "C2", "CIRS", 2, 4.0),
                ("BC1C40", "C1", "ERT", 1, 2.0),
                ("BC2C60", "C1", "RRU", 1, 2.0),
                ("BC4C50", "C1", "CIRS", 1, 2.0),
                ("BC2C50", "C1", "CIRS", 2, 4.0),
                ("BC2C40", "C1", "ERT", 2, 5.0),
            ],
        },
        "initial_bfi_plus_0_10": {
            "service": {"RRU": 1.0, "ERT": 1.0, "CIRS": 1.0},
            "bfi_shift": 0.10,
            "assignments": [
                ("BC1C20", "C2", "ERT", 1, 2.0),
                ("BC3C40", "C2", "CIRS", 1, 2.0),
                ("BC4C60", "C2", "RRU", 1, 2.0),
                ("BC1C30", "C2", "RRU", 2, 4.0),
                ("BC1C40", "C2", "CIRS", 2, 4.0),
                ("BC1C50", "C2", "ERT", 2, 4.0),
                ("BC2C40", "C2", "CIRS", 3, 6.0),
                ("BC2C60", "C1", "ERT", 1, 2.0),
                ("BC4C50", "C1", "CIRS", 1, 2.0),
                ("BC5C60", "C1", "RRU", 1, 2.0),
                ("BC1C60", "C1", "RRU", 2, 4.0),
                ("BC2C30", "C1", "CIRS", 2, 4.0),
                ("BC2C50", "C1", "ERT", 2, 4.0),
            ],
        },
    }
    scenario_rows = []
    scenario_summary_rows = []
    for scenario, spec in scenario_specs.items():
        restored_increment_total = 0.0
        total_cost = 0.0
        scenario_initial_total = sum(
            min(round(graph.nodes[b]["BFI"] + spec["bfi_shift"], 2), 1)
            for b in bridges
        )
        for bridge, depot, team_name, route_position, start in spec["assignments"]:
            initial = min(round(graph.nodes[bridge]["BFI"] + spec["bfi_shift"], 2), 1)
            restored = min(round(initial + team.delta_functionality[team_name], 2), 1)
            cost = round(
                team.base_cost[team_name] * (1 + team.alpha * (1 - initial)), 2
            ) * 1000
            completion = start + spec["service"][team_name]
            restored_increment_total += restored - initial
            total_cost += cost
            scenario_rows.append(
                {
                    "scenario": scenario,
                    "bridge": bridge,
                    "depot": depot,
                    "team": team_name,
                    "route_position": route_position,
                    "start_day": f"{start:.1f}",
                    "completion_day": f"{completion:.1f}",
                    "initial_bfi": f"{initial:.2f}",
                    "restored_bfi": f"{restored:.2f}",
                    "cost_usd": f"{cost:.0f}",
                    "provenance": "reconstructed from archived Gantt figure; not solver-certified",
                }
            )
        scenario_summary_rows.append(
            {
                "scenario": scenario,
                "bridges_in_figure": len(spec["assignments"]),
                "recalculated_cost_usd": f"{total_cost:.0f}",
                "recalculated_final_functionality": f"{(scenario_initial_total + restored_increment_total) / len(bridges):.6f}",
                "solver_status": "not available",
                "runtime_seconds": "",
                "gap_percent": "",
                "provenance": "figure reconstruction and authoritative input formulas; not solver-certified",
            }
        )
    write_csv(
        OUT / "reconstructed_sensitivity_schedules.csv",
        list(scenario_rows[0]),
        scenario_rows,
    )
    write_csv(
        OUT / "reconstructed_sensitivity_summary.csv",
        list(scenario_summary_rows[0]),
        scenario_summary_rows,
    )

    scalability_rows = [
        model_row(15, 2),
        model_row(30, 2),
        model_row(45, 3),
        model_row(60, 4),
    ]
    write_csv(OUT / "scalability_model_sizes.csv", list(scalability_rows[0]), scalability_rows)

    figure_map = {
        3: "Pareto Frontier.png",
        4: "Gatt Chart.png",
        5: "Trajectory.png",
        6: "Service Time Variation.png",
        7: "Service Time Variations (Team).png",
        8: "Time Window Reduction.png",
        9: "Gantt Chart when Time Window Reduced .png",
        10: "Initial BFI Increased.png",
        11: "Gantt Chart when BFI Increased.png",
    }
    figure_rows = []
    for number, filename in figure_map.items():
        path = ROOT / "ASCE_submission" / "Revision01" / "Figures" / filename
        figure_rows.append(
            {
                "figure": number,
                "path": str(path.relative_to(ROOT)),
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() else "",
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "",
            }
        )
    write_csv(OUT / "figure_inventory.csv", list(figure_rows[0]), figure_rows)

    summary = {
        "python": sys.version,
        "platform": platform.platform(),
        "gurobi": gp.gurobi.version(),
        "networkx": nx.__version__,
        "numpy": np.__version__,
        "matplotlib": matplotlib.__version__,
        "base_case": {
            "nodes": len(graph),
            "cities": list_cities(graph),
            "bridges": bridges,
            "depots": artifacts.depots,
            "teams": team.teams,
            "time_points": list(range(artifacts.planning_horizon)),
            "x_variables": len(artifacts.x),
            "y_variables": len(artifacts.y),
            "s_variables": len(artifacts.s),
            "NumVars": model.NumVars,
            "NumBinVars": model.NumBinVars,
            "NumIntVars": model.NumIntVars,
            "NumConstrs": model.NumConstrs,
            "NumNZs": model.NumNZs,
            "average_initial_bfi": sum(graph.nodes[b]["BFI"] for b in bridges) / len(bridges),
        },
        "gurobi_parameters": {
            "ModelSense_after_build": model.ModelSense,
            "Threads": model.Params.Threads,
            "TimeLimit": str(model.Params.TimeLimit),
            "Seed": model.Params.Seed,
            "MIPGap": model.Params.MIPGap,
            "MIPGapAbs": model.Params.MIPGapAbs,
            "FeasibilityTol": model.Params.FeasibilityTol,
            "IntFeasTol": model.Params.IntFeasTol,
            "OptimalityTol": model.Params.OptimalityTol,
        },
        "reduced_deadline_windows_valid": all(
            graph.nodes[b]["Due"] - 1 >= graph.nodes[b]["Start"] for b in bridges
        ),
    }
    (OUT / "static_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    model.dispose()


if __name__ == "__main__":
    main()
