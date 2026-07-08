import json
import app.config.settings as settings_mod
from app.config.settings import get_settings


def _no_retrieval_json(monkeypatch, tmp_path):
    """Point the module at a retrieval.json that doesn't exist."""
    monkeypatch.setattr(settings_mod, "_RETRIEVAL_JSON_PATH", tmp_path / "retrieval.json")


def test_defaults_when_no_env_or_json(monkeypatch, tmp_path):
    _no_retrieval_json(monkeypatch, tmp_path)
    for key in [
        "RAG_CHUNK_SIZE", "RAG_CHUNK_OVERLAP", "RAG_PER_RETRIEVER_TOP_K",
        "RAG_FUSED_TOP_K", "RAG_RRF_K", "RAG_RRF_WEIGHT_VECTOR",
        "RAG_RRF_WEIGHT_BM25", "RAG_RRF_WEIGHT_GRAPH", "RAG_RERANK_MODE",
        "RAG_ENABLE_RERANK", "RAG_MULTI_QUERY_N",
    ]:
        monkeypatch.delenv(key, raising=False)

    s = get_settings()
    assert s.chunk_size == 1500
    assert s.chunk_overlap == 200
    assert s.child_chunk_size == 400
    assert s.per_retriever_top_k == 10
    assert s.fused_top_k == 15
    assert s.rrf_k == 60
    assert s.rrf_weight_vector == 1.0
    assert s.rrf_weight_bm25 == 1.0
    assert s.rrf_weight_graph == 0.5
    assert s.rerank_mode == "cross_encoder"
    assert s.multi_query_n == 3


def test_env_var_overrides_default(monkeypatch, tmp_path):
    _no_retrieval_json(monkeypatch, tmp_path)
    monkeypatch.setenv("RAG_CHUNK_SIZE", "999")
    monkeypatch.setenv("RAG_FUSED_TOP_K", "42")
    s = get_settings()
    assert s.chunk_size == 999
    assert s.fused_top_k == 42


def test_retrieval_json_overrides_default_when_no_env(monkeypatch, tmp_path):
    monkeypatch.delenv("RAG_CHUNK_SIZE", raising=False)
    monkeypatch.delenv("RAG_FUSED_TOP_K", raising=False)
    json_path = tmp_path / "retrieval.json"
    json_path.write_text(json.dumps({
        "chunk_size": 800,
        "fused_top_k": 25,
        "vector_weight": 1.0,
        "bm25_weight": 0.7,
        "graph_weight": 0.3,
        "rrf_k": 60,
    }))
    monkeypatch.setattr(settings_mod, "_RETRIEVAL_JSON_PATH", json_path)

    s = get_settings()
    assert s.chunk_size == 800
    assert s.fused_top_k == 25
    assert s.rrf_weight_bm25 == 0.7
    assert s.rrf_weight_graph == 0.3


def test_env_var_wins_over_retrieval_json(monkeypatch, tmp_path):
    json_path = tmp_path / "retrieval.json"
    json_path.write_text(json.dumps({"chunk_size": 800}))
    monkeypatch.setattr(settings_mod, "_RETRIEVAL_JSON_PATH", json_path)
    monkeypatch.setenv("RAG_CHUNK_SIZE", "1234")

    s = get_settings()
    assert s.chunk_size == 1234


def test_legacy_enable_rerank_flag_maps_to_mode(monkeypatch, tmp_path):
    _no_retrieval_json(monkeypatch, tmp_path)
    monkeypatch.delenv("RAG_RERANK_MODE", raising=False)

    monkeypatch.setenv("RAG_ENABLE_RERANK", "true")
    assert get_settings().rerank_mode == "llm"

    monkeypatch.setenv("RAG_ENABLE_RERANK", "false")
    assert get_settings().rerank_mode == "off"


def test_explicit_rerank_mode_wins_over_legacy_flag(monkeypatch, tmp_path):
    _no_retrieval_json(monkeypatch, tmp_path)
    monkeypatch.setenv("RAG_ENABLE_RERANK", "true")
    monkeypatch.setenv("RAG_RERANK_MODE", "off")
    assert get_settings().rerank_mode == "off"


def test_settings_rereads_env_on_each_call(monkeypatch, tmp_path):
    _no_retrieval_json(monkeypatch, tmp_path)
    monkeypatch.setenv("RAG_CHUNK_SIZE", "111")
    assert get_settings().chunk_size == 111
    monkeypatch.setenv("RAG_CHUNK_SIZE", "222")
    assert get_settings().chunk_size == 222
