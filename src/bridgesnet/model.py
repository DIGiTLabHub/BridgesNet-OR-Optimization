"""Gurobi model construction for bridge intervention planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import gurobipy as gp
from gurobipy import GRB, quicksum

from .config import TeamConfig
from .graph import list_bridges


@dataclass
class ModelArtifacts:
    model: gp.Model
    x: Dict[Tuple[str, str, Tuple[str, str]], gp.Var]
    y: Dict[Tuple[str, Tuple[str, str], int], gp.Var]
    s: Dict[Tuple[str, Tuple[str, str]], gp.Var]
    depots: List[str]
    pair_dk: List[Tuple[str, str]]
    planning_horizon: int


@dataclass
class ObjectiveExpressions:
    resilience_raw: gp.LinExpr
    resilience: gp.LinExpr
    cost: gp.LinExpr
    bridges_count: int

    @property
    def final_functionality(self) -> gp.LinExpr:
        """Average bridge functionality at the end of the planning horizon."""

        return (self.resilience + self.resilience_raw) / self.bridges_count


def _validate_paths(shortest_paths: Dict[Tuple[str, str], Tuple[list | None, float]]) -> None:
    for (i, j), (_, travel_time) in shortest_paths.items():
        if travel_time == float("inf"):
            raise ValueError(f"No path between {i} and {j}; cannot build model")


def build_model(
    G,
    shortest_paths: Dict[Tuple[str, str], Tuple[list | None, float]],
    team_config: TeamConfig,
    planning_horizon: int = 8,
    big_m: float = 1000.0,
) -> Tuple[ModelArtifacts, ObjectiveExpressions]:
    """Create the optimization model and key expressions."""

    if planning_horizon <= 0:
        raise ValueError("planning_horizon must be positive")
    if big_m <= 0:
        raise ValueError("big_m must be positive")
    if not team_config.teams:
        raise ValueError("At least one team type is required")
    for mapping_name, mapping in (
        ("base_cost", team_config.base_cost),
        ("delta_functionality", team_config.delta_functionality),
        ("service_time", team_config.service_time),
    ):
        missing = set(team_config.teams) - set(mapping)
        if missing:
            raise ValueError(f"{mapping_name} is missing teams: {sorted(missing)}")
    if any(team_config.service_time[team] < 0 for team in team_config.teams):
        raise ValueError("service times must be nonnegative")

    _validate_paths(shortest_paths)
    bridges = list_bridges(G)
    if not bridges:
        raise ValueError("Graph has no bridge nodes to service")

    depots = [d for d in G.nodes() if G.nodes[d].get("Depot") == 1]
    if not depots:
        raise ValueError("Graph has no depot nodes; cannot route teams")

    pair_dk = [(d, k) for d in depots for k in team_config.teams]
    if not pair_dk:
        raise ValueError("No depot-team pairs generated")

    for bridge in bridges:
        attributes = G.nodes[bridge]
        missing = {"Start", "Due", "BFI", "cost", "NewBFI"} - set(attributes)
        if missing:
            raise ValueError(f"Bridge {bridge} is missing attributes: {sorted(missing)}")
        if attributes["Start"] > attributes["Due"]:
            raise ValueError(f"Bridge {bridge} has Start greater than Due")
        if not 0 <= attributes["BFI"] <= 1:
            raise ValueError(f"Bridge {bridge} has BFI outside [0, 1]")
        for team in team_config.teams:
            if team not in attributes["cost"] or team not in attributes["NewBFI"]:
                raise ValueError(f"Bridge {bridge} lacks cost/NewBFI for team {team}")
            if attributes["cost"][team] < 0:
                raise ValueError(f"Bridge {bridge} has negative cost for team {team}")
            if not 0 <= attributes["NewBFI"][team] <= 1:
                raise ValueError(
                    f"Bridge {bridge} has NewBFI outside [0, 1] for team {team}"
                )

    m = gp.Model("BIM")

    x = {
        (i, j, dk): m.addVar(vtype=GRB.BINARY, name=f"x_{i}_{j}_{dk[0]}_{dk[1]}")
        for i in G.nodes()
        for j in G.nodes()
        if i != j
        for dk in pair_dk
    }

    y = {
        (i, dk, t): m.addVar(vtype=GRB.BINARY, name=f"y_{i}_{dk[0]}_{dk[1]}_{t}")
        for i in bridges
        for dk in pair_dk
        for t in range(planning_horizon)
    }

    s = {
        (i, dk): m.addVar(vtype=GRB.CONTINUOUS, lb=0, name=f"s_{i}_{dk[0]}_{dk[1]}")
        for i in bridges
        for dk in pair_dk
    }

    # Each bridge is serviced at most once.
    m.addConstrs(
        (
            quicksum(y[i, dk, t] for dk in pair_dk for t in range(planning_horizon))
            <= 1
            for i in bridges
        ),
        name="Served_ONCE",
    )

    # Link routing decisions to service decisions.
    m.addConstrs(
        (
            quicksum(
                x[i, j, dk]
                for i in G.nodes()
                if i != j and (str(i).startswith("B") or i == dk[0])
            )
            == quicksum(y[j, dk, t] for t in range(planning_horizon))
            for dk in pair_dk
            for j in bridges
        ),
        name="Linki",
    )

    m.addConstrs(
        (
            quicksum(
                x[i, j, dk]
                for j in G.nodes()
                if j != i and (str(j).startswith("B") or j == dk[0])
            )
            == quicksum(y[i, dk, t] for t in range(planning_horizon))
            for dk in pair_dk
            for i in bridges
        ),
        name="Linkj",
    )

    # Depot departure and return for each depot-team pair.
    m.addConstrs(
        (
            quicksum(x[dk[0], j, dk] for j in bridges) == 1
            for dk in pair_dk
        ),
        name="Depot_dk",
    )

    m.addConstrs(
        (
            quicksum(x[i, dk[0], dk] for i in bridges) == 1
            for dk in pair_dk
        ),
        name="Return_dk",
    )

    # Time window linking between service start and discrete time slots.
    m.addConstrs(
        (
            s[i, dk] + team_config.service_time[dk[1]] - t
            <= big_m * (1 - y[i, dk, t])
            for i in bridges
            for dk in pair_dk
            for t in range(planning_horizon)
        ),
        name="y_s_U",
    )

    m.addConstrs(
        (
            s[i, dk] + team_config.service_time[dk[1]] - t
            >= -big_m * (1 - y[i, dk, t])
            for i in bridges
            for dk in pair_dk
            for t in range(planning_horizon)
        ),
        name="y_s_L",
    )

    # Enforce the bridge availability date (manuscript Eq. 13).
    m.addConstrs(
        (
            s[i, dk] >= G.nodes[i]["Start"]
            for i in bridges
            for dk in pair_dk
        ),
        name="Earliest_Start",
    )

    # Propagate start times along chosen arcs using shortest travel times.  A
    # depot has no intervention duration; bridge predecessors do.
    m.addConstrs(
        (
            s[j, dk]
            >= (s[i, dk] if str(i).startswith("B") else 0)
            + (team_config.service_time[dk[1]] if str(i).startswith("B") else 0)
            + shortest_paths[(i, j)][1] / 24
            - big_m * (1 - x[i, j, dk])
            for i in G.nodes()
            for j in bridges
            if i != j and (str(i).startswith("B") or G.nodes[i].get("Depot"))
            for dk in pair_dk
        ),
        name="s_Start",
    )

    # Respect bridge due dates.
    m.addConstrs(
        (
            s[i, dk] + team_config.service_time[dk[1]] <= G.nodes[i]["Due"]
            for i in bridges
            for dk in pair_dk
        ),
        name="Due",
    )

    bridges_count = len(bridges)

    resilience_raw = quicksum(
        G.nodes[i]["BFI"]
        * (
            1
            - quicksum(y[i, dk, t] for dk in pair_dk for t in range(planning_horizon))
        )
        for i in bridges
    )

    resilience = quicksum(
        G.nodes[i]["NewBFI"][dk[1]] * quicksum(y[i, dk, t] for t in range(planning_horizon))
        for i in bridges
        for dk in pair_dk
    )

    cost = quicksum(
        G.nodes[i]["cost"][dk[1]] * quicksum(y[i, dk, t] for t in range(planning_horizon))
        for i in bridges
        for dk in pair_dk
    )

    artifacts = ModelArtifacts(
        model=m,
        x=x,
        y=y,
        s=s,
        depots=depots,
        pair_dk=pair_dk,
        planning_horizon=planning_horizon,
    )
    objectives = ObjectiveExpressions(
        resilience_raw=resilience_raw,
        resilience=resilience,
        cost=cost,
        bridges_count=bridges_count,
    )
    return artifacts, objectives
