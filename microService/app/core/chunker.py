"""Document chunking with metadata preservation."""
from __future__ import annotations
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter


def chunk_documents(
    docs: list[Document],
    *,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[Document]:
    if not docs:
        return []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    out: list[Document] = []
    counter = 0
    for d in docs:
        for piece in splitter.split_text(d.page_content):
            meta = dict(d.metadata)
            meta["chunk_id"] = counter
            out.append(Document(page_content=piece, metadata=meta))
            counter += 1
    return out
