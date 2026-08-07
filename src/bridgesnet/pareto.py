"""Evidence-preserving epsilon-constraint Pareto frontier generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from gurobipy import GRB

from .model import ObjectiveExpressions, ModelArtifacts
from .solver import SolveRecord, SolverConfig, solve_model


@dataclass(frozen=True)
class ParetoPoint:
    epsilon_cost: float
    final_functionality: float
    cost_thousand_usd: float
    status: str
    runtime_seconds: float | None
    best_bound: float | None
    gap_percent: float | None

    def to_dict(self) -> dict[str, str | float | None]:
        return asdict(self)


@dataclass(frozen=True)
class ParetoSubproblem:
    index: int
    epsilon_cost: float
    status: str
    solution_count: int
    runtime_seconds: float | None
    incumbent_objective: float | None
    best_bound: float | None
    gap_percent: float | None
    final_functionality: float | None
    cost_thousand_usd: float | None
    error: str | None

    def to_dict(self) -> dict[str, str | int | float | None]:
        return asdict(self)


@dataclass
class ParetoResult:
    maximum_functionality_endpoint: SolveRecord
    minimum_cost_endpoint: SolveRecord | None
    subproblems: list[ParetoSubproblem]
    points: list[ParetoPoint]


def _log_path(log_dir: Path | None, name: str) -> Path | None:
    return None if log_dir is None else log_dir / f"{name}.log"


def _non_dominated(points: list[ParetoPoint], tolerance: float = 1e-8) -> list[ParetoPoint]:
    unique: list[ParetoPoint] = []
    for point in sorted(points, key=lambda item: (item.cost_thousand_usd, -item.final_functionality)):
        if any(
            abs(point.cost_thousand_usd - other.cost_thousand_usd) <= tolerance
            and abs(point.final_functionality - other.final_functionality) <= tolerance
            for other in unique
        ):
            continue
        unique.append(point)

    frontier: list[ParetoPoint] = []
    for point in unique:
        dominated = any(
            other.cost_thousand_usd <= point.cost_thousand_usd + tolerance
            and other.final_functionality >= point.final_functionality - tolerance
            and (
                other.cost_thousand_usd < point.cost_thousand_usd - tolerance
                or other.final_functionality > point.final_functionality + tolerance
            )
            for other in unique
        )
        if not dominated:
            frontier.append(point)
    return sorted(frontier, key=lambda item: item.cost_thousand_usd)


def pareto_frontier(
    artifacts: ModelArtifacts,
    objectives: ObjectiveExpressions,
    solver_config: SolverConfig,
    num_epsilons: int = 10,
    log_dir: Path | None = None,
) -> ParetoResult:
    """Compute a filtered cost/functionality frontier with per-solve evidence."""

    if num_epsilons < 2:
        raise ValueError("num_epsilons must be at least 2")
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
    model = artifacts.model

    maximum = solve_model(
        model,
        objectives.final_functionality,
        GRB.MAXIMIZE,
        solver_config,
        objective_name="maximum_final_network_functionality",
        log_path=_log_path(log_dir, "endpoint_max_functionality"),
    )
    if not maximum.has_incumbent:
        return ParetoResult(maximum, None, [], [])
    maximum_cost = float(objectives.cost.getValue())

    minimum = solve_model(
        model,
        objectives.cost,
        GRB.MINIMIZE,
        solver_config,
        objective_name="minimum_restoration_cost",
        log_path=_log_path(log_dir, "endpoint_min_cost"),
    )
    if not minimum.has_incumbent:
        return ParetoResult(maximum, minimum, [], [])
    minimum_cost = float(objectives.cost.getValue())

    step = (maximum_cost - minimum_cost) / (num_epsilons - 1)
    candidates: list[ParetoPoint] = []
    subproblems: list[ParetoSubproblem] = []
    for index in range(num_epsilons):
        epsilon = minimum_cost + index * step
        constraint = model.addConstr(
            objectives.cost <= epsilon,
            name=f"epsilon_cost_{index:03d}",
        )
        record = solve_model(
            model,
            objectives.final_functionality,
            GRB.MAXIMIZE,
            solver_config,
            objective_name="epsilon_maximum_final_network_functionality",
            log_path=_log_path(log_dir, f"epsilon_{index:03d}"),
        )
        functionality = float(model.ObjVal) if record.has_incumbent else None
        realized_cost = float(objectives.cost.getValue()) if record.has_incumbent else None
        subproblems.append(
            ParetoSubproblem(
                index=index,
                epsilon_cost=float(epsilon),
                status=record.status,
                solution_count=record.solution_count,
                runtime_seconds=record.runtime_seconds,
                incumbent_objective=record.incumbent_objective,
                best_bound=record.best_bound,
                gap_percent=record.gap_percent,
                final_functionality=functionality,
                cost_thousand_usd=realized_cost,
                error=record.error,
            )
        )
        if record.has_incumbent:
            candidates.append(
                ParetoPoint(
                    epsilon_cost=float(epsilon),
                    final_functionality=functionality,
                    cost_thousand_usd=realized_cost,
                    status=record.status,
                    runtime_seconds=record.runtime_seconds,
                    best_bound=record.best_bound,
                    gap_percent=record.gap_percent,
                )
            )
        model.remove(constraint)
        model.update()

    return ParetoResult(maximum, minimum, subproblems, _non_dominated(candidates))
