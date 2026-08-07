"""Plotting utilities for networks, routes, schedules, and optimization results."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Sequence, Tuple

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.patches import Patch

from .results import ProfileRow, ScheduleRow


def plot_network(
    G: nx.DiGraph,
    pos: Dict[str, Tuple[float, float]],
    node_colors: List[str],
    labels: Dict[str, str],
) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(12, 7))
    nx.draw(G, pos, with_labels=True, node_color=node_colors, node_size=700, ax=ax)
    nx.draw_networkx_labels(G, pos, labels, font_size=12, font_color="white", ax=ax)
    ax.axis("off")
    return fig


def plot_routes_by_team(
    G: nx.DiGraph,
    pos: Dict[str, Tuple[float, float]],
    node_colors: List[str],
    edge_list_by_team: Dict[str, List[Tuple[str, str]]],
    team_colors: Dict[str, str],
) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(12, 7))
    nx.draw(
        G,
        pos,
        with_labels=True,
        node_color=node_colors,
        node_size=700,
        font_size=10,
        edge_color="lightgray",
        ax=ax,
    )
    line_styles = ["solid", "dashed", "dotted", "dashdot"]
    for index, (team, edges) in enumerate(edge_list_by_team.items()):
        if edges:
            nx.draw_networkx_edges(
                G,
                pos,
                edgelist=edges,
                width=2,
                style=line_styles[index % len(line_styles)],
                edge_color=team_colors.get(team, "black"),
                ax=ax,
            )
    legend_elements = [
        Patch(facecolor=color, edgecolor="black", label=team)
        for team, color in team_colors.items()
    ]
    ax.legend(handles=legend_elements, title="Team type", loc="lower right")
    ax.set_title("Optimized intervention routes")
    ax.axis("off")
    return fig


def plot_gantt(
    schedule_data: Iterable[ScheduleRow | Tuple[str, str, str, float, float]],
    team_colors: Dict[str, str],
) -> plt.Figure:
    grouped_schedule: dict[str, list[tuple[str, str, float, float]]] = defaultdict(list)
    for item in schedule_data:
        if isinstance(item, ScheduleRow):
            grouped_schedule[item.depot].append(
                (item.bridge, item.team, item.start, item.duration)
            )
        else:
            bridge, team, depot, start, duration = item
            grouped_schedule[depot].append((bridge, team, start, duration))

    if not grouped_schedule:
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.text(0.5, 0.5, "No scheduled interventions", ha="center", va="center")
        ax.axis("off")
        return fig

    fig, axes = plt.subplots(
        nrows=len(grouped_schedule),
        figsize=(10, 3 * len(grouped_schedule)),
        sharex=True,
        squeeze=False,
    )
    hatches = {team: hatch for team, hatch in zip(team_colors, ("", "//", "xx", ".."))}
    for ax, (depot, tasks) in zip(axes[:, 0], sorted(grouped_schedule.items())):
        tasks.sort(key=lambda task: (task[2], task[0]))
        for index, (bridge, team, start, duration) in enumerate(tasks):
            ax.barh(
                index,
                duration,
                left=start,
                height=0.6,
                color=team_colors.get(team, "gray"),
                edgecolor="black",
                hatch=hatches.get(team, ""),
            )
            ax.text(start + 0.04, index, f"{bridge} ({team})", va="center", fontsize=8)
        ax.set_yticks(range(len(tasks)))
        ax.set_yticklabels([task[0] for task in tasks])
        ax.set_title(f"Depot {depot}")
        ax.invert_yaxis()
        ax.grid(axis="x", linestyle="--", alpha=0.5)
    axes[-1, 0].set_xlabel("Time (days)")
    fig.tight_layout()
    return fig


def plot_pareto(
    functionality: Sequence[float],
    cost: Sequence[float],
) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(functionality, cost, color="black", marker="o", linestyle="-")
    ax.set_title("Cost-functionality Pareto frontier")
    ax.set_xlabel("Final network functionality")
    ax.set_ylabel("Restoration cost (thousand USD)")
    ax.grid(True, linestyle="--", alpha=0.5)
    fig.tight_layout()
    return fig


def plot_cumulative_profile(profile: Sequence[ProfileRow]) -> plt.Figure:
    fig, functionality_axis = plt.subplots(figsize=(8, 5))
    cost_axis = functionality_axis.twinx()
    times = [row.time_days for row in profile]
    functionality_axis.step(
        times,
        [row.cumulative_functionality for row in profile],
        where="post",
        color="black",
        marker="o",
        label="Functionality",
    )
    cost_axis.step(
        times,
        [row.cumulative_cost_thousand_usd for row in profile],
        where="post",
        color="0.45",
        linestyle="--",
        marker="s",
        label="Cost",
    )
    functionality_axis.set_xlabel("Time (days)")
    functionality_axis.set_ylabel("Cumulative network functionality")
    cost_axis.set_ylabel("Cumulative cost (thousand USD)")
    functionality_axis.grid(True, linestyle=":", alpha=0.5)
    handles1, labels1 = functionality_axis.get_legend_handles_labels()
    handles2, labels2 = cost_axis.get_legend_handles_labels()
    functionality_axis.legend(handles1 + handles2, labels1 + labels2, loc="best")
    fig.tight_layout()
    return fig
