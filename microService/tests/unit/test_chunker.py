from langchain_core.documents import Document
from app.core.chunker import chunk_documents, chunk_documents_hierarchical


def test_chunks_preserve_source_metadata():
    docs = [Document(page_content="abc " * 1000, metadata={"source": "x.pdf", "page": 3})]
    chunks = chunk_documents(docs, chunk_size=200, chunk_overlap=20)
    assert len(chunks) > 1
    for c in chunks:
        assert c.metadata["source"] == "x.pdf"
        assert c.metadata["page"] == 3
        assert "chunk_id" in c.metadata


def test_chunks_have_sequential_ids():
    docs = [Document(page_content="x" * 5000, metadata={"source": "y.pdf"})]
    chunks = chunk_documents(docs, chunk_size=500, chunk_overlap=50)
    ids = [c.metadata["chunk_id"] for c in chunks]
    assert ids == list(range(len(chunks)))


def test_empty_input_returns_empty():
    assert chunk_documents([], chunk_size=500, chunk_overlap=50) == []


def test_hierarchical_empty_input_returns_empty_pair():
    assert chunk_documents_hierarchical([]) == ([], [])


def test_hierarchical_children_are_smaller_and_more_numerous_than_parents():
    docs = [Document(page_content="word " * 3000, metadata={"source": "z.pdf"})]
    parents, children = chunk_documents_hierarchical(
        docs, parent_chunk_size=1500, parent_chunk_overlap=200,
        child_chunk_size=400, child_chunk_overlap=50,
    )
    assert len(parents) > 1
    assert len(children) > len(parents)
    assert all(len(p.page_content) <= 1500 + 50 for p in parents)  # small slop for separator boundaries
    assert all(len(c.page_content) <= 400 + 50 for c in children)


def test_hierarchical_children_have_chunk_id_and_parent_back_reference():
    docs = [Document(page_content="word " * 3000, metadata={"source": "z.pdf", "page": 2})]
    parents, children = chunk_documents_hierarchical(docs)

    # chunk_id is still a global, sequential counter (same semantics as chunk_documents)
    assert [c.metadata["chunk_id"] for c in children] == list(range(len(children)))
    # every child's parent_id points at a real parent
    valid_parent_ids = {p.metadata["parent_id"] for p in parents}
    assert all(c.metadata["parent_id"] in valid_parent_ids for c in children)
    # source metadata is preserved on both levels
    assert all(p.metadata["source"] == "z.pdf" for p in parents)
    assert all(c.metadata["page"] == 2 for c in children)


def test_hierarchical_every_parent_has_at_least_one_child():
    docs = [Document(page_content="word " * 3000)]
    parents, children = chunk_documents_hierarchical(docs)
    parent_ids_with_children = {c.metadata["parent_id"] for c in children}
    assert parent_ids_with_children == {p.metadata["parent_id"] for p in parents}
