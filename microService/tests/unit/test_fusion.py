from app.retrieval.fusion import reciprocal_rank_fusion


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
