"""Epsilon-constraint Pareto frontier generation."""

from __future__ import annotations

from typing import List, Tuple

import numpy as np
from gurobipy import GRB

from .model import ObjectiveExpressions, ModelArtifacts


def pareto_frontier(
    artifacts: ModelArtifacts,
    objectives: ObjectiveExpressions,
    num_epsilons: int = 10,
) -> Tuple[List[float], List[float]]:
    """Compute Pareto points by bounding cost and maximizing resilience."""

    m = artifacts.model

    # Maximize resilience to get upper bound on cost.
    m.setObjective(
        (objectives.resilience + objectives.resilience_raw) / objectives.bridges_count,
        GRB.MAXIMIZE,
    )
    m.optimize()
    max_resilience = m.ObjVal
    max_cost = objectives.cost.getValue()

    # Minimize cost to get lower bound on cost.
    m.setObjective(objectives.cost, GRB.MINIMIZE)
    m.optimize()
    min_cost = m.ObjVal
    min_resilience = (
        objectives.resilience.getValue() + objectives.resilience_raw.getValue()
    ) / objectives.bridges_count

    epsilons = np.linspace(min_cost, max_cost, num_epsilons)
    resilience_array: List[float] = []
    cost_array: List[float] = []

    for eps in epsilons:
        constraint = m.addConstr(objectives.cost <= eps, name="epsilon_constraint")
        m.setObjective(
            (objectives.resilience + objectives.resilience_raw) / objectives.bridges_count,
            GRB.MAXIMIZE,
        )
        m.optimize()
        resilience_array.append(m.ObjVal)
        cost_array.append(objectives.cost.getValue())
        m.remove(constraint)
        m.update()

    return resilience_array, cost_array
