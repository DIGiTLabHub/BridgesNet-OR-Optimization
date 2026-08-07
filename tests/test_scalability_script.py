"""Focused tests for the standalone scalability experiment driver."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import pytest

from bridgesnet.graph import list_bridges, list_cities


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_sensitivity_analysis_scalability.py"
SPEC = importlib.util.spec_from_file_location("scalability_driver", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
scalability_driver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scalability_driver)


def test_parse_instance_specs() -> None:
    assert scalability_driver.parse_instance_specs("15:2,30:2,45:3,60:4") == [
        (15, 2),
        (30, 2),
        (45, 3),
        (60, 4),
    ]

    with pytest.raises(argparse.ArgumentTypeError):
        scalability_driver.parse_instance_specs("20:2")
    with pytest.raises(argparse.ArgumentTypeError):
        scalability_driver.parse_instance_specs("15:7")
    with pytest.raises(argparse.ArgumentTypeError):
        scalability_driver.parse_instance_specs("15:2,15:2")


def test_build_scalability_graph_has_exact_size_and_depots() -> None:
    graph, graph_config, depots = scalability_driver.build_scalability_graph(
        bridge_count=30,
        depot_count=3,
        seed=20260806,
    )

    assert graph_config.n_cities == 6
    assert graph_config.bridge_count_range == (2, 2)
    assert len(list_cities(graph)) == 6
    assert len(list_bridges(graph)) == 30
    assert len(graph) == 36
    assert graph.number_of_edges() == 90
    assert depots == ["C1", "C2", "C3"]
    assert [
        city for city in list_cities(graph) if graph.nodes[city]["Depot"] == 1
    ] == depots


def test_instance_snapshot_is_deterministic(tmp_path: Path) -> None:
    graph1, config1, depots1 = scalability_driver.build_scalability_graph(15, 2, 7)
    graph2, config2, depots2 = scalability_driver.build_scalability_graph(15, 2, 7)
    team = scalability_driver.TeamConfig()
    payload1 = scalability_driver.instance_payload(
        graph1, config1, team, depots1, planning_horizon=8
    )
    payload2 = scalability_driver.instance_payload(
        graph2, config2, team, depots2, planning_horizon=8
    )

    digest1 = scalability_driver.write_instance(tmp_path / "one.json", payload1)
    digest2 = scalability_driver.write_instance(tmp_path / "two.json", payload2)
    assert digest1 == digest2
    assert (tmp_path / "one.json").read_bytes() == (tmp_path / "two.json").read_bytes()


def test_summarize_runs_uses_median_runtime_and_maximum_gap() -> None:
    rows = [
        {
            "bridges": 15,
            "depots": 2,
            "binary_variables": 3240,
            "continuous_variables": 90,
            "constraints": 3267,
            "runtime_seconds": 8.0,
            "gap_percent": 0.0,
            "incumbent_objective": 0.79,
            "restoration_cost_thousand_usd": 50.05,
            "status": "OPTIMAL",
        },
        {
            "bridges": 15,
            "depots": 2,
            "binary_variables": 3240,
            "continuous_variables": 90,
            "constraints": 3267,
            "runtime_seconds": 12.0,
            "gap_percent": 2.5,
            "incumbent_objective": 0.78,
            "restoration_cost_thousand_usd": 48.0,
            "status": "TIME_LIMIT",
        },
    ]

    summary = scalability_driver.summarize_runs(rows, [(15, 2)])[0]
    assert summary["runtime_median_seconds"] == 10.0
    assert summary["gap_max_percent"] == 2.5
    assert summary["objective_median"] == 0.785
    assert summary["optimal_runs"] == 1
    assert summary["status_summary"] == "OPTIMAL=1; TIME_LIMIT=1"
