"""Solution extraction helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .config import TeamConfig
from .model import ModelArtifacts, ObjectiveExpressions


@dataclass
class SolutionSummary:
    objective: float
    cost: float
    resilience: float
    visited_bridges: int
    active_edges_by_team: Dict[str, List[Tuple[str, str]]]
    schedule_data: List[Tuple[str, str, str, float]]


def extract_solution(
    G,
    artifacts: ModelArtifacts,
    objectives: ObjectiveExpressions,
    team_config: TeamConfig,
) -> SolutionSummary:
    """Build a summary of the optimized solution."""

    m = artifacts.model
    if m.Status <= 0:
        raise RuntimeError("Model has not been optimized")

    visited_bridges = 0
    for (bridge, dk, t), var in artifacts.y.items():
        if var.X > 0.5:
            visited_bridges += 1

    active_edges_by_team = {team: [] for team in team_config.teams}
    for (i, j, dk), var in artifacts.x.items():
        if var.X > 0.5:
            _, team = dk
            active_edges_by_team[team].append((i, j))

    schedule_data: List[Tuple[str, str, str, float]] = []
    for (bridge, dk), var in artifacts.s.items():
        assigned = any(
            artifacts.y[bridge, dk, t].X > 0.5 for t in range(artifacts.planning_horizon)
        )
        if assigned:
            depot, team = dk
            schedule_data.append((bridge, team, depot, var.X))

    cost_value = objectives.cost.getValue()
    resilience_value = (
        objectives.resilience.getValue() + objectives.resilience_raw.getValue()
    ) / objectives.bridges_count

    return SolutionSummary(
        objective=m.ObjVal,
        cost=cost_value,
        resilience=resilience_value,
        visited_bridges=visited_bridges,
        active_edges_by_team=active_edges_by_team,
        schedule_data=schedule_data,
    )
