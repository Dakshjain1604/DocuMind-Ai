import pytest
from app.core.observability import (
    count_tokens,
    estimate_cost_usd,
    get_trace,
    init_trace_db,
    log_event,
    new_request_id,
    record_trace,
    timed_stage,
)


def test_new_request_id_is_short_and_unique():
    a, b = new_request_id(), new_request_id()
    assert a != b
    assert len(a) == 12


def test_count_tokens_returns_positive_int_for_nonempty_text():
    assert count_tokens("hello world") > 0


def test_count_tokens_empty_string_is_zero():
    assert count_tokens("") == 0


def test_estimate_cost_usd_defaults_to_zero_for_unknown_model():
    assert estimate_cost_usd("some/free-model:free", 1000, 1000) == 0.0


def test_timed_stage_appends_to_sink_on_success():
    sink = []
    with timed_stage("mystage", "req-1", sink=sink, extra_field="x"):
        pass
    assert len(sink) == 1
    assert sink[0]["stage"] == "mystage"
    assert sink[0]["extra_field"] == "x"
    assert sink[0]["latency_ms"] >= 0


def test_timed_stage_appends_error_to_sink_and_reraises():
    sink = []
    with pytest.raises(ValueError):
        with timed_stage("mystage", "req-1", sink=sink):
            raise ValueError("boom")
    assert len(sink) == 1
    assert sink[0]["error"] == "boom"


def test_timed_stage_without_sink_does_not_raise(capsys):
    with timed_stage("mystage", "req-1"):
        pass  # should just log, no sink required


def test_init_trace_db_is_idempotent(tmp_path):
    db_path = str(tmp_path / "traces.db")
    init_trace_db(db_path)
    init_trace_db(db_path)  # must not raise on second call


def test_record_and_get_trace_roundtrip(tmp_path):
    db_path = str(tmp_path / "traces.db")
    record_trace(
        "req-abc",
        doc_hash="doc1",
        query="what is X?",
        total_latency_ms=100.5,
        total_tokens_in=50,
        total_tokens_out=75,
        total_cost_usd=0.0,
        cache_hit=False,
        stages=[{"stage": "rewrite", "latency_ms": 10.0}],
        context=[{"n": 1, "chunk_id": 3}],
        answer_text="X is Y",
        db_path=db_path,
    )
    trace = get_trace("req-abc", db_path=db_path)
    assert trace["doc_hash"] == "doc1"
    assert trace["query"] == "what is X?"
    assert trace["total_latency_ms"] == 100.5
    assert trace["total_tokens_in"] == 50
    assert trace["cache_hit"] is False
    assert trace["stages"] == [{"stage": "rewrite", "latency_ms": 10.0}]
    assert trace["context"] == [{"n": 1, "chunk_id": 3}]
    assert trace["answer_text"] == "X is Y"


def test_get_trace_returns_none_for_unknown_id(tmp_path):
    db_path = str(tmp_path / "traces.db")
    init_trace_db(db_path)
    assert get_trace("nope", db_path=db_path) is None


def test_get_trace_returns_none_when_db_file_absent(tmp_path):
    assert get_trace("nope", db_path=str(tmp_path / "never_created.db")) is None


def test_record_trace_overwrites_existing_request_id(tmp_path):
    db_path = str(tmp_path / "traces.db")
    record_trace("req-x", doc_hash="d", query="q", answer_text="first", db_path=db_path)
    record_trace("req-x", doc_hash="d", query="q", answer_text="second", db_path=db_path)
    trace = get_trace("req-x", db_path=db_path)
    assert trace["answer_text"] == "second"
