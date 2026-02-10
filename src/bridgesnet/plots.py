"""Plotting utilities for networks, routes, Gantt charts, and Pareto frontiers."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.patches import Patch


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

    for team, edges in edge_list_by_team.items():
        if edges:
            nx.draw_networkx_edges(
                G, pos, edgelist=edges, width=2, edge_color=team_colors[team], ax=ax
            )

    legend_elements = [
        Patch(facecolor=color, edgecolor="black", label=team)
        for team, color in team_colors.items()
    ]
    ax.legend(handles=legend_elements, title="Teams", loc="lower right")
    ax.set_title("Emergency Routing Paths by Team", fontsize=14)
    ax.axis("off")
    return fig


def plot_gantt(
    schedule_data: Iterable[Tuple[str, str, str, float]],
    team_colors: Dict[str, str],
) -> plt.Figure:
    grouped_schedule = defaultdict(list)
    for bridge, team, depot, start in schedule_data:
        grouped_schedule[depot].append((bridge, team, start))

    if not grouped_schedule:
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.text(0.5, 0.5, "No scheduled tasks", ha="center", va="center")
        ax.axis("off")
        return fig

    fig, axes = plt.subplots(
        nrows=len(grouped_schedule),
        figsize=(10, 3 * len(grouped_schedule)),
        sharex=True,
    )

    if len(grouped_schedule) == 1:
        axes = [axes]

    for ax, (depot, tasks) in zip(axes, grouped_schedule.items()):
        yticks = []
        yticklabels = []
        for i, (bridge, team, start) in enumerate(tasks):
            ax.barh(
                i,
                1,
                left=start,
                height=0.6,
                color=team_colors.get(team, "gray"),
            )
            ax.text(
                start + 0.05,
                i,
                f"{bridge} ({team})",
                va="center",
                ha="left",
                fontsize=8,
            )
            yticks.append(i)
            yticklabels.append(bridge)

        ax.set_yticks(yticks)
        ax.set_yticklabels(yticklabels)
        ax.set_title(f"Gantt Chart - Depot {depot}")
        ax.invert_yaxis()
        ax.grid(axis="x", linestyle="--", alpha=0.5)

    axes[-1].set_xlabel("Time")
    fig.tight_layout()
    return fig


def plot_pareto(
    resilience_array: List[float],
    cost_array: List[float],
) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(
        resilience_array,
        cost_array,
        c="blue",
        edgecolors="black",
        s=70,
        marker="o",
        alpha=0.8,
    )
    ax.set_title("Pareto Frontier: Cost vs. Resilience", fontsize=14, fontweight="bold")
    ax.set_xlabel("Resilience", fontsize=12, color="blue")
    ax.set_ylabel("Cost ($1000)", fontsize=12, color="red")
    ax.tick_params(axis="y", colors="red")
    ax.tick_params(axis="x", colors="blue")

    for x, y in zip(resilience_array, cost_array):
        ax.text(x, y + 0.5, f"{y:.0f}", fontsize=9, color="red", ha="center")
        ax.text(x, y - 1.5, f"{x:.2f}", fontsize=9, color="blue", ha="center")

    ax.grid(True, linestyle="--", alpha=0.5)
    fig.tight_layout()
    return fig
