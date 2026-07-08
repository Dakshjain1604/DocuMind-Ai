import pytest
from app.retrieval.search import reciprocal_rank_fusion


def test_rrf_merges_two_overlapping_lists():
    a = ["x", "y", "z"]
    b = ["y", "x", "w"]
    result = reciprocal_rank_fusion([a, b], k=60)
    assert result[0] in {"x", "y"}
    assert "w" in result
    assert "z" in result


def test_rrf_handles_disjoint_results():
    a = ["a", "b"]
    b = ["c", "d"]
    result = reciprocal_rank_fusion([a, b], k=60)
    assert set(result) == {"a", "b", "c", "d"}
    assert len(result) == 4


def test_rrf_handles_empty_branches():
    assert reciprocal_rank_fusion([], k=60) == []
    assert reciprocal_rank_fusion([[], []], k=60) == []


def test_rrf_respects_top_k():
    a = ["a", "b", "c", "d", "e"]
    b = ["e", "d", "c", "b", "a"]
    result = reciprocal_rank_fusion([a, b], k=60, top_k=3)
    assert len(result) == 3


def test_rrf_higher_ranks_score_higher():
    a = ["winner", "loser"]
    b = ["winner", "loser"]
    result = reciprocal_rank_fusion([a, b], k=60)
    assert result[0] == "winner"


def test_rrf_none_weights_matches_equal_weighting():
    a = ["x", "y", "z"]
    b = ["y", "x", "w"]
    unweighted = reciprocal_rank_fusion([a, b], k=60)
    equal_weighted = reciprocal_rank_fusion([a, b], k=60, weights=[1.0, 1.0])
    assert unweighted == equal_weighted


def test_rrf_applies_weights_to_scale_contribution():
    # "graph" ranking alone would put "only_in_graph" first, but with a low
    # weight it should lose to an item appearing in both other rankings.
    vec = ["a", "b"]
    bm25 = ["a", "b"]
    graph = ["only_in_graph"]
    result = reciprocal_rank_fusion(
        [vec, bm25, graph], k=60, weights=[1.0, 1.0, 0.01]
    )
    assert result[0] == "a"
    assert "only_in_graph" in result


def test_rrf_weights_length_mismatch_raises():
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([["a"], ["b"]], weights=[1.0])
