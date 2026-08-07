"""Named manuscript cases built on one parameterized network realization."""

from __future__ import annotations

import copy
from dataclasses import dataclass

import networkx as nx

from .config import TeamConfig
from .graph import list_bridges


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    graph: nx.DiGraph
    team_config: TeamConfig


def _recompute_bridge_outcomes(graph: nx.DiGraph, team_config: TeamConfig) -> None:
    for bridge in list_bridges(graph):
        bfi = graph.nodes[bridge]["BFI"]
        graph.nodes[bridge]["cost"] = {
            team: round(
                team_config.base_cost[team]
                * (1 + team_config.alpha * (1 - bfi)),
                2,
            )
            for team in team_config.teams
        }
        graph.nodes[bridge]["NewBFI"] = {
            team: min(round(bfi + team_config.delta_functionality[team], 2), 1)
            for team in team_config.teams
        }


def manuscript_scenarios(
    base_graph: nx.DiGraph,
    base_team_config: TeamConfig,
) -> list[Scenario]:
    """Return base and manuscript sensitivity cases from the same network.

    Only the parameter named by each case changes.  This isolates scenario
    effects from random graph regeneration.
    """

    base = copy.deepcopy(base_graph)

    service_graph = copy.deepcopy(base_graph)
    service_config = TeamConfig(
        teams=list(base_team_config.teams),
        base_cost=dict(base_team_config.base_cost),
        delta_functionality=dict(base_team_config.delta_functionality),
        service_time={"RRU": 1.0, "ERT": 2.0, "CIRS": 2.0},
        alpha=base_team_config.alpha,
    )

    due_graph = copy.deepcopy(base_graph)
    for bridge in list_bridges(due_graph):
        due_graph.nodes[bridge]["Due"] -= 1
        if due_graph.nodes[bridge]["Due"] < due_graph.nodes[bridge]["Start"]:
            raise ValueError(
                f"Due-minus-one creates an invalid window for bridge {bridge}"
            )

    bfi_graph = copy.deepcopy(base_graph)
    for bridge in list_bridges(bfi_graph):
        bfi_graph.nodes[bridge]["BFI"] = min(
            round(bfi_graph.nodes[bridge]["BFI"] + 0.10, 2), 1
        )
    _recompute_bridge_outcomes(bfi_graph, base_team_config)

    return [
        Scenario(
            "base",
            "Parameterized network at the selected configuration; manuscript case at defaults.",
            base,
            base_team_config,
        ),
        Scenario(
            "service_time_1_2_2",
            "Service durations RRU=1, ERT=2, CIRS=2 days.",
            service_graph,
            service_config,
        ),
        Scenario(
            "due_minus_1",
            "Every bridge due date is one day earlier.",
            due_graph,
            base_team_config,
        ),
        Scenario(
            "initial_bfi_plus_0_10",
            "Every initial BFI is increased by 0.10 and derived cost/NewBFI are recomputed.",
            bfi_graph,
            base_team_config,
        ),
    ]
