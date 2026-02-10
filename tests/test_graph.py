"""Unit tests for graph construction."""

from bridgesnet.config import GraphConfig, TeamConfig
from bridgesnet.graph import build_graph, list_bridges


def test_build_graph_has_bridges_and_attributes() -> None:
    team_config = TeamConfig()
    graph_config = GraphConfig(n_cities=4, seed=2)
    G = build_graph(graph_config, team_config)

    bridges = list_bridges(G)
    assert bridges
    bridge = bridges[0]
    assert "BFI" in G.nodes[bridge]
    assert "cost" in G.nodes[bridge]
    assert "NewBFI" in G.nodes[bridge]

    for u, v in G.edges():
        assert "Time" in G[u][v]
