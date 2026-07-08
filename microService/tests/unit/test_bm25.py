from app.retrieval.search import BM25Index


def test_bm25_ranks_relevant_doc_higher():
    idx = BM25Index.build([
        "the mitochondria produces atp through cellular respiration",
        "the nucleus contains the dna",
        "ribosomes synthesize proteins",
    ])
    hits = idx.search("what produces atp", top_k=2)
    assert hits[0][0] == 0  # chunk index 0 should rank first


def test_bm25_empty_corpus_returns_empty():
    idx = BM25Index.build([])
    assert idx.search("anything", top_k=5) == []


def test_bm25_serialize_roundtrip(tmp_path):
    corpus = ["alpha beta gamma", "beta gamma delta"]
    idx = BM25Index.build(corpus)
    p = tmp_path / "bm25.pkl"
    idx.save(p)
    reloaded = BM25Index.load(p)
    a = idx.search("alpha", top_k=2)
    b = reloaded.search("alpha", top_k=2)
    assert a == b
