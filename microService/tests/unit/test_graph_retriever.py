from app.retrieval.search import GraphIndex


SAMPLE_GRAPH = {
    "nodes": [
        {"id": "Mitochondria", "type": "Organelle", "description": "x", "source_chunks": [1, 4]},
        {"id": "ATP", "type": "Concept", "description": "y", "source_chunks": [4]},
        {"id": "Nucleus", "type": "Organelle", "description": "z", "source_chunks": [7]},
        {"id": "DNA", "type": "Concept", "description": "w", "source_chunks": [7, 8]},
    ],
    "edges": [
        {"src": "Mitochondria", "dst": "ATP", "type": "produces"},
        {"src": "Nucleus", "dst": "DNA", "type": "contains"},
    ],
    "communities": {"Mitochondria": 0, "ATP": 0, "Nucleus": 1, "DNA": 1},
    "community_summaries": {"0": "Energy production.", "1": "Genetic material storage."},
}


def test_fuzzy_match_finds_entity():
    idx = GraphIndex(SAMPLE_GRAPH)
    matches = idx.match_entities(["mitochondria"])
    assert matches == ["Mitochondria"]


def test_traverse_returns_neighbor_chunks():
    idx = GraphIndex(SAMPLE_GRAPH)
    chunks = idx.traverse_chunks(["Mitochondria"], hops=1)
    assert set(chunks) >= {1, 4}


def test_traverse_includes_community_chunks():
    idx = GraphIndex(SAMPLE_GRAPH)
    chunks = idx.traverse_chunks(["Mitochondria"], hops=2)
    assert set(chunks) >= {1, 4}


def test_community_summary_lookup():
    idx = GraphIndex(SAMPLE_GRAPH)
    assert idx.community_summary("Mitochondria") == "Energy production."
    assert idx.community_summary("Unknown") is None
