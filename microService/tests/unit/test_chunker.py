from langchain_core.documents import Document
from app.core.chunker import chunk_documents


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
