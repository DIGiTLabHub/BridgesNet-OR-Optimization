"""Shared, evidence-preserving Gurobi solve helpers."""

from __future__ import annotations

import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB

from .model import ObjectiveExpressions


@dataclass(frozen=True)
class SolverConfig:
    """Parameters applied consistently by every optimization entry point."""

    time_limit: float = 3600.0
    mip_gap: float = 1e-4
    threads: int = 0
    seed: int = 0
    log_to_console: bool = True

    def validate(self) -> None:
        if self.time_limit <= 0:
            raise ValueError("time_limit must be positive")
        if not 0 <= self.mip_gap < 1:
            raise ValueError("mip_gap must be in [0, 1)")
        if self.threads < 0:
            raise ValueError("threads cannot be negative")
        if not 0 <= self.seed <= 2_000_000_000:
            raise ValueError("seed must be in [0, 2000000000]")


@dataclass
class SolveRecord:
    objective_name: str
    objective_sense: str
    status_code: int | None
    status: str
    runtime_seconds: float | None
    solution_count: int
    incumbent_objective: float | None
    best_bound: float | None
    gap_percent: float | None
    error: str | None = None

    @property
    def has_incumbent(self) -> bool:
        return self.solution_count > 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def status_name(status_code: int) -> str:
    statuses = {
        GRB.LOADED: "LOADED",
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.CUTOFF: "CUTOFF",
        GRB.ITERATION_LIMIT: "ITERATION_LIMIT",
        GRB.NODE_LIMIT: "NODE_LIMIT",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SOLUTION_LIMIT: "SOLUTION_LIMIT",
        GRB.INTERRUPTED: "INTERRUPTED",
        GRB.NUMERIC: "NUMERIC",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.INPROGRESS: "INPROGRESS",
        GRB.USER_OBJ_LIMIT: "USER_OBJ_LIMIT",
    }
    for attribute in ("WORK_LIMIT", "MEM_LIMIT"):
        code = getattr(GRB, attribute, None)
        if code is not None:
            statuses[code] = attribute
    return statuses.get(status_code, f"STATUS_{status_code}")


def configure_solver(
    model: gp.Model,
    config: SolverConfig,
    log_path: Path | None = None,
) -> None:
    config.validate()
    model.Params.TimeLimit = config.time_limit
    model.Params.MIPGap = config.mip_gap
    model.Params.Threads = config.threads
    model.Params.Seed = config.seed
    model.Params.LogToConsole = int(config.log_to_console)
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        model.Params.LogFile = str(log_path.resolve())


def solve_model(
    model: gp.Model,
    objective: gp.LinExpr | gp.QuadExpr | gp.Var,
    sense: int,
    config: SolverConfig,
    *,
    objective_name: str,
    log_path: Path | None = None,
) -> SolveRecord:
    """Configure and solve one model, returning status even when no incumbent exists."""

    if sense not in (GRB.MAXIMIZE, GRB.MINIMIZE):
        raise ValueError("sense must be GRB.MAXIMIZE or GRB.MINIMIZE")
    configure_solver(model, config, log_path)
    model.setObjective(objective, sense)
    try:
        model.optimize()
    except gp.GurobiError as exc:
        return SolveRecord(
            objective_name=objective_name,
            objective_sense="maximize" if sense == GRB.MAXIMIZE else "minimize",
            status_code=None,
            status="GUROBI_ERROR",
            runtime_seconds=None,
            solution_count=0,
            incumbent_objective=None,
            best_bound=None,
            gap_percent=None,
            error=f"{exc.errno}: {exc}",
        )

    status_code = int(model.Status)
    solution_count = int(model.SolCount)
    incumbent = float(model.ObjVal) if solution_count else None
    bound: float | None = None
    gap: float | None = None
    try:
        bound = float(model.ObjBound)
    except gp.GurobiError:
        pass
    if solution_count:
        try:
            gap = float(model.MIPGap) * 100
        except gp.GurobiError:
            pass
    return SolveRecord(
        objective_name=objective_name,
        objective_sense="maximize" if sense == GRB.MAXIMIZE else "minimize",
        status_code=status_code,
        status=status_name(status_code),
        runtime_seconds=float(model.Runtime),
        solution_count=solution_count,
        incumbent_objective=incumbent,
        best_bound=bound,
        gap_percent=gap,
    )


def solve_maximum_functionality(
    model: gp.Model,
    objectives: ObjectiveExpressions,
    config: SolverConfig,
    log_path: Path | None = None,
) -> SolveRecord:
    """Solve the repository's primary objective with an explicit maximize sense."""

    return solve_model(
        model,
        objectives.final_functionality,
        GRB.MAXIMIZE,
        config,
        objective_name="final_network_functionality",
        log_path=log_path,
    )


def runtime_metadata(project_root: Path) -> dict[str, Any]:
    """Collect lightweight runtime and repository provenance for result folders."""

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "git_commit": commit.stdout.strip() if commit.returncode == 0 else "unavailable",
        "git_worktree_dirty": bool(dirty.stdout.strip()) if dirty.returncode == 0 else None,
        "python": sys.version,
        "gurobi": gp.gurobi.version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
    }
