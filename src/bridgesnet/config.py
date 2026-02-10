"""Configuration objects for graph generation and optimization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple


@dataclass(frozen=True)
class TeamConfig:
    """Team-level parameters used in cost and service calculations."""

    teams: List[str] = field(default_factory=lambda: ["RRU", "ERT", "CIRS"])
    base_cost: Dict[str, float] = field(
        default_factory=lambda: {"RRU": 1.0, "ERT": 2.0, "CIRS": 5.0}
    )
    delta_functionality: Dict[str, float] = field(
        default_factory=lambda: {"RRU": 0.3, "ERT": 0.55, "CIRS": 0.75}
    )
    service_time: Dict[str, float] = field(
        default_factory=lambda: {"RRU": 1.0, "ERT": 1.0, "CIRS": 1.0}
    )
    alpha: float = 0.5


@dataclass(frozen=True)
class GraphConfig:
    """Settings for synthetic bridge network generation."""

    n_cities: int = 6
    seed: int = 2
    depot_bias: float = 0.90
    bridge_count_range: Tuple[int, int] = (1, 1)
    bridge_bfi_range: Tuple[float, float] = (0.2, 0.4)
    bridge_start_range: Tuple[int, int] = (0, 2)
    bridge_due_offset_range: Tuple[int, int] = (2, 5)
    speed_choices: Sequence[int] = (60, 80, 120)
    capacity_choices: Sequence[int] = (500, 700, 800)
    length_range: Tuple[int, int] = (1, 6)
    final_length_range: Tuple[int, int] = (2, 6)
    layout_seed: int = 39
