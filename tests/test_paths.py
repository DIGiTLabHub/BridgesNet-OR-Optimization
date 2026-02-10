"""Unit tests for shortest-path logic."""

from bridgesnet.config import GraphConfig, TeamConfig
from bridgesnet.graph import build_graph
from bridgesnet.paths import compute_shortest_paths


def test_shortest_paths_compute_times() -> None:
    team_config = TeamConfig()
    graph_config = GraphConfig(n_cities=4, seed=2)
    G = build_graph(graph_config, team_config)
    shortest_paths = compute_shortest_paths(G)

    for (source, target), (_, time) in shortest_paths.items():
        assert source != target
        assert time >= 0
