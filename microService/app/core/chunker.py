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


def chunk_documents_hierarchical(
    docs: list[Document],
    *,
    parent_chunk_size: int = 1500,
    parent_chunk_overlap: int = 200,
    child_chunk_size: int = 400,
    child_chunk_overlap: int = 50,
) -> tuple[list[Document], list[Document]]:
    """Small-to-big chunking. Parents are the big, coherent context units;
    children are the small, precise retrieval units.

    Returns (parents, children). Each parent gets a global `parent_id`.
    Each child keeps the existing `chunk_id` semantics (global counter that
    vector/BM25/graph already key everything on) plus a `parent_id`
    back-reference — no new ID space is introduced.
    """
    if not docs:
        return [], []
    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=parent_chunk_size,
        chunk_overlap=parent_chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=child_chunk_size,
        chunk_overlap=child_chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    parents: list[Document] = []
    children: list[Document] = []
    parent_counter = 0
    child_counter = 0
    for d in docs:
        for parent_piece in parent_splitter.split_text(d.page_content):
            parent_meta = dict(d.metadata)
            parent_meta["parent_id"] = parent_counter
            parents.append(Document(page_content=parent_piece, metadata=parent_meta))

            for child_piece in child_splitter.split_text(parent_piece):
                child_meta = dict(d.metadata)
                child_meta["chunk_id"] = child_counter
                child_meta["parent_id"] = parent_counter
                children.append(Document(page_content=child_piece, metadata=child_meta))
                child_counter += 1

            parent_counter += 1
    return parents, children
