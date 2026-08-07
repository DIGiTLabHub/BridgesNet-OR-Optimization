"""Focused regression tests for the corrected optimization workflow."""

from __future__ import annotations

import networkx as nx
import pytest
from gurobipy import GRB

from bridgesnet.config import GraphConfig, TeamConfig
from bridgesnet.graph import build_graph, list_bridges
from bridgesnet.model import build_model
from bridgesnet.pareto import pareto_frontier
from bridgesnet.paths import compute_shortest_paths
from bridgesnet.results import cumulative_profile, extract_solution
from bridgesnet.scenarios import manuscript_scenarios
from bridgesnet.solver import SolverConfig, solve_maximum_functionality


def one_bridge_graph() -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_node("C1", Depot=1)
    graph.add_node(
        "B1",
        Start=1,
        Due=3,
        BFI=0.2,
        cost={"RRU": 1.4},
        NewBFI={"RRU": 0.8},
    )
    graph.add_edge("C1", "B1", Time=0.1)
    graph.add_edge("B1", "C1", Time=0.1)
    return graph


def test_primary_solve_is_maximization_and_enforces_earliest_start() -> None:
    graph = one_bridge_graph()
    team = TeamConfig(
        teams=["RRU"],
        base_cost={"RRU": 1.0},
        delta_functionality={"RRU": 0.6},
        service_time={"RRU": 1.0},
        alpha=0.5,
    )
    artifacts, objectives = build_model(
        graph, compute_shortest_paths(graph), team, planning_horizon=4
    )
    record = solve_maximum_functionality(
        artifacts.model,
        objectives,
        SolverConfig(time_limit=30, threads=1, log_to_console=False),
    )

    assert record.status == "OPTIMAL"
    assert record.objective_sense == "maximize"
    assert artifacts.model.ModelSense == GRB.MAXIMIZE
    solution = extract_solution(graph, artifacts, objectives, team)
    assert solution.final_functionality == pytest.approx(0.8)
    assert solution.schedule[0].start >= 1
    assert solution.schedule[0].completion == pytest.approx(
        solution.schedule[0].start + solution.schedule[0].duration
    )
    profile = cumulative_profile(graph, solution.schedule, planning_horizon=4)
    assert profile[-1].cumulative_functionality == pytest.approx(0.8)
    artifacts.model.dispose()


def test_default_model_count_includes_earliest_start_constraints() -> None:
    team = TeamConfig()
    graph = build_graph(GraphConfig(seed=2), team)
    artifacts, _ = build_model(graph, compute_shortest_paths(graph), team)
    artifacts.model.update()
    assert artifacts.model.NumBinVars == 3240
    assert artifacts.model.NumVars - artifacts.model.NumIntVars == 90
    assert artifacts.model.NumConstrs == 3267
    artifacts.model.dispose()


def test_pareto_records_every_subproblem_and_filters_duplicates(tmp_path) -> None:
    graph = one_bridge_graph()
    team = TeamConfig(
        teams=["RRU"],
        base_cost={"RRU": 1.0},
        delta_functionality={"RRU": 0.6},
        service_time={"RRU": 1.0},
        alpha=0.5,
    )
    artifacts, objectives = build_model(
        graph, compute_shortest_paths(graph), team, planning_horizon=4
    )
    result = pareto_frontier(
        artifacts,
        objectives,
        SolverConfig(time_limit=30, threads=1, log_to_console=False),
        num_epsilons=3,
        log_dir=tmp_path,
    )

    assert result.maximum_functionality_endpoint.status == "OPTIMAL"
    assert result.minimum_cost_endpoint is not None
    assert result.minimum_cost_endpoint.status == "OPTIMAL"
    assert len(result.subproblems) == 3
    assert all(item.status == "OPTIMAL" for item in result.subproblems)
    assert len(result.points) == 1
    assert len(list(tmp_path.glob("*.log"))) == 5
    artifacts.model.dispose()


def test_manuscript_scenarios_change_only_named_parameters() -> None:
    team = TeamConfig()
    graph = build_graph(GraphConfig(seed=2), team)
    original = {
        bridge: dict(graph.nodes[bridge]) for bridge in list_bridges(graph)
    }
    scenarios = {item.name: item for item in manuscript_scenarios(graph, team)}

    assert scenarios["base"].team_config.service_time == team.service_time
    assert scenarios["service_time_1_2_2"].team_config.service_time == {
        "RRU": 1.0,
        "ERT": 2.0,
        "CIRS": 2.0,
    }
    for bridge in list_bridges(graph):
        assert scenarios["due_minus_1"].graph.nodes[bridge]["Due"] == (
            original[bridge]["Due"] - 1
        )
        assert scenarios["initial_bfi_plus_0_10"].graph.nodes[bridge][
            "BFI"
        ] == pytest.approx(min(original[bridge]["BFI"] + 0.10, 1))
        assert graph.nodes[bridge]["BFI"] == original[bridge]["BFI"]
