import networkx as nx
import pytest
from unittest.mock import AsyncMock, patch
from app.indexing.community import detect_communities, build_networkx_graph


def test_build_networkx_creates_nodes_and_edges():
    entities = [
        {"id": "A", "type": "Concept", "description": "alpha", "source_chunks": [0]},
        {"id": "B", "type": "Concept", "description": "beta", "source_chunks": [1]},
    ]
    rels = [{"src": "A", "dst": "B", "type": "related_to", "description": "x", "source_chunks": [0]}]
    g = build_networkx_graph(entities, rels)
    assert set(g.nodes) == {"A", "B"}
    assert g.has_edge("A", "B")


def test_detect_communities_assigns_ids():
    g = nx.Graph()
    g.add_edges_from([("a", "b"), ("b", "c"), ("x", "y"), ("y", "z")])
    comms = detect_communities(g)
    # two groups: {a,b,c} and {x,y,z}
    assert comms["a"] == comms["b"] == comms["c"]
    assert comms["x"] == comms["y"] == comms["z"]
    assert comms["a"] != comms["x"]


def test_detect_communities_skips_when_graph_too_small():
    g = nx.Graph()
    g.add_node("only")
    comms = detect_communities(g)
    assert comms == {}
