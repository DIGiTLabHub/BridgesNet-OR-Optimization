"""Solution extraction and cumulative-profile helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Tuple

from .config import TeamConfig
from .graph import list_bridges
from .model import ModelArtifacts, ObjectiveExpressions


@dataclass(frozen=True)
class ScheduleRow:
    bridge: str
    depot: str
    team: str
    route_position: int
    start: float
    completion: float
    duration: float
    initial_bfi: float
    restored_bfi: float
    cost_thousand_usd: float

    def to_dict(self) -> dict[str, str | int | float]:
        return asdict(self)


@dataclass(frozen=True)
class ProfileRow:
    time_days: int
    cumulative_functionality: float
    cumulative_cost_thousand_usd: float
    completed_bridges: int

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


@dataclass
class SolutionSummary:
    objective: float
    cost: float
    final_functionality: float
    visited_bridges: int
    active_edges_by_vehicle: Dict[Tuple[str, str], List[Tuple[str, str]]]
    schedule: List[ScheduleRow]

    @property
    def resilience(self) -> float:
        """Backward-compatible alias for final network functionality."""

        return self.final_functionality

    @property
    def active_edges_by_team(self) -> Dict[str, List[Tuple[str, str]]]:
        combined: Dict[str, List[Tuple[str, str]]] = {}
        for (_, team), edges in self.active_edges_by_vehicle.items():
            combined.setdefault(team, []).extend(edges)
        return combined

    @property
    def schedule_data(self) -> List[Tuple[str, str, str, float, float]]:
        return [
            (row.bridge, row.team, row.depot, row.start, row.duration)
            for row in self.schedule
        ]


def _ordered_route(
    depot: str,
    edges: List[Tuple[str, str]],
) -> List[str]:
    successors = {source: target for source, target in edges}
    route: List[str] = []
    current = depot
    seen = {depot}
    while current in successors:
        current = successors[current]
        if current == depot:
            break
        if current in seen:
            break
        seen.add(current)
        if current.startswith("B"):
            route.append(current)
    return route


def extract_solution(
    G,
    artifacts: ModelArtifacts,
    objectives: ObjectiveExpressions,
    team_config: TeamConfig,
) -> SolutionSummary:
    """Build a canonical summary from an available incumbent solution."""

    model = artifacts.model
    if model.SolCount <= 0:
        raise RuntimeError(
            f"No incumbent solution is available (solver status {model.Status})"
        )

    active_edges: Dict[Tuple[str, str], List[Tuple[str, str]]] = {
        dk: [] for dk in artifacts.pair_dk
    }
    for (source, target, dk), variable in artifacts.x.items():
        if variable.X > 0.5:
            active_edges[dk].append((source, target))

    route_positions: Dict[Tuple[str, Tuple[str, str]], int] = {}
    for dk, edges in active_edges.items():
        for position, bridge in enumerate(_ordered_route(dk[0], edges), start=1):
            route_positions[(bridge, dk)] = position

    schedule: List[ScheduleRow] = []
    selected_bridges: set[str] = set()
    for (bridge, dk, completion_period), variable in artifacts.y.items():
        if variable.X <= 0.5:
            continue
        selected_bridges.add(bridge)
        depot, team = dk
        duration = float(team_config.service_time[team])
        schedule.append(
            ScheduleRow(
                bridge=bridge,
                depot=depot,
                team=team,
                route_position=route_positions.get((bridge, dk), 0),
                start=float(artifacts.s[bridge, dk].X),
                completion=float(completion_period),
                duration=duration,
                initial_bfi=float(G.nodes[bridge]["BFI"]),
                restored_bfi=float(G.nodes[bridge]["NewBFI"][team]),
                cost_thousand_usd=float(G.nodes[bridge]["cost"][team]),
            )
        )

    schedule.sort(key=lambda row: (row.depot, row.team, row.route_position, row.bridge))
    final_functionality = float(objectives.final_functionality.getValue())
    return SolutionSummary(
        objective=float(model.ObjVal),
        cost=float(objectives.cost.getValue()),
        final_functionality=final_functionality,
        visited_bridges=len(selected_bridges),
        active_edges_by_vehicle=active_edges,
        schedule=schedule,
    )


def cumulative_profile(
    G,
    schedule: List[ScheduleRow],
    planning_horizon: int,
) -> List[ProfileRow]:
    """Compute end-of-period functionality and restoration expenditure."""

    if planning_horizon <= 0:
        raise ValueError("planning_horizon must be positive")
    bridges = list_bridges(G)
    baseline_total = sum(float(G.nodes[bridge]["BFI"]) for bridge in bridges)
    bridge_count = len(bridges)
    rows: List[ProfileRow] = []
    for period in range(planning_horizon):
        completed = [row for row in schedule if row.completion <= period + 1e-8]
        functionality = (
            baseline_total
            + sum(row.restored_bfi - row.initial_bfi for row in completed)
        ) / bridge_count
        rows.append(
            ProfileRow(
                time_days=period,
                cumulative_functionality=float(functionality),
                cumulative_cost_thousand_usd=float(
                    sum(row.cost_thousand_usd for row in completed)
                ),
                completed_bridges=len(completed),
            )
        )
    return rows
